# dashboard
import streamlit as st
from streamlit_elements import dashboard
from streamlit_elements import nivo, elements, mui, media

# data 
import pandas as pd
import re
import time
import datetime
from tqdm import tqdm
from stqdm import stqdm

from lifetimes.plotting import *
from lifetimes.utils import *

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
st.caption(now_time) #.strftime('%Y-%m-%d %H:%M'))


# 웹브라우저를 열지 않고 크롤링 하려면 headless 옵션을 주면 된다.

chrome_options = Options()
chrome_options.add_argument('--headless')  # 웹 브라우저를 헤드리스 모드로 실행할 경우 추가
driver = webdriver.Chrome(options=chrome_options) # options=chrome_options

# 에피소드별 댓글 정보 (user_nick, comment_date)
def get_comment_by_ep(start,end):
    result_list = []

    for i in stqdm(range(start, end + 1)):

        driver.get(f"https://comic.naver.com/webtoon/detail?titleId=811721&no={i}")
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
                comment_dates = driver.find_elements(By.CLASS_NAME, 'u_cbox_date')
                comment_likes = driver.find_elements(By.CLASS_NAME, 'u_cbox_cnt_recomm')
                comment_dislikes = driver.find_elements(By.CLASS_NAME,'u_cbox_cnt_unrecomm')
            except Exception as e:
                # 더 이상 더보기 버튼이 없으면 예외 발생하고 반복문 탈출
                break


        # 유저 아이디는 남지만 클린봇에 의해 댓글이 삭제되는 경우가 있음. 
        comment_data = {
            'episode': episode_title,
            'user_id': [],
            'comment_date': [],
            'comment_like': [],
            'comment_dislike': []
        }

        for user_id, comment_date, comment_like, comment_dislike in zip(user_ids ,comment_dates, comment_likes, comment_dislikes):
            try:
                # comment_like, comment_dislike가 없는 경우를 처리하기 위해 int()를 사용하여 변환
                comment_data['user_id'].append(user_id.text)
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
            submit_search = st.form_submit_button('GCS DATA')
            scraping = st.form_submit_button('댓글 데이터 수집')

# 데이터 불러오기
if submit_search:
    comment_data = load_data(data_folder[0])
    main_data = load_data(data_folder[1])

    st.session_state.comment_data = comment_data
    st.session_state.main_data = main_data


# 댓글 데이터 수집.

start = 51
end = 60

if scraping:
    data = get_comment_by_ep(start,end)
    st.session_state.data = data

if hasattr(st.session_state, 'data'):
   data = st.session_state.data 


if st.button('Download to CSV'):
    # 파일 경로 및 파일명 설정
    file_path = f'C:\webtoon\comment_data(ep{start}~{end}).csv'  
    data.to_csv(file_path, index=False,encoding='utf-8-sig')
    st.success("Success")




st.subheader(''' 
            🖥️ 분석해 볼만한 과제들
            ''')
st.write(''' 
        ##### ① 특정 에피소드의 트래픽 증가 원인 분석        
        * Dau, wau, mau의 변동성에 영향을 준 시점이 있을까? 그리고 영향을 준 특정 에피소드가 있다면? 
        * 월별 Stickiness는 차트를 만들어보자. 독자들의 고착도가 증가하고 있는지 확인할 수 있다. 만약 증가하는 추세가 보인다면 언제부터 였을까?
        * 웹툰이 시즌마다 어떻게 변화하는지를 분석하여, 각 시즌의 특징과 독자들의 참여도의 변동을 분석해보자.

        ##### ② 같은 장르간 웹툰 비교
        * 같은 장르의 다른 작품들과 비교 하고 싶은데, 그러기 위해서는 댓글 데이터를 작품별로 수집해야한다. 이게 꽤 시간이 많이걸린다..        

        ##### ③ 댓글을 활용한 분석
        * vip 멤버를 구해보자! (참여도가 가장 높은 찐팬 독자) Recency Frequency 를 기준으로.. (monetray의 경우 공감수+ 댓글수 로 대체)
 
        ''' )



if hasattr(st.session_state, 'main_data'):
    main_data = st.session_state.main_data
    st.subheader('episode data')
    st.write(main_data)




