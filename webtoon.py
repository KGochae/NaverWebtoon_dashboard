# dashboard
import streamlit as st
from streamlit_elements import dashboard
from streamlit_elements import nivo, elements, mui, media

# data 
import pandas as pd
import numpy as np
import re
import time
import datetime
import calendar
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
from scipy.stats import shapiro, levene,ttest_ind

from tqdm import tqdm
from stqdm import stqdm

from lifetimes.plotting import *
from lifetimes.utils import *
from lifetimes.plotting import *
from lifetimes.utils import *
from lifetimes import BetaGeoFitter
from lifetimes.fitters.gamma_gamma_fitter import GammaGammaFitter

from hyperopt import hp, fmin, tpe, rand, SparkTrials, STATUS_OK, space_eval, Trials




# scraping
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# google cloud platform
import io
from googleapiclient.discovery import build
from google.cloud import storage, bigquery
from google.oauth2 import service_account

# 일부 css
with open( "webtoon.css" ) as css:
    st.markdown( f'<style>{css.read()}</style>' , unsafe_allow_html= True)
pd.set_option('mode.chained_assignment',  None)

# 데이터 수집 날짜
now = datetime.datetime.now()
now_time = now.strftime("%Y-%m-%d")
st.caption(' 해당 대시보드는 220606 ~ 240303 기간동안의 데이터 기준으로 만들어졌습니다. 😀') #.strftime('%Y-%m-%d %H:%M'))


# 웹브라우저를 열지 않고 크롤링 하려면 headless 옵션을 주면 된다.

# chrome_options = Options()
# chrome_options.add_argument('--headless')  # 웹 브라우저를 헤드리스 모드로 실행할 경우 추가
# driver = webdriver.Chrome(options=chrome_options) # options=chrome_options

# 에피소드별 댓글 정보 (user_nick, comment_date)



def get_comment_by_ep(episode):
    result_list = []

    for ep in stqdm(episode):

        driver.get(f"https://comic.naver.com/webtoon/detail?titleId=811721&no={ep}")
        time.sleep(0.2)
        
        episode_title = driver.find_element(By.XPATH,'//*[@id="subTitle_toolbar"]').text
        time.sleep(0.2)

        total_comment = driver.find_element(By.XPATH, '//*[@id="cbox_module_wai_u_cbox_sort_option_tab2"]') # '//*[@id="cbox_module_wai_u_cbox_sort_option_tab2"]'
        total_comment.click()
        time.sleep(0.2)
                                                        
        while True:
            try:
                # 더보기 버튼 클릭
                more_btn = driver.find_element(By.CLASS_NAME, 'u_cbox_btn_more')
                more_btn.click()

                # 새로운 댓글 로딩이 완료될 때까지 대기 (시간을 조절하셔서 적절히 대기시간을 설정하세요)
                time.sleep(1)

                # 업데이트된 댓글 요소들을 다시 찾기
                user_ids = driver.find_elements(By.CLASS_NAME, 'u_cbox_name_area')
                contents = driver.find_elements(By.CLASS_NAME, 'u_cbox_contents')
                comment_dates = driver.find_elements(By.CLASS_NAME, 'u_cbox_date')
                comment_likes = driver.find_elements(By.CLASS_NAME, 'u_cbox_cnt_recomm')
                comment_dislikes = driver.find_elements(By.CLASS_NAME,'u_cbox_cnt_unrecomm')

            except Exception as e:
                # 더 이상 더보기 버튼이 없으면 예외 발생하고 반복문 탈출
                break


        # 유저 아이디는 남지만 클린봇에 의해 댓글이 삭제되는 경우가 있음. 
        comment_data = {
            'episode': episode_title,
            'content': [],
            'user_id': [],
            'comment_date': [],
            'comment_like': [],
            'comment_dislike': []
        }

        for user_id, content, comment_date, comment_like, comment_dislike in zip(user_ids,contents,comment_dates, comment_likes, comment_dislikes):
            try:
                # comment_like, comment_dislike가 없는 경우를 처리하기 위해 int()를 사용하여 변환
                comment_data['user_id'].append(user_id.text)
                comment_data['content'].append(content.text)
                comment_data['comment_date'].append(comment_date.text)
                comment_data['comment_like'].append(int(comment_like.text))
                comment_data['comment_dislike'].append(int(comment_dislike.text))

            except ValueError:
                # 해당 댓글은 스킵하고 다음 댓글로 진행
                pass

        df = pd.DataFrame(comment_data)
        result_list.append(df)

    # 각 에피소드별 데이터프레임을 합치기
    result_df = pd.concat(result_list, ignore_index=True)

    return result_df



# 업로드 날짜 데이터
def get_webtoon_upload_at():
    try:
        result_list = []  

        # 페이지가 몇개 있는지 가져오기
        driver.get("https://comic.naver.com/webtoon/list?titleId=811721")
        time.sleep(0.5) 
        favorite = driver.find_elements(By.CLASS_NAME, 'EpisodeListUser__count--fNEWK')
        page_numbers = driver.find_elements(By.CLASS_NAME, 'Paginate__page--iRmGj')
        total_pages = len(page_numbers)

        for i in stqdm(range(1, total_pages + 1)):
            # 각 페이지에 얼마나 작품이 있는지 개수 가져오기
            driver.get(f"https://comic.naver.com/webtoon/list?titleId=811721&page={i}")
            time.sleep(0.8) 

            elements = driver.find_elements(By.CLASS_NAME, 'EpisodeListList__item--M8zq4')
            episode_num = len(elements)  # 작품의 개수

            for j in range(1, episode_num + 1):  
                title  = driver.find_element(By.CLASS_NAME ,'EpisodeListInfo__title--mYLjC').text
                episode = driver.find_element(By.XPATH, f'//*[@id="content"]/div[3]/ul/li[{j}]/a/div[2]/p/span').text
                upload_at = driver.find_element(By.XPATH, f'//*[@id="content"]/div[3]/ul/li[{j}]/a/div[2]/div/span[2]').text
    
                # 각 작품의 정보를 딕셔너리로 만들어 리스트에 추가
                result_list.append({
                    'title': title,
                    'episode': episode,
                    'upload_at': upload_at
                })

        result = pd.DataFrame(result_list)
        result['favorite'] = favorite
        ep_len = len(result)
        return result, ep_len

    except Exception as e:
        print(f"error {str(e)} : 데이터 수집 완료")
        return None


# 각 에피소드별 참여도 지표
def get_webtoon_info(ep_len):
    try:
        result_list = []

        for i in stqdm(range(1, ep_len+1)):
            driver.get(f"https://comic.naver.com/webtoon/detail?titleId=811721&no={i}")
            time.sleep(0.2)

            episode = driver.find_element(By.XPATH, '//*[@id="subTitle_toolbar"]').text
            time.sleep(0.2)

            like_count = driver.find_element(By.XPATH, '//*[@id="viewerView"]/div/div/div[1]/div[1]/div/div/a/em[2]').text        
            time.sleep(0.2)

            comment_count = driver.find_element(By.XPATH, '//*[@id="cbox_module"]/div/div[1]/span').text
            time.sleep(0.2)

            score = driver.find_element(By.XPATH, '//*[@id="viewerView"]/div/div/div[1]/div[1]/button[2]/span[1]/span').text
            time.sleep(0.2)

            score_count = driver.find_element(By.XPATH, '//*[@id="viewerView"]/div/div/div[1]/div[1]/button[2]/span[2]').text
            score_count = re.sub(r"\D", "", score_count)

            tag = driver.find_element(By.CLASS_NAME,'TagGroup__tag--xu0OH').text


            result_list.append({
                'episode': episode,
                'Tag' : tag,
                'like_count': like_count,
                'comment_count': comment_count,
                'score_count': score_count,
                'score': score,
                'down_at' : now_time
                })


        return  pd.DataFrame(result_list)
 

    except Exception as e:
        print(f"error {str(e)} : 데이터 수집 완료")
        return None


# def get_webtoon_info():
#     driver.get('https://comic.naver.com/webtoon/list?titleId=811721')
#     time.sleep(0.5)

#     total_len = driver.find_element(By.XPATH, '//*[@id="content"]/div[3]/ul/li[1]/a/div[2]/p/span').text
#     total_len = re.sub(r"\D", "", total_len)
#     total_len = int(total_len)


#     cookie_len = driver.find_element(By.XPATH, '//*[@id="content"]/div[3]/div[2]/button/span[1]/strong').text  
#     cookie_len = re.sub(r"\D", "", cookie_len)
#     cookie_len = int(cookie_len)

#     ep_len = total_len - cookie_len

#     try:

#         # episode 별 지표
#         result_list = []

#         for i in range(1, ep_len+1):
#             time.sleep(1)
#             driver.get(f"https://comic.naver.com/webtoon/detail?titleId=811721&no={i}")

#             time.sleep(2)
#             episode = driver.find_element(By.XPATH, '//*[@id="subTitle_toolbar"]').text
#             like_count = driver.find_element(By.CLASS_NAME, 'u_cnt _count').text        
#             comment_count = driver.find_element(By.CLASS_NAME, 'u_cbox_count').text
#             score = driver.find_element(By.XPATH, '//*[@id="viewerView"]/div/div/div[1]/div[1]/button[2]/span[1]/span').text
#             score_count = driver.find_element(By.XPATH, '//*[@id="viewerView"]/div/div/div[1]/div[1]/button[2]/span[2]').text
#             score_count = re.sub(r"\D", "", score_count)

#             tag = driver.find_element(By.CLASS_NAME,'TagGroup__tag--xu0OH').text



#             result_list.append({
#                 'episode': episode,
#                 'Tag' : tag,
#                 'like_count': like_count,
#                 'comment_count': comment_count,
#                 'score_count': score_count,
#                 'score': score,
#                 'down_at' : now
#                 })


#         return  pd.DataFrame(result_list)
 

#     except Exception as e:
#         print(f"error {str(e)} : 데이터 수집 완료")
#         return None


def get_data ():
 
    df, ep_len = get_webtoon_upload_at()
    indicator = get_webtoon_info(ep_len)    

    # 결과 출력
    stick_df = pd.merge(df, indicator, on='episode',how='inner')
    return stick_df



# ---------------------------------------------------------------- GOOGLE Cloud Storage 에 데이터 연결 ----------------------------------------------------------- #


#------------- Create API client ----------------------------------- #

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)



#------------- storage 에 있는 userid 데이터 가져오기 --------------- #
main_bucket = 'naver_webtoon'
data_folder = ['baeksoon/user_id/', 'baeksoon/main_data/']



def load_data(data_folder):
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(main_bucket)
    blobs = bucket.list_blobs()

    # 폴더 안에 있는 CSV 파일만 필터링합니다.

    comment_data =  [blob for blob in blobs if blob.name.startswith(data_folder) and blob.name.endswith('.csv')]

    # CSV 파일을 DataFrames로 변환합니다.
    dfs = []
    for blob in comment_data:
        csv_data = blob.download_as_string()
        df = pd.read_csv(io.StringIO(csv_data.decode('utf-8')))
        dfs.append(df)

    # 모든 DataFrames를 병합합니다.
    data = pd.concat(dfs)
    return data






# 데이터 불러오기 side_bar
with st.sidebar:
    # st.image('https://image-comic.pstatic.net/webtoon/811721/thumbnail/thumbnail_IMAG21_9a2a959a-666b-4156-8e4f-db64dfe319c6.jpg',width=200)
    with st.form(key ='searchform'):
        col1,col2= st.columns([2,2]) 
        with col1:         
            st.subheader("webtoon dataset")
        
        with col2:    
            submit_search = st.form_submit_button('data')
            scraping = st.form_submit_button('comment')

# 데이터 불러오기
if submit_search:
    comment_data = load_data(data_folder[0])
    main_data = load_data(data_folder[1])

    st.session_state.comment_data = comment_data
    st.session_state.main_data = main_data


# 댓글 데이터 수집.

# episode = [67,76,78]

# if scraping:
#     comment = get_comment_by_ep(episode)
#     st.session_state.comment = comment

# if hasattr(st.session_state, 'comment'):
#    comment = st.session_state.comment 
#    st.write(comment)

# if st.button('Download to CSV'):
#     # 파일 경로 및 파일명 설정
#     file_path = f'C:\webtoon\comment_top3.csv'  
#     comment.to_csv(file_path, index=False,encoding='utf-8-sig')
#     st.success("Success")






# st.subheader(''' 
#             🖥️ 분석해볼만한 과제들
#             ''')

# st.write(''' 
#         ##### ① 특정 에피소드의 트래픽 증가 원인 분석        
#         * Dau, wau, mau의 변동성에 영향을 준 시점이 있을까? 그리고 영향을 준 특정 에피소드가 있다면? 
#         * 월별 Stickiness는 차트를 만들어보자. 독자들의 고착도가 증가하고 있는지 확인할 수 있다. 만약 증가하는 추세가 보인다면 언제부터 였을까?
#         * 웹툰이 시즌마다 어떻게 변화하는지를 분석하여, 각 시즌의 특징과 독자들의 참여도의 변동을 분석해보자.

#         ##### ② 같은 장르간 웹툰 비교
#         * 같은 장르의 다른 작품들과 비교 하고 싶은데, 그러기 위해서는 댓글 데이터를 작품별로 수집해야한다. 이게 꽤 시간이 많이걸린다..        

#         ##### ③ 댓글을 활용한 분석
#         * vip 멤버를 구해보자! (참여도가 가장 높은 찐팬 독자) Recency Frequency 를 기준으로.. (monetray의 경우 공감수+ 댓글수 로 대체)
 
#         ''' )



if hasattr(st.session_state, 'main_data'):
    main_data = st.session_state.main_data
    main_data['chapter'] = main_data['episode'].apply(lambda x: re.search(r'\b(\d+)\D', x).group(1) if re.search(r'\b(\d+)\D', x) else None)

    @st.cache_resource
    def data_diff (data):
        # data = pd.concat(dfs) if dfs else ''
        data = data.sort_values(by=['upload_at', 'down_at'])

        data['like_count'] = data['like_count'].str.replace(',', '').astype(int)
        data['comment_count'] = data['comment_count'].str.replace(',', '').astype(int)

        data['user_response'] = data['like_count'] + data['comment_count'] + data['score_count']

        # 날짜 데이터 형태가 'T19:39:21Z' 형식 이라 / 일단 '년월일' 형태의 문자열(str)로 바꾸고 다시 데이트타입으로 바꿔야한다.
        data['upload_at'] = pd.to_datetime(data['upload_at']).dt.strftime('%Y-%m-%d')
        data['upload_at'] = pd.to_datetime(data['upload_at'], format='%Y-%m-%d')

        data['down_at'] = pd.to_datetime(data['down_at']).dt.strftime('%Y-%m-%d')
        data['down_at'] = pd.to_datetime(data['down_at'], format='%Y-%m-%d')
        # data = data[data['down_at'] > '2023-10-01'] ################################################ 
        # year 과 month 를 구분해주자.
        data['year'] = data['upload_at'].dt.year.astype(str)
        data['month'] = data['upload_at'].dt.month.astype(str)

        # 전일 대비 조회수및 좋아요 컬럼
        data['prev_user_response'] = data.groupby(['chapter','upload_at'])['user_response'].shift()
    
        # data.loc[(data['down_at'] - data['upload_at'] ).dt.days == 1, 'user_response'] = 0

        data['response_diff'] = data['user_response'] - data['prev_user_response']

        data['down_at'] = pd.to_datetime(data['down_at']).dt.strftime('%Y-%m-%d')    
        data['upload_at'] = pd.to_datetime(data['upload_at']).dt.strftime('%Y-%m-%d')    

    
        return data
    
    data = data_diff(main_data)

    # 일별 독자들의 참여도 (좋아요+댓글+평점 참가를 합친 값)
    response_df = data.groupby(['down_at']).agg(
       total_response = pd.NamedAgg(column='response_diff', aggfunc='sum')
    ).reset_index()


    nivo_data_response = []
    for index, row in response_df.iterrows():
        nivo_data_response.append({'x': row['down_at'], 'y': row['total_response']})

    nivo_data_response = [{
        "id": "response",
        "data": nivo_data_response
    }]
    today_response = response_df['total_response'].iloc[-1]
    with st.container():       
            with elements("response_by_day"):
                layout = [
                    dashboard.Item("item_1", 0, 0, 4, 2),

                ]
                with dashboard.Grid(layout):

                    mui.Box( # subscribe
                        children = [
                            mui.Typography(
                                "Today Count",
                                variant="body2",
                                sx={"fontFamily":"Pretendard Variable",
                                    "font-size": "18px",
                                    "pt":2} ,
                            ),

                            mui.Typography(
                                f"{today_response}",
                                variant="body2",
                                sx={
                                    "font-size": "32px",
                                    "fontWeight":"bold",
                                    "padding-top": 0
                                    } ,
                                
                            ),
                            
                            mui.Divider(),

                            mui.Typography(
                                '일별 독자 반응(좋아요+댓글+평점참여)',
                                    variant="body2",
                                    color="text.secondary",
                                    sx={'pt':1,"font-size": "10px"}
                            ),

                            nivo.Line(
                                data= nivo_data_response,
                                margin={'top': 0, 'right': 30, 'bottom': 150, 'left': 60},
                                # xScale={'type': 'point',
                                #         },

                                curve="monotoneX",
                                axisTop=None,
                                axisRight=None,
                                axisBottom={
                                    'format': '%m-%d',  # '%Y-%m-%d'
                                    'legendOffset': -12,
                                    'tickValues': 'every 3 days'
                                },
                                xFormat="time:%Y-%m-%d",
                                xScale={
                                    'format': '%Y-%m-%d',
                                    'precision': 'day',
                                    'type': 'time',
                                    # 'useUTC': False
                                },
                                colors= {'scheme': 'accent'},

                                enableGridX = False,
                                enableGridY = False,
                                enableArea = True,
                                areaOpacity = 0.2,
                                # enablePointLabel=True,
                                # pointLabel='y',
                                lineWidth=2,
                                pointSize=3,
                                pointColor='white',
                                pointBorderWidth=0.5,
                                pointBorderColor={'from': 'serieColor'},
                                pointLabelYOffset=-12,
                                useMesh=True,
                                legends=[
                                            {
                                            'anchor': 'top-left',
                                            'direction': 'column',
                                            'justify': False,
                                            # 'translateX': -30,
                                            # 'translateY': -200,
                                            'itemsSpacing': 0,
                                            'itemDirection': 'left-to-right',
                                            'itemWidth': 80,
                                            'itemHeight': 15,
                                            'itemOpacity': 0.75,
                                            'symbolSize': 12,
                                            'symbolShape': 'circle',
                                            'symbolBorderColor': 'rgba(0, 0, 0, .5)',
                                            'effects': [
                                                    {
                                                    'on': 'hover',
                                                    'style': {
                                                        'itemBackground': 'rgba(0, 0, 0, .03)',
                                                        'itemOpacity': 1
                                                        }
                                                    }
                                                ]
                                            }
                                        ],                            
                                theme={
                                        # "background-color": "rgba(158, 60, 74, 0.2)",
                                        "textColor": "black",
                                        "tooltip": {
                                            "container": {
                                                "background": "#3a3c4a",
                                                "color": "white",
                                            }
                                        }
                                    },                                           
                                animate= False)
                                ]                                
                            ,key="item_1",sx={"text-align":"center"})