if hasattr(st.session_state, 'comment_data'):
    comment_data = st.session_state.comment_data
    # comment_data = comment_data[comment_data['comment_date'].dt.date != max(comment_data['comment_date'].dt.date)]
    unique_user  = len(comment_data['user_id'].unique())  # 댓글을 담긴 유니크한 유저

    with st.container():
        st.header(''' 
                Activation User  
                ''')
        st.caption(''' 
                   * 활성화 유저의 기준은 '댓글'을 남긴 유저로 정했어요. 댓글과 좋아요는 웹툰을 보고 난 뒤, 즉 서비스를 이용했다는 가장 확실한 흔적이 라고 생각했습니다. 
                   * 그 중 에피소드별 남겨진 댓글의 아이디를 기준으로 고유 유저수를 집계 했어요🫡! 웹툰 페이지에서 구할 수 있는 댓글 정보를 이용하여 일부 필터링된 '닉네임(id***)' 이 같다면 동일 유저로 판단했습니다. 
                     
                    ''')

        # 날짜 데이터를 datetime 형식으로 변환 (요일 추출을 위해..)
        comment_data['comment_date'] = pd.to_datetime(comment_data['comment_date'], errors='coerce')
        comment_data['day_name'] = comment_data['comment_date'].dt.day_name()


        # 일자별 활성 사용자 (DAU)
        dau = comment_data.groupby([comment_data['comment_date'].dt.date,'day_name'])['user_id'].nunique().reset_index() #  'day_name'
        # 주간별 활성 사용자 (WAU)
        wau = comment_data.groupby(comment_data['comment_date'].dt.to_period('W').dt.start_time.dt.date)['user_id'].nunique().reset_index()
        # 월간별 활성 사용자 (MAU)
        mau = comment_data.groupby(comment_data['comment_date'].dt.to_period('M').dt.start_time.dt.date)['user_id'].nunique().reset_index()
            

        # 날짜별로
        # ddau = comment_data.groupby(['day_name'])['user_id'].nunique().reset_index()




        # mau = comment_data.groupby(comment_data['year'])['user_id'].nunique() 
        # datetime.date(now.year, now.month, now.day)
        
        max_date = max(comment_data['comment_date'].dt.date) - datetime.timedelta(days=1) #   
        min_date = min(comment_data['comment_date'].dt.date)
        # befor_7 = max_date - datetime.timedelta(days=7)


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


        # @st.cache_resource
        def user_active_chart (df,title,color):
            title = indication
            date_mask = (df['comment_date'] >= start_d) & (df['comment_date'] <= end_d) # date로 지정된 값들만 
            df = df.loc[date_mask]
            pivot = pd.pivot_table(df, values='user_id', index='comment_date')



            st.subheader(f'📊 {title}')
            st.line_chart(pivot, use_container_width=True,color=color)



        col1,col2 = st.columns([3,1])
        # line_chart_activation_user 
        with col1:
            
            user_active_chart(df,'📊 Daily Active User','#75D060')
    
            st.markdown(''' 
                    > * 무직백수계백순 웹툰의 경우 일요일, 수요일에 연재되는 작품입니다. 정해진 요일에만 연재되는 웹툰 특성상 요일별로 큰 변동성이 있었습니다. 
                                        
                    ''')
   

        # issue
        with col2:
            st.subheader(' ✔️Issue')

            st.markdown('''
                ##### 일별 평균 참여도
                 ''')

            st.write('''
                * 해당 주의 전체 DAU가 WAU 보다 높은 경우 : 재방문하는 독자들이 많은것으로 볼 수 있습니다.  
                * 해당 주의 전체
                
                ''')


            chort_df = comment_data.copy()
            chort_df.set_index('user_id', inplace=True)

            # 유저별 첫 참여기간 추출
            chort_df['CohortGroup'] = chort_df.groupby(level=0)['comment_date'].min().apply(lambda x: x.strftime('%Y-%m'))
            chort_df.reset_index(inplace=True)