if hasattr(st.session_state, 'comment_data'):
    comment_data = st.session_state.comment_data


    # 이벤트가 실행될 때마다 전처리 코드들이 실행되지 않게 cache_resource 
    @st.cache_resource
    def preprocessing (comment_data):
        # 클린봇에 의해 제거된 댓글 제거
        comment_data = comment_data.dropna(axis=0)

        # N일전 N시간 전 같은 형태의 값이 있다.
        # 정규 표현식을 사용하여 숫자만 추출하고 데이터 수집일인 '2024-03-08' 기간과 뺴야한다.
        def extract_numbers(value):
            return int(re.sub(r"\D", "", value))  if isinstance(value, str) else None


        down_date = '2024-03-08'
        down_date = pd.to_datetime(down_date, format='%Y-%m-%d')
        
        # 'comment_date' 컬럼의 값에 '~일 전' 형식인 경우, 숫자 추출하여 'col' 컬럼에 할당
        comment_data['comment_date'] = comment_data['comment_date'].apply(lambda x: extract_numbers(x) if '일 전' in str(x) else x)
        comment_data['comment_date'] = comment_data['comment_date'].apply(lambda x: down_date - datetime.timedelta(days=x) if isinstance(x, int) else x)    

        # comment_date 열의 값을 날짜 형식으로 변환
        comment_data['comment_date'] = pd.to_datetime(comment_data['comment_date'], errors='coerce') # errors='coerce' 를통해 '2일전' 같은 문자열 값들은 None 값으로 바뀌게 된다.

        # 데이터는 2월 마지막주 를 기준으로 집게
        comment_data = comment_data.dropna(subset=['comment_date'])
        comment_data = comment_data[comment_data['comment_date'] <= '2024-03-03']

        comment_data['day_name'] = comment_data['comment_date'].dt.day_name()
        # 일자별 활성 사용자 (DAU)
        dau = comment_data.groupby([comment_data['comment_date'].dt.date,'day_name'])['user_id'].nunique().reset_index() #  'day_name'
        # 주간별 활성 사용자 (WAU)
        wau = comment_data.groupby(comment_data['comment_date'].dt.to_period('W').dt.start_time.dt.date)['user_id'].nunique().reset_index()
        # 월간별 활성 사용자 (MAU)
        mau = comment_data.groupby(comment_data['comment_date'].dt.to_period('M').dt.start_time.dt.date)['user_id'].nunique().reset_index()
        return  comment_data, dau, wau, mau
    
    comment_data, dau, wau, mau = preprocessing(comment_data)

    unique_user  = len(comment_data['user_id'].unique())  # 댓글을 담긴 유니크한 유저

    with st.container():
        st.header(''' 
                Activation User  
                ''')
        st.caption(''' 
                   활성화 유저의 기준은 '댓글'을 남긴 유저로 정했어요. 댓글과 좋아요는 웹툰을 보고 난 뒤, 즉 서비스를 이용했다는 가장 확실한 흔적이 라고 생각했습니다.  
                   그 중 에피소드별 남겨진 댓글의 아이디를 기준으로 고유 유저수를 집계 했어요🫡! 웹툰 페이지에서 구할 수 있는 댓글 정보를 이용하여 일부 필터링된 '닉네임(id***)' 이 같다면 동일 유저로 판단했습니다. 
                     
                    ''')

        

        max_date = max(comment_data['comment_date'].dt.date) 
        min_date = min(comment_data['comment_date'].dt.date)


        # 날짜, activation 옵션 columns
        col1,col2 = st.columns([1,4])
        with col1:
            d = st.date_input(
                "날짜",
                (min_date, max_date),
                min_date, # 최소 날짜
                max_date, # 최대 날짜
                format="YYYY.MM.DD",
            ) 
            if len(d) >= 2: 
                start_d = d[0]
                end_d = d[1]
            else:
                start_d = d[0]
                end_d = max_date

        with col2:

            indication = st.radio(
                "유저 활성화 지표",
                ["DAU", "WAU", "MAU"],
                 horizontal=True, label_visibility="visible"
            )
        # 선택된 값을 기반으로 해당 데이터프레임 가져오기
            if indication == "DAU":
                df = dau
            elif indication == "WAU":
                df = wau
            elif indication == "MAU":
                df = mau
            





        #     st.write(f''' 현재 {unique_user}명의 독자가 웹툰을 보고 댓글을 남겼어요. '개그' 장르의 다른 작품에 비해 % 높은 수치입니다!''')


        # 활성화 지표별 시각화 함수
        def user_active_chart (df,title,color):
            title = indication
            date_mask = (df['comment_date'] >= start_d) & (df['comment_date'] <= end_d) # date로 지정된 값들만 
            df = df.loc[date_mask]
            pivot = pd.pivot_table(df, values='user_id', index='comment_date')



            st.subheader(f'📊 {title}')
            st.line_chart(pivot, use_container_width=True,color=color)



        col1,col2 = st.columns([3,1])
        with col1:
            
            user_active_chart(df,'📊 Daily Active User','#75D060')
    
            st.markdown(''' 
                    > * 무직백수계백순 웹툰의 경우 일요일, 수요일에 연재되는 작품입니다. 정해진 요일에만 연재되는 웹툰 특성상 요일별로 큰 변동성이 있었습니다.                                                                 
                    ''')
   

        # issue
        with col2:
            # st.subheader(' ✔️Issue')

            st.markdown('''
                #### 독자들의 재방문이 높을까?              
                         ''')
            st.caption('* 해당 주의 전체 DAU가 WAU 보다 높은 경우 : 재방문하는 독자들이 많은것으로 볼 수 있습니다.  ')

            #--------------------------------- 재방문 그래프 ---------------------------------------------- #

            dau = dau.rename(columns={'user_id':'dau'})
            dau['comment_date'] = pd.to_datetime(dau['comment_date'], errors='coerce')
            dau['week'] = dau['comment_date'].dt.to_period('W').dt.start_time.dt.date
            dau['month'] = dau['comment_date'].dt.to_period('M').dt.start_time.dt.date

            dw = pd.merge(dau, wau, left_on='week', right_on='comment_date', how='inner')
            dw = dw.rename(columns={'user_id': 'wau','comment_date':'week','comment_date_x':'day'}).drop(columns=['comment_date_y']) 
            dw['dau_sum'] = dw.groupby(['week'])['dau'].transform('sum')
            dw['dau_wau_diff'] = dw['dau_sum'] - dw['wau']
            dw= dw.drop_duplicates(subset=['week'])[['week','dau_sum','wau','dau_wau_diff']]


            # chort_df = comment_data.copy()
            # chort_df.set_index('user_id', inplace=True)
            # 유저별 첫 참여기간 추출
            # chort_df['CohortGroup'] = chort_df.groupby(level=0)['comment_date'].min().apply(lambda x: x.strftime('%Y-%m'))
            # chort_df.reset_index(inplace=True)