# ------------------------------------------------------ 댓글 데이터를 기준으로 유저 고착도를 구해보자 --------------------------------------------- #




        st.header('Stickiness ')
        st.caption(''' 해당 웹툰은 아직 연재일이 1년이 안된 웹툰입니다. 또한 주에 2번 연재되는 작품 특성상 활성화 유저 또한 해당 연재일에 주로 들어오는 경향이 있기 때문에
                    wau를 나눠서 구하는것이 적절해 보였습니다.
                    ''')



        # 주간 stick 구하기 
        # 일단, 해당 요일이 어느 주인지 filter 필요
        # 해당 테이블에 wau merge   
        dau = dau.rename(columns={'user_id':'dau'})
        dau['comment_date'] = pd.to_datetime(dau['comment_date'], errors='coerce')
        dau['week'] = dau['comment_date'].dt.to_period('W').dt.start_time.dt.date

        stick_df = pd.merge(dau, wau, left_on='week', right_on='comment_date', how='inner')
        stick_df = stick_df.rename(columns={'user_id': 'wau','comment_date':'week','comment_date_x':'day'}).drop(columns=['comment_date_y']) 
        stick_df['week_stick'] = round(stick_df['dau'] / stick_df['wau'],2) * 100
        stick_df['week_stick'] = stick_df['week_stick'].astype(int)
        
        col1, col2 = st.columns([3,1])
        with col1:
            # 연재되는 날짜의 유저 고착도 구하기
            published_day = stick_df[stick_df['day_name'].isin(['Sunday','Wednesday'])]
            published_day['week'] = pd.to_datetime(published_day['week']).dt.strftime('%Y-%m-%d')

            # 평균 고착도
            mean_stick = round(published_day['week_stick'].mean())

            # 데이터 변환
            nivo_data = []
            for index, row in published_day.iterrows():
                nivo_data.append({'x': row['week'], 'y': row['week_stick']})

            nivo_data = [{
                "id": "stickness",
                "data": nivo_data
            }]


            st.markdown('''#### 연재요일  Stickness ''' )
            with st.container():       
                    with elements("playlist_line_chart"):
                        layout = [
                            dashboard.Item("item_1", 0, 0, 12, 2),
                        ]

                        with dashboard.Grid(layout):
                                                            
                                mui.Box( # 재생목록별 전체 조회수 증가량
                                       
                                        nivo.Line(
                                            data= nivo_data,
                                            margin={'top': 40, 'right': 15, 'bottom': 50, 'left': 55},
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
                    #### 요일별 평균 stickiness (막대차트)                     
                    지발님의 작품 계백순의 평균 고착도는 {mean_stick} % 입니다. 한주동안 100명중 {mean_stick}명의 독자가 꾸준히 웹툰을 보러 오고있다고 할 수 있어요!😀                       
                     ''')
            st.write(published_day)
            # stick_by_day = stick_df.groupby(['day_name']).agg(stickiness_mean = pd.NamedAgg(column='week_stick', aggfunc='mean')).reset_index()
            # stick_by_day['stickiness_mean'] =stick_by_day['stickiness_mean'].round(2)




        # total_stick = round(total_dau['stick'].sum()/ len(total_dau),2)
        # serialize_dau = total_dau[total_dau['day_name'].isin(['Sunday','Wednesday'])]
        # serialize_stick =round(serialize_dau['stick'].sum() / len(serialize_dau),2)

        # st.write(f''' 해당 하는 월의 stickiness (유저 고착도)를 구해 보았습니다!  
        #          전체 날짜를 포함한 stickiness 값은 {total_stick}% 입니다.
        #          하지만 작가님의 웹툰이 연재 되는 날짜(일요일, 수요일)를 기준으로 본다면 {serialize_stick}% 으로 약 두배가량 높습니다.
        #          ''')

        # ----------------------------------------------------- DAU , WAU, MAU 차트 ----------------------------------------------------------------------------- #



        # with st.container():  # 활성화 유저수 정보     
        #         with elements("Active_user_chart"):
        #             layout = [
        #                 dashboard.Item("item_1", 0, 0, 12, 2),
        #             ]

        #             with dashboard.Grid(layout):
                                                                                                               
        #                     mui.Box( # 
        #                         nivo.Line(
        #                             data= diff,
        #                             margin={'top': 40, 'right': 15, 'bottom': 50, 'left': 55},
        #                             xScale={'type': 'point',
        #                                     },

        #                             curve="cardinal",
        #                             axisTop=None,
        #                             axisRight=None,
        #                             # axisBottom={
        #                             #     'orient': 'bottom',
        #                             #     'tickValues': 'every 10 days',
        #                             # },
        #                             colors= {'scheme': 'accent'},
        #                             enableGridX = False,
        #                             enableGridY = False,
        #                             enableArea = True,
        #                             areaOpacity = 0.2   ,
        #                             lineWidth=2,
        #                             pointSize=3,
        #                             pointColor='white',
        #                             pointBorderWidth=0.5,
        #                             pointBorderColor={'from': 'serieColor'},
        #                             pointLabelYOffset=-12,
        #                             useMesh=True,
        #                             legends=[
        #                                         {
        #                                         'anchor': 'top-left',
        #                                         'direction': 'column',
        #                                         'justify': False,
        #                                         # 'translateX': -30,
        #                                         # 'translateY': -200,
        #                                         'itemsSpacing': 0,
        #                                         'itemDirection': 'left-to-right',
        #                                         'itemWidth': 80,
        #                                         'itemHeight': 15,
        #                                         'itemOpacity': 0.75,
        #                                         'symbolSize': 12,
        #                                         'symbolShape': 'circle',
        #                                         'symbolBorderColor': 'rgba(0, 0, 0, .5)',
        #                                         'effects': [
        #                                                 {
        #                                                 'on': 'hover',
        #                                                 'style': {
        #                                                     'itemBackground': 'rgba(0, 0, 0, .03)',
        #                                                     'itemOpacity': 1
        #                                                     }
        #                                                 }
        #                                             ]
        #                                         }
        #                                     ],                            
        #                             theme={
        #                                     # "background-color": "rgba(158, 60, 74, 0.2)",
        #                                     "textColor": "black",
        #                                     "tooltip": {
        #                                         "container": {
        #                                             "background": "#3a3c4a",
        #                                             "color": "white",
        #                                         }
        #                                     }
        #                                 },
        #                             animate= False)
                                    
                                        
        #                                 ,key="item_1",sx={"borderRadius":"15px", "borderRadius":"15px","background-color":"#F0F2F6"}) 






    with st.container():
        st.subheader(''' 
                    🤔 독자들이 가장 많이 보는 시간대는 언제인가요?
                    ''')
        st.caption(''' 
                * 웹툰의 조회수에 대한 정확한 값은 알 수 없었습니다. 하지만 조회수와 댓글간의 상관성은 매우 높다고 판단하여 독자들의 참여도 지표인 '댓글'을 남긴시간을 이용하여 가장 많이 보는 시간대를 집계해보았습니다! 
                    ''')
        # comment_data[;]
        comment_data['hour'] = comment_data['comment_date'].dt.hour #.strftime("%Y-%m-%d %H:%M:%S")
        comment_data = comment_data.dropna(subset=['hour'])   
        comment_group_by_hour = comment_data.groupby(['hour']).agg(        
            cnt = pd.NamedAgg(column='hour',aggfunc='count'))

        st.line_chart(comment_group_by_hour, use_container_width=True)

        st.write('''
                  웹툰 업로드가 되는 시간대인 23시~24시 밤부터 새벽 시간대에 가장 많은 독자들이 접속함을 볼 수 있었어요! 
                 또한 낮 시간대에는 상대적으로 12시에 많은 웹툰을 보는 독자들이 있었습니다.''')



        st.divider()


    with st.container():
        
        st.subheader('가치가 높은 독자 선별하기')
        # lifetimes_df = comment_data.copy()
        # lifetimes_df['comment_date'] = lifetimes_df['comment_date'].dt.date
        # current_date = lifetimes_df['comment_date'].max()
        # metrics_df = summary_data_from_transaction_data(lifetimes_df
        #                                         , customer_id_col = 'user_id'
        #                                         , datetime_col = 'comment_date'
        #                                         , observation_period_end=current_date)
        # st.write(metrics_df)




# if st.button('Download to CSV'):
#     # 파일 경로 및 파일명 설정
#     file_path = f'C:\webtoon\comment_data(71~77).csv'  
#     comment_data.to_csv(file_path, index=False,encoding='utf-8-sig')
#     st.success("Success")



# custom tag 
# https://comic.naver.com/curation/list?type=CUSTOM_TAG&id=229