# ------------------------------------------------------ 댓글 데이터를 기준으로 유저 고착도를 구해보자 --------------------------------------------- #




        st.header('Stickiness ')
        st.caption(''' 해당 웹툰은 아직 연재일이 1년이 안된 웹툰입니다. 또한 주에 2번 연재되는 작품 특성상 활성화 유저 또한 해당 연재일에 주로 들어오는 경향이 있기 때문에
                    wau를 나눠서 구하는것이 적절해 보였습니다.
                    ''')



        # 주간 stick 구하기 
        # 일단, 해당 요일이 어느 주인지 filter 필요
        # 해당 테이블에 wau merge   
        stick_df = pd.merge(dau, wau, left_on='week', right_on='comment_date', how='inner')
        stick_df = stick_df.rename(columns={'user_id': 'wau','comment_date':'week','comment_date_x':'day'}).drop(columns=['comment_date_y']) 
        stick_df['week_stick'] = round(stick_df['dau'] / stick_df['wau'],2) * 100
        stick_df['week_stick'] = stick_df['week_stick'].astype(int)
        


        # 연재되는 날짜의 유저 고착도 구하기
        def Stickiness(stick_df ,day):
            Stickiness = stick_df[stick_df['day_name'].isin(day)]
            Stickiness['week'] = pd.to_datetime(Stickiness['week']).dt.strftime('%Y-%m-%d')
            Stickiness = Stickiness.groupby(['week']).agg(
                week_stick_mean = pd.NamedAgg(column='week_stick', aggfunc='mean')                                                   
                                                    ).reset_index()
            Stickiness['week_stick_mean']=round(Stickiness['week_stick_mean'])

            # (연재되는 날의)평균 고착도
            mean_stick = round(Stickiness['week_stick_mean'].mean())

            # 데이터 변환
            nivo_data = []
            for index, row in Stickiness.iterrows():
                nivo_data.append({'x': row['week'], 'y': row['week_stick_mean']})

            nivo_data = [{
                "id": "stickness",
                "data": nivo_data
            }]
            return mean_stick, nivo_data



        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown('''#### 📊 Stickness ''' )
            mean_stick, nivo_data =  Stickiness(stick_df, day = list(calendar.day_name))
            title = '요일별' 
            on = st.toggle('(연재일) Stickness')
            if on:
                mean_stick, nivo_data =  Stickiness(stick_df, day = ['Sunday','Wednesday'])
                title = '연재일'





            with st.container():       
                    with elements("playlist_line_chart"):
                        layout = [
                            dashboard.Item("item_1", 0, 0, 12, 2),
                        ]

                        with dashboard.Grid(layout):                                                            
                            mui.Box(                                        
                                nivo.Line(
                                    data= nivo_data,
                                    margin={'top': 40, 'right': 30, 'bottom': 30, 'left': 30},
                                    # xScale={'type': 'point',
                                    #         },

                                    curve="monotoneX",
                                    axisTop=None,
                                    axisRight=None,
                                    axisBottom={
                                        'format': '%y-%m-%d',  # '%Y-%m-%d'
                                        'legendOffset': -12,
                                        'tickValues': 'every 30 days'
                                    },
                                    xFormat="time:%Y-%m-%d",
                                    xScale={
                                        'format': '%Y-%m-%d',
                                        'precision': 'day',
                                        'type': 'time',
                                        # 'useUTC': False
                                    },
                                    colors= {'scheme': 'accent'},

                                    enableGridX = False,
                                    enableGridY = False,
                                    enableArea = True,
                                    areaOpacity = 0.2,
                                    lineWidth=2,
                                    pointSize=3,
                                    pointColor='white',
                                    pointBorderWidth=0.5,
                                    pointBorderColor={'from': 'serieColor'},
                                    pointLabelYOffset=-12,
                                    useMesh=True,
                                    legends=[
                                                {
                                                'anchor': 'top-left',
                                                'direction': 'column',
                                                'justify': False,
                                                # 'translateX': -30,
                                                # 'translateY': -200,
                                                'itemsSpacing': 0,
                                                'itemDirection': 'left-to-right',
                                                'itemWidth': 80,
                                                'itemHeight': 15,
                                                'itemOpacity': 0.75,
                                                'symbolSize': 12,
                                                'symbolShape': 'circle',
                                                'symbolBorderColor': 'rgba(0, 0, 0, .5)',
                                                'effects': [
                                                        {
                                                        'on': 'hover',
                                                        'style': {
                                                            'itemBackground': 'rgba(0, 0, 0, .03)',
                                                            'itemOpacity': 1
                                                            }
                                                        }
                                                    ]
                                                }
                                            ],                            
                                    theme={
                                            # "background-color": "rgba(158, 60, 74, 0.2)",
                                            "textColor": "black",
                                            "tooltip": {
                                                "container": {
                                                    "background": "#3a3c4a",
                                                    "color": "white",
                                                }
                                            }
                                        },
                                    markers=[{                                                
                                        'axis': 'y',
                                        'legend': 'mean',
                                        'lineStyle': {
                                            'stroke': '#b0413e',
                                            'strokeWidth': 1
                                        },
                                        'value': mean_stick                                                
                                    }] ,                                             
                                    animate= False)
                                    ,key="item_1",sx={"borderRadius":"15px", "borderRadius":"15px","background-color":"#F0F2F6"}) 





        with col2:
            
            st.write(f''' 
                    #### {title} 평균 stickiness (막대차트)                     
                    * 지발님의 작품 '무직백수 계백순'의 평균 고착도(DAU/WAU)는 <strong style="color:#75D060"> {mean_stick}% </strong>입니다.  
                    * 큰 변동 없이 7일 중 평균 <strong style="color:#75D060"> {(mean_stick/100)*7}번 </strong> 댓글을 남기고 있습니다.  
                    * 한 주당 2번 연재되는 웹툰 시스템을 고려한다면 아주 준수한 상태라고 생각합니다.😀 
                     ''',unsafe_allow_html=True )  


    

    # 독자들이 서비스를 이용하는 시간대
    with st.container():
        st.subheader(''' 
                    🤔 독자들이 가장 많이 보는 시간대는 언제인가요?
                    ''')
        st.caption(''' 
                * 웹툰의 조회수에 대한 정확한 값은 알 수 없었습니다. 하지만 조회수와 댓글간의 상관성은 매우 높다고 판단하여 독자들의 참여도 지표인 '댓글'을 남긴시간을 이용하여 가장 많이 보는 시간대를 집계해보았습니다! 
                    ''')
        # comment_data[;]
        comment_data['hour'] = comment_data['comment_date'].dt.hour #.strftime("%Y-%m-%d %H:%M:%S")

        comment_group_by_hour = comment_data.groupby(['hour']).agg(        
            cnt = pd.NamedAgg(column='hour',aggfunc='count'))

        st.line_chart(comment_group_by_hour, use_container_width=True)
        st.write('''
                  주로 웹툰 업로드가 되는 시간대인 밤(11시)부터 새벽 시간대에 가장 많은 독자들이 접속함을 볼 수 있었어요! 
                 또한 상대적으로 완만하지만 오전 시간대(6시~8시) 그리고 낮 시간대에는 12시에 많은 웹툰을 보는 독자들이 있었습니다. ''')



        comment_data['morning'] = 0
        comment_data['day'] = 0
        comment_data['night'] = 0

        comment_data.loc[comment_data['hour'].between(6, 11), 'morning'] = 1
        comment_data.loc[comment_data['hour'].between(12, 17), 'day'] = 1
        comment_data.loc[~comment_data['hour'].between(6, 17), 'night'] = 1


        user_timeinfo = comment_data.groupby(['user_id']).agg(
                    morning = pd.NamedAgg(column='morning',aggfunc='sum'),
                    day = pd.NamedAgg(column='day',aggfunc='sum'),
                    night = pd.NamedAgg(column='night',aggfunc='sum')
                )



        st.divider()

    # ltv 산출하기
    with st.container():
        
        st.header('🏅 LTV 활용하기')
        st.markdown(''' 
                    #### ✔️ 밤에 비해 오전, 낮시간대의 UV가 적은 것을 볼 수 있었습니다.            
                    이를 위해 효율적으로 낮 시간대의 UV 확보하기 위한 프로모션 이벤트를 진행하려고 합니다. 이벤트를 진행할 예산을 효율적으로 사용하여 목표를 달성할 수 있는 방법이 있을까요?    
                    독자들이 주로 이용하는 시간대의 그룹을 나누고 LTV를 활용하여 이벤트를 진행해봅시다.                      
                     ''')



        # st.write('''
        #          해당 서비스에서 LTV를 구해야하는 이유는 뭘까? 먼저 해당 서비스의 수익 모델을 확인해보자.

        #          ① 수익성 분배 PPS(Page Profit Share)모델  
        #          웹툰 하단의 이미지 광고, 미리보기 유료 판매 수익, 드라마/영화 영상화, IP(지적 재산권)기반 비즈니스를 통해 수익창출                              
        #          ② 부분 유료화 수익 모델  
        #          쿠키를 결제하여 아직 연재되지 않은 에피소드를 볼 수 있음.
                
        #         > "광고 노출수" = "웹툰 조회수" = "수익 창출" 큰 상관성이 있다.

        #          ''')

        st.caption(''' LTV를 산출하기 위해 독자별 **쿠키(유료결제)를 이용 여부**를 추가했습니다. 쿠키를 결제한 유저들의 정보를 100% 알 수 없었지만 댓글 데이터를 이용하여 유추할 수 있었습니다.  
            바로 <strong style="color:#6BC55C"> '웹툰이 업로드된 날짜'와 '댓글이 작성된 날짜'를 이용</strong>하는 것이죠.
            만약, '2024-03-01'에 업로드된 작품이 있다면, 유료결제를 하지 않은 사람의 경우 업로드된 날짜 이후에 댓글을 남길 수 있습니다.  
            하지만 **쿠키를 이용하여 미리보기를 한 유저의 경우 업로드 날짜(2024-03-01) 이전에 웹툰을 보고 댓글을 작성**했을 것입니다! <strong style="color:#6BC55C">즉, '웹툰이 게시된 날짜' > '댓글이 작성된 날짜'인 경우 '쿠키를 사용한 독자' 로 판단</strong>했습니다. 
            ''', unsafe_allow_html=True)

        info = main_data.drop_duplicates(subset=['episode'])[['chapter','episode','upload_at']]
        ltv_df = pd.merge(comment_data, info, on='episode',how='left')
        ltv_df['cookie'] = np.where(ltv_df['comment_date'] < ltv_df['upload_at'], 12000, 0)
        ltv_df['price'] = ltv_df['cookie'] + ltv_df['comment_like'] + 500 

        current_date = ltv_df['comment_date'].max()
        ltv_df['comment_date'] = pd.to_datetime(ltv_df['comment_date']).dt.date


        metrics_df = summary_data_from_transaction_data(ltv_df
                                                , customer_id_col = 'user_id'
                                                , datetime_col = 'comment_date'
                                                , monetary_value_col='price'
                                                , observation_period_end=current_date).reset_index()




        # 약 8개월(240) 데이터, holdout_Days 1/8
        # train, test set 분리 -  liftime 에서는 calibration/holdout 으로 분리한다.(명칭만 다르다)
        holdout_days = 30
        calibration_end_date = current_date - datetime.timedelta(days = holdout_days)

        metrics_cal_df = calibration_and_holdout_data(ltv_df
                                                ,customer_id_col = 'user_id'
                                                ,datetime_col = 'comment_date'
                                                ,calibration_period_end=calibration_end_date # train 데이터 기간
                                                ,observation_period_end=current_date         # 끝 기간
                                                ,monetary_value_col='price')

        # frequency가 0인 것은 제외하기
        whole_filtered_df = metrics_df[metrics_df.frequency > 0]
        filtered_df       = metrics_cal_df[metrics_cal_df.frequency_cal > 0]


        # 평가 지표: default는 MSE
        def score_model(actuals, predicted, metric='mse'):

            metric = metric.lower()

            # MSE / RMSE
            if metric=='mse' or metric=='rmse':
                val = np.sum(np.square(actuals-predicted))/actuals.shape[0]
            elif metric=='rmse':
                val = np.sqrt(val)
            # MAE
            elif metric=='mae':
                val = np.sum(np.abs(actuals-predicted))/actuals.shape[0]
            else:
                val = None

            return val

        # BG/NBD 모형 평가
        def evaluate_bgnbd_model(param,data):

            l2_reg = param

            # 모형 적합
            model = BetaGeoFitter(penalizer_coef=l2_reg)
            model.fit(data['frequency_cal'], data['recency_cal'], data['T_cal'])

            # 모형 평가
            frequency_actual = data['frequency_holdout']
            frequency_predicted = model.predict(data['duration_holdout']
                                                , data['frequency_cal']
                                                , data['recency_cal']
                                                , data['T_cal']
                                            )
            mse = score_model(frequency_actual, frequency_predicted, 'mse')

            return {'loss': mse, 'status': STATUS_OK}

        # Gamma/Gamma 모델 평가
        def evaluate_gg_model(param,data):

            l2_reg = param

            # GammaGamma 모형 적합
            model = GammaGammaFitter(penalizer_coef=l2_reg)
            model.fit(data['frequency_cal'], data['monetary_value_cal'])

            # 모형 평가
            monetary_actual = data['monetary_value_holdout']
            monetary_predicted = model.conditional_expected_average_profit(data['frequency_holdout'], data['monetary_value_holdout'])
            mse = score_model(monetary_actual, monetary_predicted, 'mse')

            # return score and status
            return {'loss': mse, 'status': STATUS_OK}


        # BG/NBD 최적 L2 penalty
        @st.cache_resource
        def best_L2_penalty(filtered_df):
            def evaluate_bgnbd_wrapper(param):
                return evaluate_bgnbd_model(param, filtered_df)
            def evaluate_gg_wrapper(param):
                return evaluate_gg_model(param, filtered_df)

            search_space = hp.uniform('l2', 0.0, 1.0)
            algo = tpe.suggest
            trials = Trials()

            argmin_bgnbd = fmin(
                fn=evaluate_bgnbd_wrapper,
                space=search_space,
                algo=algo,
                max_evals=100,
                trials=trials
            )
            
            # GammaGamma 최적 L2 penalty
            trials = Trials()
            argmin_gg = fmin(
            fn = evaluate_gg_wrapper,
            space = search_space,
            algo = algo,
            max_evals=100,
            trials=trials
            )

            l2_bgnbd = space_eval(search_space, argmin_bgnbd)
            l2_gg = space_eval(search_space, argmin_gg)

            return l2_bgnbd, l2_gg
        
        # L2 penalty를 적용하여 각각을 모델링
        @st.cache_resource
        def bgnbd_model(l2_bgnbd):
            lifetimes_model = BetaGeoFitter(penalizer_coef=l2_bgnbd) #l2_bgnbd = hyperopt로 나온 결과적용
            # calibration 데이터의 R,F,T로 모형 적합
            lifetimes_model.fit(filtered_df['frequency_cal'], filtered_df['recency_cal'], filtered_df['T_cal']) 

            # holdout 데이터로 모델 평가: F의 실제값과 예측값의 MSE
            frequency_actual = filtered_df['frequency_holdout']
            frequency_predicted = lifetimes_model.predict(filtered_df['duration_holdout']
                                                ,filtered_df['frequency_cal']
                                                , filtered_df['recency_cal']
                                                , filtered_df['T_cal'])
            frequency_mse = score_model(frequency_actual, frequency_predicted, 'mse')
            return lifetimes_model, frequency_mse  #st.write('구매횟수에대한 제곱오차: {0}'.format(frequency_mse))

        @st.cache_resource
        def gg_model(l2_gg):

            # gammagamma 모델을 이용하여 미래 구매 금액 구하기
            spend_model = GammaGammaFitter(penalizer_coef=l2_gg)
            spend_model.fit(filtered_df['frequency_cal'], filtered_df['monetary_value_cal'])
            # conditional_expected_average_profit: 고객별 평균 구매 금액 예측
            monetary_actual = filtered_df['monetary_value_holdout']
            monetary_predicted = spend_model.conditional_expected_average_profit(filtered_df['frequency_holdout']
                                                                                ,filtered_df['monetary_value_holdout'])

            monetary_mse = score_model(monetary_actual, monetary_predicted, 'mse')
            return spend_model, monetary_mse

        # l2_bgnbd, l2_gg = best_L2_penalty(filtered_df)
        lifetimes_model, frequency_mse= bgnbd_model(0.001322590266385021) # BG/NBD l2 페널티값
        spend_model, monetary_mse = gg_model(0.0018085768788633095) #  GammaGamma l2 페널티값





        col1,col2 = st.columns([1,2])
        with col1:
            st.markdown('''##### 📁쿠키를 사용한 유저의 테이블(일부) ''')

            expander = st.expander('독자 Price 기준')
            with expander:
                st.caption('''
                        아래의 테이블을 보면 연재가 되기전에 댓글이 작성된 것을 볼 수 있습니다. 또한 Monetary 산출을 위한 유저 사용 금액(price)을 다음과 같이 정의 했습니다.
                        
                        * 쿠키 1개 이용 = 12000원의 가치 (극적인 값을 위해)                                              
                        * 받은 좋아요 = 개당 1원의 가치  
                        * 댓글 작성수 = 개당 500원의 가치  
                           
                        유료결제 뿐만 아니라 '댓글'과 '댓글 좋아요' 또한 작품의 관심, 인기도에 영향을 미치는 중요한 지표라고 생각합니다.
                        가장 먼저 보여지는 베스트 댓글을 보고 또 다른 댓글을 남기기도 하고, 좋아요를 누르기도 하면서 독자들의 참여도를 이끌어 내는 지표라고 생각했기 때문에 금액으로 환산하여 집계 했습니다.
                        ''')
        
                st.write(ltv_df[ltv_df['cookie'] == 12000][['episode','upload_at','user_id','comment_date','comment_like','cookie','price']].sample(5))

            # 좋아요가 많다는 것은 독자들이 해당 댓글에 공감하고, 동조할 확률이 높다는 자료가 있다. 해당 작품에 영향을 미치는 중요한 지표라고 생각되었습니다.
            # 베스트댓글에 또 다른 댓글을 남기기도 하고, 좋아요를 눌르기도하는 이런 독자들의 참여도를 이끌어 낼 수 있는 지표라고 생각했기 때문에 금전적인 가치가 어느정도 있다고 판단했습니다.



        ### LTV 테이블
        with col2:
            st.markdown('''##### 📁LTV 테이블 ''')
            expander = st.expander('LTV 산출 방법')
            with expander:
                st.caption(f'''
                            BG/NBD, GammaGamma 모델을 이용하여 8개월 동안의 LTV, 예상 구매횟수 및 금액을 산출해보았습니다. BG/NBD 모델은 
                            * Frequency : 얼마나 자주 구매(참여) 했는지 
                            * Recency : 최근에 구매(참여) 했는지 
                            *  T : 고객별 첫 구매(참여) ~ 집계일까지의 시간
                            * 예측 구매 횟수의 평균 제곱오차 : ±{round(frequency_mse,3)}일
                            * 예측 구매 금액의 평균 제곱오차 : ±{round(monetary_mse,3)}원
                            * 산출된 LTV 값에 따라 (상위20%) diamond , (20-40) platinum, (40-60) gold, (나머지) silver
                        ''')



                final_df = whole_filtered_df.copy() #  전체 데이터를 대상으로 LTV산출
                final_df['ltv'] = spend_model.customer_lifetime_value(lifetimes_model,
                                                                    final_df['frequency'],
                                                                    final_df['recency'],
                                                                    final_df['T'],
                                                                    final_df['monetary_value'],
                                                                    time=8, # 몇개월 동안의 ltv를 볼것인지 , 8개월 
                                                                    #discount_rate=0.01 # monthly discount rate ~12.7% 연간
                                                                    )


                # 8개월 동안의 예상 구매횟수
                t=240 
                final_df['predicted_purchases'] = lifetimes_model.conditional_expected_number_of_purchases_up_to_time(t
                                                                                                    , final_df['frequency']
                                                                                                    , final_df['recency']
                                                                                                    , final_df['T'])
                # 8개월 동안의 예상 구매금액
                final_df['predicted_monetary_value'] = spend_model.conditional_expected_average_profit(final_df['frequency']
                                                                                    ,final_df['monetary_value'])


                # 4분위수로 나눠서 독자들을 분리
                final_df['segment'] = 0 # pd.qcut(final_df['ltv'], 5 , labels=['bronze','silver', 'gold','platinum','diamond'])
                # ltv 기준으로 분위수 계산
                quantiles = final_df['ltv'].quantile([0.8, 0.6, 0.4])
                final_df.loc[final_df['ltv'] >= quantiles.iloc[0], 'segment'] = 'diamond'
                final_df.loc[final_df['ltv'].between(quantiles.iloc[1], quantiles.iloc[0]), 'segment'] = 'platinum'
                final_df.loc[final_df['ltv'].between(quantiles.iloc[2], quantiles.iloc[1]), 'segment'] = 'gold'
                final_df.loc[final_df['ltv'] <= quantiles.iloc[2], 'segment'] = 'silver'


                # 이외 여러 컨셉들로 분리도 해보자. 
                # 예를 들어, 최근에 댓글 및 쿠키를 사용한 독자들인 경우(lookie) ltv에 산출된 예산에 따라서 어떤 마케팅을 할 수 있을지 전략을 세 울 수 있단말이죠?

                final_df = pd.merge(final_df,user_timeinfo,on='user_id',how='inner')
                final_df['morning_ratio'] = round(final_df['morning']/(final_df['morning'] + final_df['day'] + final_df['night']) * 100)
                final_df['day_ratio'] = round(final_df['day']/(final_df['morning'] + final_df['day'] + final_df['night']) * 100)
                final_df['night_ratio'] = round(final_df['night']/(final_df['morning'] + final_df['day'] + final_df['night']) * 100)            

                st.write(final_df)
            
            def hist (final_df):
                fig, axes = plt.subplots(1, 4, figsize=(16, 4))
                # M_top20_per = np.percentile(final_df['monetary_value'], 90)
                axes[0].hist(final_df['monetary_value'], bins=20, alpha=0.5, color='blue', label='Monetary')
                # axes[0].axvline(x=M_top20_per, color='red', linestyle='--', label='Top 10%')
                axes[0].set_title('Monetary Distribution')
                axes[0].legend()

                # frequency
                # F_top20_per = np.percentile(final_df['frequency'], 80)
                axes[1].hist(final_df['frequency'], bins=20, alpha=0.5, color='blue', label='Frequency')
                # axes[1].axvline(x=F_top20_per, color='red', linestyle='--', label='Top 20%')
                axes[1].set_title('frequency Distribution')
                axes[1].legend()

                # Recency
                # R_top20_per = np.percentile(final_df['recency'], 80)
                axes[2].hist(final_df['recency'], bins=20, alpha=0.5, color='blue', label='Recency')
                # axes[2].axvline(x=R_top20_per, color='red', linestyle='--', label='Top 20%')
                axes[2].set_title('Recency Distribution')
                axes[2].legend()


                L_top20_per = np.percentile(final_df['monetary_value'], 80)
                axes[3].hist(final_df['ltv'], bins=20, alpha=0.5, color='blue', label='LTV')
                axes[3].axvline(x=L_top20_per, color='red', linestyle='--', label='Top 20%')
                axes[3].set_title('LTV Distribution')
                axes[3].legend()


                plt.tight_layout()
                st.pyplot(fig)

            hist(final_df)





    with st.container():
        st.subheader('📊 독자 세그먼트 EDA')
        # 세그먼트별로 

        st.write(''' 
                프로모션을 진행할시에 반응할 확률이 높은 독자는 누구일까요? 산출된 고객 생애 가치(LTV)와 서비스를 주로 이용하는 시간대를 나눠서 아래와 같이 우선순위를 정해보았습니다.  
                * ltv가 높고 오전 혹은 낮에 이용하는 독자 (출근 이벤트: 등교, 출근하는 시간대에 맞춘 n분 무료보기 및 쿠키 조조할인)  
                * ltv는 낮지만 오전 혹은 낮에만 이용하는 독자                 
                ''')
        st.caption(''' 밤에만 혹은 낮/오전에만 웹툰을 이용하는 독자들이 있었습니다. ''')

        
        dia_user = final_df.groupby(['segment']).agg(
            monetary_value = pd.NamedAgg(column='monetary_value',aggfunc='mean'),
            ltv = pd.NamedAgg(column='ltv',aggfunc='mean'),
            morning = pd.NamedAgg(column='morning',aggfunc='sum'),
            day = pd.NamedAgg(column='day',aggfunc='sum'),
            night = pd.NamedAgg(column='night',aggfunc='sum')

        )

        col1, col2 = st.columns([1,4])
        with col1:
            st.write(dia_user)
        with col2:
            high_user = final_df[final_df['segment'].isin(['diamond','platinum'])]
            morning_day_user = high_user[(high_user['morning_ratio'] >= 30) | (high_user['day_ratio'] >= 30)]
            all_user = final_df[(final_df['morning_ratio'] >= 30) | (final_df['day_ratio'] >= 30)]


            # st.write(high_user)
            st.write(f''' 
                     전체 유니크한 독자 : {len(final_df)}명  
                     아침/낮에 감상 비율이 30% 이상인 독자 : {len(all_user)}명   
                     아침/낮에 감상 비율이 30% 이상이고 LTV가 Platinum 이상인 독자: {len(morning_day_user)}''')

            # with col2:
            # monetary



    # with st.container():




        # import plotly.graph_objects as go

        # bronze_group = final_df[final_df['segment'] == 'bronze']
        # silver_group = final_df[final_df['segment'] == 'silver']
        # gold_group = final_df[final_df['segment'] == 'gold']        
        # platinum_group = final_df[final_df['segment'] == 'platinum']
        # diamond_group = final_df[final_df['segment'] == 'diamond']

        # # Plotly subplot 그래프 생성
        # fig = go.Figure()
        # # Monetary subplot
        # fig.add_trace(go.Histogram(x=diamond_group['monetary_value'], name='diamond'))
        # # Frequency subplot
        # fig.add_trace(go.Histogram(x=platinum_group['monetary_value'], name='platinum'))
        # # Recency subplot
        # fig.add_trace(go.Histogram(x=gold_group['monetary_value'], name='gold'))

        # # 그래프 레이아웃 설정
        # fig.update_layout(title='Distribution of Monetary',
        #                 barmode='overlay')

        # # Streamlit에 그래프 표시
        # st.plotly_chart(fig)

        # st.markdown(''' 
        #     #### ② 목표를 부여하여 독자들의 참여도 올리기  
        #     웹툰 수익구조에 따르면 조회수 그리고 독자들의 참여도가 굉장히 중요하다는 것을 알 수 있습니다. 
        #     산출된 ltv 로 나눠진 세그먼트에 따라 열혈독자, 일반독자 랭크를 눈에 보이게 부여하면 어떨까요? 열혈독자를 달기 위한 일종의 목표를 만들어 줌으로써 기존의 기여도가 높은 독자 뿐만 아니라 다른 독자들의 참여도를 높히는것 입니다!
        #     게임처럼 LTV 수치가 일종에 경험치가 되고, 이는 독자의 참여도(댓글, 좋아요, 베스트 댓글 ,쿠키 사용 등)를 통해 등급이 올라 감으로서 성취감을 느끼게 한다면 독자들의 참여도가 더 높아질 수 있습니다.
            
        #     ''')


    st.divider()

    # 쿠키가 가장 많이 사용된 에피소드와 관련   
    with st.container():
            
            # uploaded_file = pd.read_csv('csv_data/waktaverse_benefit.csv')
            st.subheader('🍪 Episode By Cookie')
            st.caption(''' 쿠키사용량이 높았던 에피소드의 특징은 무엇일까요? 에피소드별(x:업로드된 날짜) 쿠키 사용량을 시각화하여 가장 가치가 높았던 에피소드를 찾아보고 독자들의 니즈를 파악해보았습니다.''')    
         
            cookie_by_ep = ltv_df.groupby(['chapter','episode','upload_at']).agg(
                total_cookie = pd.NamedAgg(column='cookie', aggfunc='sum')            
            ).reset_index().sort_values(by=['upload_at'])

            cookie_by_ep['upload_at'] = pd.to_datetime(cookie_by_ep['upload_at']).dt.strftime('%Y-%m-%d')
            # cookie_by_ep['month'] = pd.to_datetime(cookie_by_ep['upload_at']).dt.strftime('%Y-%m')

            mean_cookie = round(cookie_by_ep['total_cookie'].mean())

           # 데이터 변환
            nivo_data_cookie = []
            for index, row in cookie_by_ep.iterrows():
                nivo_data_cookie.append({'x': row['upload_at'], 'y': row['total_cookie']})

            nivo_data_cookie = [{
                "id": "cookie",
                "data": nivo_data_cookie
            }]
            

            top_cookie = cookie_by_ep.sort_values(by=['total_cookie'],ascending=False)
            recent_data  = main_data[main_data['down_at'] =='2024-03-06'][['episode','like_count','comment_count','score']] # 240306 기준의 에피소드 정보 결합
            top_cookie = pd.merge(top_cookie,recent_data,on='episode',how='inner') 



            col1,col2 = st.columns([3,3])
            with col1:
                st.markdown('''##### 📈 Cookie Chart''')

                with elements("cookie chart"):
                            layout = [
                                dashboard.Item("item_1", 0, 0, 6, 2),
                                dashboard.Item("item_2", 0, 2, 2, 1.8),
                                dashboard.Item("item_3", 2, 2, 2, 1.8),
                                dashboard.Item("item_4", 4, 2, 2, 1.8),

                            ]

                            with dashboard.Grid(layout):                                                            
                                mui.Box(                                        
                                    nivo.Line(
                                        data= nivo_data_cookie,
                                        margin={'top': 30, 'right': 30, 'bottom': 30, 'left': 60},
                                        # xScale={'type': 'point',
                                        #         },

                                        curve="monotoneX",
                                        axisTop=None,
                                        axisRight=None,
                                        axisBottom={
                                            'format': '%y-%m-%d',  # '%Y-%m-%d'
                                            'legendOffset': -12,
                                            'tickValues': 'every 30 days'
                                        },
                                        xFormat="time:%Y-%m-%d",
                                        xScale={
                                            'format': '%Y-%m-%d',
                                            'precision': 'day',
                                            'type': 'time',
                                            # 'useUTC': False
                                        },
                                        colors= {'scheme': 'accent'},

                                        enableGridX = False,
                                        enableGridY = False,
                                        enableArea = True,
                                        areaOpacity = 0.2,
                                        # enablePointLabel=True,
                                        # pointLabel='y',
                                        lineWidth=2,
                                        pointSize=3,
                                        pointColor='white',
                                        pointBorderWidth=0.5,
                                        pointBorderColor={'from': 'serieColor'},
                                        pointLabelYOffset=-12,
                                        useMesh=True,
                                        legends=[
                                                    {
                                                    'anchor': 'top-left',
                                                    'direction': 'column',
                                                    'justify': False,
                                                    # 'translateX': -30,
                                                    # 'translateY': -200,
                                                    'itemsSpacing': 0,
                                                    'itemDirection': 'left-to-right',
                                                    'itemWidth': 80,
                                                    'itemHeight': 15,
                                                    'itemOpacity': 0.75,
                                                    'symbolSize': 12,
                                                    'symbolShape': 'circle',
                                                    'symbolBorderColor': 'rgba(0, 0, 0, .5)',
                                                    'effects': [
                                                            {
                                                            'on': 'hover',
                                                            'style': {
                                                                'itemBackground': 'rgba(0, 0, 0, .03)',
                                                                'itemOpacity': 1
                                                                }
                                                            }
                                                        ]
                                                    }
                                                ],                            
                                        theme={
                                                # "background-color": "rgba(158, 60, 74, 0.2)",
                                                "textColor": "black",
                                                "tooltip": {
                                                    "container": {
                                                        "background": "#3a3c4a",
                                                        "color": "white",
                                                    }
                                                }
                                            },
                                        markers=[{                                                
                                            'axis': 'y',
                                            'legend': 'mean',
                                            'lineStyle': {
                                                'stroke': '#b0413e',
                                                'strokeWidth': 1
                                            },
                                            'value': mean_cookie                                              
                                        }] ,                                             
                                        animate= False)
                                        ,key="item_1",sx={"borderRadius":"15px", "borderRadius":"15px","background-color":"#F0F2F6"}) 

                                mui.Card( # 썸네일,좋아요,댓글,링크           
                                    children=[      
                                        mui.Typography(
                                            f"🥇 {top_cookie['upload_at'].iloc[0]}",
                                            color="text.secondary",
                                            sx={"font-size": "14px",
                                                # "fontWeight":"bold",
                                                "text-align":"left",
                                                "padding-left":"12px",
                                                "padding-top" : "2px"
                                                },                                            
                                        ),
                                        mui.CardMedia( # 썸네일 이미지
                                            sx={ "height": 150,
                                                "ovjectFit":"cover",
                                                "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://image-comic.pstatic.net/webtoon/811721/67/thumbnail_202x120_dd2e1d7e-c605-43ba-b9d5-5df6e80b95b4.jpg)",
                                                # "borderRadius": '5%', 
                                                "backgroundPosition": "top 80%",
                                                # "border": "1.5px solid white",  # 흰색 경계선 추가
                                                },                                
                                            title = '썸네일'
                                                ),
                
                                        mui.CardContent(  # 타이틀 
                                            sx={"padding-top": "10px",
                                                "padding-bottom":"10px",
                                                "max-height": "100%",
                                                "overflow": "hidden"},

                                                children=[
                                                    mui.Typography( # title
                                                        f"{top_cookie['episode'].iloc[0]}",
                                                        component="div",
                                                        sx={"font-size":"16px",
                                                            "fontWeight":"bold",
                                                            "height":"45px",
                                                            "max-height": "100%",
                                                            # "overflow": "hidden",
                                                            }                            
                                                    )],

                                            ),
                                                                            
                                        mui.CardContent( # 댓글 좋아요 링크
                                            sx={"display": "flex",
                                                "padding-top": "0",
                                                "padding-bottom":"0",
                                                "gap": "60px",
                                                "align-items": "center", # "position": "fixed"
                                                },
                                                
                                            children=[

                                                mui.Typography(
                                                        f"❤️ {top_cookie['like_count'].iloc[0]} 댓글 {top_cookie['comment_count'].iloc[0]} ",
                                                        variant="body2",
                                                        sx={"font-size": "12px"},                                            
                                                    ),

                                                mui.Link(
                                                    "📖Webtoon",
                                                    href=f"https://comic.naver.com/webtoon/detail?titleId=811721&no={top_cookie['chapter'].iloc[0]}",
                                                    target="_blank",
                                                    sx={"font-size": "12px",
                                                        "font-weight": "bold",
                                                        }
                                                ),
                                            ]
                                        ),
                                        
                                        ] 
                                        ,key="item_2",sx={"background-color" : "#F0F2F6", "background-size" : "cover","borderRadius": '20px'})

                                mui.Card( # 썸네일,좋아요,댓글,링크           
                                    children=[      
                                        mui.Typography(
                                            f"🥈 {top_cookie['upload_at'].iloc[1]}",
                                            color="text.secondary",
                                            sx={"font-size": "14px",
                                                # "fontWeight":"bold",
                                                "text-align":"left",
                                                "padding-left":"12px",
                                                "padding-top" : "2px"
                                                },                                            
                                        ),
                                        mui.CardMedia( # 썸네일 이미지
                                            sx={ "height": 150,
                                                "ovjectFit":"cover",
                                                "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://image-comic.pstatic.net/webtoon/811721/78/thumbnail_202x120_605ae5f8-d2ff-400e-b175-d61e3b68d737.jpg)",
                                                "backgroundPosition": "top 80%",
                                                # "border": "1.5px solid white",  # 흰색 경계선 추가
                                                },                                
                                            title = '썸네일'
                                                ),
                
                                        mui.CardContent(  # 타이틀 
                                            sx={"padding-top": "10px",
                                                "padding-bottom":"10px",
                                                "max-height": "100%",
                                                "overflow": "hidden"},

                                                children=[
                                                    mui.Typography( # title
                                                        f"{top_cookie['episode'].iloc[1]}",
                                                        component="div",
                                                        sx={"font-size":"16px",
                                                            "fontWeight":"bold",
                                                            "height":"45px",
                                                            "max-height": "100%",
                                                            # "overflow": "hidden",
                                                            }                            
                                                    )],

                                            ),
                                                                            
                                        mui.CardContent( # 댓글 좋아요 링크
                                            sx={"display": "flex",
                                                "padding-top": "0",
                                                "padding-bottom":"0",
                                                "gap": "60px",
                                                "align-items": "center", # "position": "fixed"
                                                },
                                                
                                            children=[

                                                mui.Typography(
                                                        f"❤️ {top_cookie['like_count'].iloc[1]} 댓글 {top_cookie['comment_count'].iloc[1]} ",
                                                        variant="body2",
                                                        sx={"font-size": "12px"},                                            
                                                    ),

                                                mui.Link(
                                                    "📖Webtoon",
                                                    href=f"https://comic.naver.com/webtoon/detail?titleId=811721&no={top_cookie['chapter'].iloc[1]}",
                                                    target="_blank",
                                                    sx={"font-size": "12px",
                                                        "font-weight": "bold",
                                                        }
                                                ),
                                            ]
                                        ),
                                        
                                        ] 
                                        ,key="item_3",sx={"background-color" : "#F0F2F6", "background-size" : "cover","borderRadius": '20px'})

                                mui.Card( # 썸네일,좋아요,댓글,링크           
                                    children=[      
                                        mui.Typography(
                                            f"🥉 {top_cookie['upload_at'].iloc[2]}",
                                            color="text.secondary",
                                            sx={"font-size": "14px",
                                                "text-align":"left",
                                                "padding-left":"12px",
                                                "padding-top" : "2px"
                                                },                                            
                                        ),
                                        mui.CardMedia( # 썸네일 이미지
                                            sx={ "height": 150,
                                                "ovjectFit":"cover",
                                                "backgroundImage": f"linear-gradient(rgba(0, 0, 0, 0), rgba(0,0,0,0.5)), url(https://image-comic.pstatic.net/webtoon/811721/76/thumbnail_202x120_8cb1fe5a-8ab4-422b-a398-8a43f5deb29e.jpg)",
                                                # "borderRadius": '5%', 
                                                "backgroundPosition": "top 80%",
                                                # "border": "1.5px solid white",  # 흰색 경계선 추가
                                                },                                
                                            title = '썸네일'
                                                ),
                
                                        mui.CardContent(  # 타이틀 
                                            sx={"padding-top": "10px",
                                                "padding-bottom":"10px",
                                                "max-height": "100%",
                                                "overflow": "hidden"},

                                                children=[
                                                    mui.Typography( # title
                                                        f"{top_cookie['episode'].iloc[2]}",
                                                        component="div",
                                                        sx={"font-size":"16px",
                                                            "fontWeight":"bold",
                                                            "height":"45px",
                                                            "max-height": "100%",
                                                            # "overflow": "hidden",
                                                            }                            
                                                    )],

                                            ),
                                                                            
                                        mui.CardContent( # 댓글 좋아요 링크
                                            sx={"display": "flex",
                                                "padding-top": "0",
                                                "padding-bottom":"0",
                                                "gap": "60px",
                                                "align-items": "center", # "position": "fixed"
                                                },
                                                
                                            children=[

                                                mui.Typography(
                                                        f"❤️ {top_cookie['like_count'].iloc[2]} 댓글 {top_cookie['comment_count'].iloc[2]} ",
                                                        variant="body2",
                                                        sx={"font-size": "12px"},                                            
                                                    ),

                                                mui.Link(
                                                    "📖Webtoon",
                                                    href=f"https://comic.naver.com/webtoon/detail?titleId=811721&no={top_cookie['chapter'].iloc[2]}",
                                                    target="_blank",
                                                    sx={"font-size": "12px",
                                                        "font-weight": "bold",
                                                        }
                                                ),
                                            ]
                                        ),
                                        
                                        ] 
                                        ,key="item_4",sx={"background-color" : "#F0F2F6", "background-size" : "cover","borderRadius": '20px'})




            with col2:
                st.markdown('''### 🤔 가설  ''')
                st.write(''' 
                    긴 시리즈의 에피소드일수록 쿠키 사용량이 높을까요? 하루분량으로 끝나는 단편 스토리와 반대로 긴 시리즈의 에피소드의 경우
                    독자들의 입장에서 뒷 내용이 더 궁금할 수 있지 않을까 생각이 들었습니다.                         
                    ''')
                st.caption('''
                    초기에 미리보기할 웹툰이 없다는 점을 고려하여 cookie 가 0 인 데이터는 제외하였습니다.
                         ''')

                # 제목 형식에 ' : ' 를 기준으로 분리
                # \s* 공백 \(\d+\) 괄호안의 숫자 제거

                cookie_by_ep['title'] = cookie_by_ep['episode'].apply(lambda x: re.sub(r'\s*\(\d+\)$', '', x.split(':')[1]).strip()) 
                cookie_by_ep.loc[cookie_by_ep['chapter'] == '67', 'title'] = cookie_by_ep.loc[cookie_by_ep['chapter'] == '67', 'title'].str[:4]

                cookie_by_ep = cookie_by_ep[cookie_by_ep['total_cookie'] > 0]
                group = cookie_by_ep.groupby(['title']).agg(
                    cookie_mean = pd.NamedAgg(column='total_cookie',aggfunc='mean'),
                    series_cnt = pd.NamedAgg(column='episode',aggfunc='count'),
                ).reset_index()

                group_1 = group[group['series_cnt'] > 1]['cookie_mean']
                group_2 = group[group['series_cnt'] != 1 ]['cookie_mean']

      
                c1,c2 = st.columns([1,1])
                with c1:            
                    st.markdown('''##### ① 정규성 및 등분산성 확인''')

                    # 정규성검정
                    fig = plt.figure(figsize=(8, 6))
                    sns.histplot(group['cookie_mean'], kde=True, color='blue', bins=10)
                    plt.title('Density Plot of cookie')
                    plt.xlabel('cookie_mean')
                    plt.ylabel('Density')
                    st.pyplot(fig)
 
 
                     # 등분산성 검정
                    _, p_levene = levene(group_1, group_2)
                    st.write(f'''
                              * Levene's p_value : {p_levene}  ''') 


                with c2:                    
                    st.markdown('''##### ② 독립 표본 t-검정 ''')
                    # 독립표본 t-검정
                    t_statistic, p_value = ttest_ind(group_1, group_2)

                    # 결과 출력
                    st.write(f'''
                             * 검정결과 아쉽게도 시리즈 형태의 에피소드 라고 쿠키 사용량이 높다라고 볼 수는 없었습니다.
                             * 단순히 시리즈의 길이 보다 해당 에피소드의 '재미도','서비스신' 같은 요소들이 쿠키 사용량에 따라 차이가 있지 않을까 생각이 들었습니다.
                             * 또한 해당 웹툰의 경우 꾸준히 쿠키사용량이 증가하고 있는 추세입니다. 초기에 나온 에피소드와 현재의 에피소드를 같이 비교하기에는 한계가 있다고 생각이 들었습니다.
                             * T-statistic : {t_statistic}  
                             P-value : {p_value}                               

                             
                                                         ''')
 

            # st.markdown('''
            #             ##### ① 장르 반전
            #             가장 높은 cookie 점수를 달성한 매너리즘 에피소드의 경우 해당 웹툰의 '1부 마무리'라는 이벤트의 영향도 있지만 
            #             그 동안 단순히 가벼운 개그물로 보아왔던 작품안에서 '진지함' '감동' 이라는 장르의 반전을 추가하면서 독자들에게 큰 인상을 준것을 알 수 있습니다.
                        
            #             ##### ② 서비스신
            #             무직백수 계백순 웹툰의 경우 작화, 캐릭터가 예쁘다는 큰 매력 포인트가 있습니다. 특히, 78화: 초대(1)의 에피소드의 경우 이를 극대화 하는 서비스 장면이 추가 되면서 독자들의 큰 반응을 이끈것으로 보입니다.
                            
            #             ##### ③ 그냥 웃기다.
            #             이 외에 '개그' 장르 답게 독자들의 웃음 코드를 잘 살리는 에피소드의 경우 독자들의 반응이 좋은것을 볼 수 있습니다.

            #             ''')
