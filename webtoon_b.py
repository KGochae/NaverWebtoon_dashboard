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


col1, col2 = st.columns([8,7])
with col1:
        c1, c2= st.columns([1.5,8])
        with c1:
            st.image('image/thumbnail.png',width=120) 
            with st.form(key ='searchform'):
                submit_search = st.form_submit_button('Load data')


                
        with c2:
            st.markdown('''# Webtoon Dashboard''')
            st.caption(''' 네이버 웹툰 '지발' 작가님의 '무직백수 계백순' 작품의 성과지표를 대시보드로 구축 해보고 분석 해보았습니다😀!  
                       데이터는 (23.06.06 ~ 24.03.03)기간동안 남겨진 댓글을 이용하였습니다. `Load Data` 를 클릭해주세요!''') #.strftime('%Y-%m-%d %H:%M'))



# ---------------------------------------------------------------- GOOGLE Cloud Storage 에 데이터 연결 ----------------------------------------------------------- #

# ------------- Create API client ----------------------------------- #

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)


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




if submit_search:
    comment_data = load_data(data_folder[0])
    main_data = load_data(data_folder[1])
    main_data['upload_at'] = pd.to_datetime(main_data['upload_at'], format='%y.%m.%d')
    main_data['upload_at'] = main_data['upload_at'].dt.strftime('%Y-%m-%d')

    st.session_state.comment_data = comment_data
    st.session_state.main_data = main_data




if hasattr(st.session_state, 'main_data'):
    main_data = st.session_state.main_data
    main_data['chapter'] = main_data['episode'].apply(lambda x: re.search(r'\b(\d+)\D', x).group(1) if re.search(r'\b(\d+)\D', x) else None).astype(int)


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




    # ---------------------------------------------------------------- DAU, WAU, MAU활성화 유저 지표  ---------------------------------------------------------------- #

    with st.container():
        st.header(''' 
                Activation User  
                ''')
        st.caption('''                     
                    에피소드별 남겨진 댓글의 아이디를 기준으로 고유 유저수를 집계 했습니다🫡!일부 필터링된 '닉네임(id***)' 형태이며 같다면 동일 유저로 판단했습니다.                      
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
    

   

        # issue
        with col2:
            # st.subheader(' ✔️Issue')

            st.markdown('''
                #### Comment
                         ''')
            st.markdown('''
                     * 무직백수계백순 웹툰의 경우 일요일, 수요일에 연재되는 작품입니다. <strong style="color:#75D060"> 정해진 요일에만 연재되는 웹툰 특성상 요일별로 변동성이 큰 편</strong>입니다.     
                     * 해당 주의 전체 DAU가 WAU 보다 항상 높습니다. 재방문(댓글 참여)하는 독자들이 조금 있는 편입니다.                                           
                       ''', unsafe_allow_html=True)

            #--------------------------------- dau - wau ---------------------------------------------- #

            dau = dau.rename(columns={'user_id':'dau'})
            dau['comment_date'] = pd.to_datetime(dau['comment_date'], errors='coerce')
            dau['week'] = dau['comment_date'].dt.to_period('W').dt.start_time.dt.date
            dau['month'] = dau['comment_date'].dt.to_period('M').dt.start_time.dt.date

            dw = pd.merge(dau, wau, left_on='week', right_on='comment_date', how='inner')
            dw = dw.rename(columns={'user_id': 'wau','comment_date':'week','comment_date_x':'day'}).drop(columns=['comment_date_y']) 
            dw['dau_sum'] = dw.groupby(['week'])['dau'].transform('sum')
            dw['dau_wau_diff'] = dw['dau_sum'] - dw['wau']
            dw= dw.drop_duplicates(subset=['week'])[['week','dau_sum','wau','dau_wau_diff']]

            pivot_dw = pd.pivot_table(dw, values='dau_wau_diff', index='week')      


            expander = st.expander('DAU-WAU chart')
            with expander:            
                st.line_chart(pivot_dw, use_container_width=True,color='#75D060')
                st.write(dw)
            # chort_df = comment_data.copy()
            # chort_df.set_index('user_id', inplace=True)
            # 유저별 첫 참여기간 추출
            # chort_df['CohortGroup'] = chort_df.groupby(level=0)['comment_date'].min().apply(lambda x: x.strftime('%Y-%m'))
            # chort_df.reset_index(inplace=True)


# ------------------------------------------------------ 댓글 데이터를 기준으로 유저 고착도를 구해보자 --------------------------------------------- #



        st.header('Stickiness ')
        st.caption(''' 주에 2번 연재되는 작품 특성상 활성화 유저 또한 해당 연재일에 주로 들어오는 경향이 있었습니다. 이를 위해 연재되는 날짜의 평균 고착도를 볼 수 있도록 했습니다.
                    ''')



        # 주간 stick 구하기 
        # 일단, 해당 요일이 어느 주인지 filter 필요
        # 해당 테이블에 wau merge   
        stick_df = pd.merge(dau, wau, left_on='week', right_on='comment_date', how='inner')
        stick_df = stick_df.rename(columns={'user_id': 'wau','comment_date':'week','comment_date_x':'day'}).drop(columns=['comment_date_y']) 
        stick_df['week_stick'] = round(stick_df['dau'] / stick_df['wau'],2) * 100
        stick_df['week_stick'] = stick_df['week_stick'].astype(int)


        # 연재되는 날짜의 유저 고착도 구하기
        def user_stickiness(stick_df ,day):
            Stickiness = stick_df[stick_df['day_name'].isin(day)]
            Stickiness['week'] = pd.to_datetime(Stickiness['week']).dt.strftime('%Y-%m-%d')
            Stickiness = Stickiness.groupby(['week']).agg(
                week_stick_mean = pd.NamedAgg(column='week_stick', aggfunc='mean')                                                   
                                                    ).reset_index()
            Stickiness['week_stick_mean'] = round(Stickiness['week_stick_mean'])

            # (연재되는 날의)평균 고착도
            mean_stick = round(Stickiness['week_stick_mean'].mean())

            # 데이터 변환
            nivo_data = []
            for index, row in Stickiness.iterrows():
                nivo_data.append({'x': row['week'], 'y': row['week_stick_mean']})

            stickiness_nivo_data = [{
                "id": "stickness",
                "data": nivo_data
            }]

            return  mean_stick, stickiness_nivo_data
        


        # 평균 고착도를 요일별, 연재일별로 보기 위한 toggle 입니다.
        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown('''#### 📊 Stickiness ''' )
            mean_stick, stickiness_nivo_data =  user_stickiness(stick_df, day = list(calendar.day_name))
            title = '요일별' 
            on = st.toggle('(연재일) Stickiness')
            if on:
                mean_stick, stickiness_nivo_data =  user_stickiness(stick_df, day = ['Sunday','Wednesday'])
                title = '연재일'





            with st.container():       
                    with elements("Stickiness_line_chart"):
                        layout = [
                            dashboard.Item("item_1", 0, 0, 12, 2),
                        ]

                        with dashboard.Grid(layout):                                                            
                            mui.Box(                                        
                                nivo.Line(
                                    data= stickiness_nivo_data,
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
            st.markdown(f''' 
                    #### {title} 평균 stickiness                      
                    * 지발님의 작품 '무직백수 계백순'의 평균 고착도(DAU/WAU)는 <strong style="color:#75D060"> {mean_stick}% </strong>입니다.  
                    * 큰 변동 없이 7일 중 평균 <strong style="color:#75D060"> {(mean_stick/100)*7}번 </strong> 댓글을 남기고 있습니다.  
                    * 한 주당 2번 연재되는 웹툰 시스템을 고려한다면 준수한 상태라고 생각합니다. 
                     ''',unsafe_allow_html=True )    
 

    



    # ---------------------------------------------------------------- 독자들이 서비스를 이용하는 시간대 ---------------------------------------------------------------- #
    
    
    with st.container():
        
        # 시간(hour) 정보를 추출 하여 집계(count)
        comment_data['hour'] = comment_data['comment_date'].dt.hour 
        comment_group_by_hour = comment_data.groupby(['hour']).agg(        
            cnt = pd.NamedAgg(column='hour',aggfunc='count'))


        col1, col2 = st.columns([3,1])
        with col1 :
            st.subheader(''' 
                        🤔 독자들이 가장 많이 보는 시간대는 언제인가요?
                        ''')
            st.caption(''' 
                    * 웹툰의 조회수에 대한 정확한 값은 알 수 없었습니다. 하지만 조회수와 댓글간의 상관성은 매우 높으며 이에 따라 독자들의 참여도 지표인 '댓글'을 남긴시간을 이용하여 이용 시간대를 구했습니다. 
                        ''')

            st.line_chart(comment_group_by_hour, use_container_width=True)


        with col2:
            st.markdown('''#### Comment''')
            st.write('''
                    * 주로 **웹툰이 업로드가 되는 시간대인 밤(23시)부터 새벽 시간대**에 가장 많은 독자들이 접속함을 볼 수 있었어요! 
                    또한 상대적으로 완만하지만 **오전 시간대(6시~8시)** 그리고 **점심 시간대(12시)** 에 웹툰을 보는 독자들이 있었습니다. 
                    
                    * 상대적으로 적은 오전/낮 시간대에 독자들을 확보하려면 어떻게 하면 좋을까요? 
                    ''')



        # 웹툰을 보는 시간 (아침 점심 밤) 유저 비율 추가
        comment_data['morning'] = 0
        comment_data['day'] = 0
        comment_data['night'] = 0

        comment_data.loc[comment_data['hour'].between(6, 11), 'morning'] = 1
        comment_data.loc[comment_data['hour'].between(12, 18), 'day'] = 1
        comment_data.loc[~comment_data['hour'].between(6, 18), 'night'] = 1


        user_timeinfo = comment_data.groupby(['user_id']).agg(
                    morning = pd.NamedAgg(column='morning',aggfunc='sum'),
                    day = pd.NamedAgg(column='day',aggfunc='sum'),
                    night = pd.NamedAgg(column='night',aggfunc='sum')
                )



        st.divider()




    # -------------------------------------------------------------- ltv 산출하기 -------------------------------------------------------------------------------------- #
   
    
    with st.container():
        
        st.header('🏅 LTV 활용하기')
        st.markdown(''' 
                    #### ✔️ 밤에 비해 오전, 낮시간대의 UV가 적은 것을 볼 수 있었습니다.            
                    > 오전/낮 시간대의 더 많은 UV 확보하기 위해 **'등교/출근, 점심 시간대에 맞춘 n분 무료보기 및 쿠키 조조할인 혜택 및 광고'** 프로모션을 진행하려고 하는데요! 이벤트를 진행할 예산을 효율적으로 사용하여 목표를 달성할 수 있는 방법이 있을까요?  
                    > 이를 위해, 독자들이 주로 **이용하는 시간대**의 그룹을 나누고 **RFM, LTV** 를 활용하여 **미래가치가 높은 독자**들을 선별해 이벤트를 진행해보려고 합니다.

                     ''')


        # st.write('''
        #          해당 서비스에서 LTV를 구해야하는 이유는 뭘까? 먼저 해당 서비스의 수익 모델을 확인해보자.

        #          ① 수익성 분배 PPS(Page Profit Share)모델  
        #          웹툰 하단의 이미지 광고, 미리보기 유료 판매 수익, 드라마/영화 영상화, IP(지적 재산권)기반 비즈니스를 통해 수익창출                              

        #          ② 부분 유료화 수익 모델  
        #          쿠키를 결제하여 아직 연재되지 않은 에피소드를 볼 수 있음.
                
        #         > "광고 노출수" = "웹툰 조회수" = "수익 창출" 큰 상관성이 있다.
        #          ''')

        st.caption(''' 좀 더 정확한 LTV를 산출하기 위해 독자별 **쿠키(유료결제)를 이용 여부**를 추가했습니다.
            예를 들어, '2024-03-01'에 업로드된 작품이 있다면, 유료결제를 하지 않은 사람의 경우 업로드된 날짜 이후에 댓글을 남길 수 있습니다.  
            하지만 **쿠키를 이용하여 미리보기를 한 유저의 경우 업로드 날짜(2024-03-01) 이전에 웹툰을 보고 댓글을 작성**했을 것입니다! <strong style="color:#6BC55C">즉, '웹툰이 게시된 날짜' > '댓글이 작성된 날짜'인 경우 '쿠키를 사용한 독자' 로 판단</strong>했습니다. 
            ''', unsafe_allow_html=True)



# ---------------------------------------------------------------- LTV를 산출하기 위한 전처리 및 모델링 과정 -------------------------------------------------------------------------------------- #

        info = main_data.drop_duplicates(subset=['episode'])[['chapter','episode','upload_at']]
        ltv_df = pd.merge(comment_data, info, on='episode',how='left')
        ltv_df['cookie'] = np.where(ltv_df['comment_date'] < ltv_df['upload_at'], 1200, 0)
        ltv_df['price'] = ltv_df['cookie'] + ltv_df['comment_like'] + 500 

        current_date = ltv_df['comment_date'].max()
        ltv_df['comment_date'] = pd.to_datetime(ltv_df['comment_date']).dt.date


        metrics_df = summary_data_from_transaction_data(ltv_df
                                                , customer_id_col = 'user_id'
                                                , datetime_col = 'comment_date'
                                                , monetary_value_col='price'
                                                , observation_period_end=current_date).reset_index()




        # 약 8개월(240) 데이터, holdout_Days 1/8
        # train, test set 분리 -  liftime 에서는 calibration/holdout 으로 분리(명칭만 다르다)
        holdout_days = 30
        calibration_end_date = current_date - datetime.timedelta(days = holdout_days)

        metrics_cal_df = calibration_and_holdout_data(ltv_df
                                                ,customer_id_col = 'user_id'
                                                ,datetime_col = 'comment_date'
                                                ,calibration_period_end=calibration_end_date # train 데이터 기간
                                                ,observation_period_end=current_date         # 끝 기간
                                                ,monetary_value_col='price')

        # frequency가 0인 것은 제외하기 (BG/NBD 모델 자체가 반복구매를 가정 하고 있다.)
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

        # l2_bgnbd, l2_gg = best_L2_penalty(filtered_df) # 최적의 페널티값 실행
        lifetimes_model, frequency_mse = bgnbd_model(0.001322590266385021) # 구해진 BG/NBD l2 페널티값
        spend_model, monetary_mse      = gg_model(0.0018085768788633095) #  구해진 GammaGamma l2 페널티값





        # LTV table COl
        col1,col2 = st.columns([1,2])

        with col1:
            st.markdown('''##### 📁쿠키를 사용한 유저의 테이블(일부) ''')

            expander = st.expander('독자 Price 기준')
            with expander:
                st.caption('''
                        Monetary 산출을 위한 유저 사용 금액(price)을 다음과 같이 정의 했습니다.
                        (실제 쿠키의 가격은 개당 120원 이지만 극적인 표현을 위해 1200원으로 조정)
                           
                        * 쿠키 1개 이용 = 1200원의 가치                                               
                        * 받은 좋아요 = 개당 1원의 가치  
                        * 댓글 작성수 = 개당 500원의 가치  
                           
                        유료결제 뿐만 아니라 '댓글'과 '댓글 좋아요' 또한 작품의 관심, 인기도에 영향을 미치는 중요한 지표라고 생각합니다.
                        가장 먼저 보여지는 베스트 댓글을 보고 또 다른 댓글을 남기기도 하고, 좋아요를 누르기도 하면서 독자들의 참여도를 이끌어 내는 지표라고 생각했기 때문에 금액으로 환산하여 집계 했습니다.
                        ''')
        
                st.write(ltv_df[ltv_df['cookie'] == 1200][['episode','upload_at','user_id','comment_date','comment_like','cookie','price']].sample(5))



        with col2:
            st.markdown('''##### 📁LTV 산출하기 ''')
            expander = st.expander('LTV TABLE ')
            with expander:
                st.caption(f'''
                            파이썬에서 제공하는 Lifetimes 패키지의 BG/NBD, GammaGamma 모델을 이용하여 향후 8개월 동안의 LTV, 예상 구매횟수 및 금액을 산출해보았습니다. 

                            * 예측 구매 횟수의 평균 제곱오차 : ±{round(frequency_mse,3)}일
                            * 예측 구매 금액의 평균 제곱오차 : ±{round(monetary_mse,3)}원
                            * 수집한 데이터가 약 8개월치 이므로, 8개월 동안의 예상 LTV를 산출했습니다.
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


                # 8개월 동안의 예상 구매횟수 (수집한 데이터가 약 8개월치)
                t=240 
                final_df['predicted_purchases'] = lifetimes_model.conditional_expected_number_of_purchases_up_to_time(t
                                                                                                    , final_df['frequency']
                                                                                                    , final_df['recency']
                                                                                                    , final_df['T'])
                # 8개월 동안의 예상 구매금액
                final_df['predicted_monetary_value'] = spend_model.conditional_expected_average_profit(final_df['frequency']
                                                                                    ,final_df['monetary_value'])


                # 독자 세그먼트 나누기
                final_df['segment'] = 0 # pd.qcut(final_df['ltv'], 5 , labels=['bronze','silver', 'gold','platinum','diamond'])

                quantiles = final_df['ltv'].quantile([0.8, 0.6, 0.4])
                final_df.loc[final_df['ltv'] >= quantiles.iloc[0], 'segment'] = 'diamond'
                final_df.loc[final_df['ltv'].between(quantiles.iloc[1], quantiles.iloc[0]), 'segment'] = 'platinum'
                final_df.loc[final_df['ltv'].between(quantiles.iloc[2], quantiles.iloc[1]), 'segment'] = 'gold'
                final_df.loc[final_df['ltv'] <= quantiles.iloc[2], 'segment'] = 'silver'

 
                # 최근에 댓글 및 쿠키를 사용한 독자들인 경우(lookie) ltv에 산출된 예산에 따라서 어떤 마케팅을 할 수 있을지 전략을 세 울 수 있다.

                final_df = pd.merge(final_df,user_timeinfo,on='user_id',how='inner')
                final_df['morning_ratio'] = round(final_df['morning']/(final_df['morning'] + final_df['day'] + final_df['night']) * 100)
                final_df['day_ratio'] = round(final_df['day']/(final_df['morning'] + final_df['day'] + final_df['night']) * 100)
                final_df['night_ratio'] = round(final_df['night']/(final_df['morning'] + final_df['day'] + final_df['night']) * 100)            


                # final_df['time'] = 0 
                # final_df.loc[(final_df['morning_ratio'] >= 30) | (final_df['day_ratio'] >= 30), 'time'] = 'morning/day'
                # final_df.loc[~(final_df['morning_ratio'] >= 30) | (final_df['day_ratio'] >= 30), 'time'] = 'morning/day'
                

                st.write(final_df)


            # FRML 차트
            @st.cache_resource
            def hist (final_df):
                fig, axes = plt.subplots(1, 4, figsize=(16, 4))
                M_top20_per = np.percentile(final_df['monetary_value'], 80)
                axes[0].hist(final_df['monetary_value'], bins=20, alpha=0.5, color='blue', label='Monetary')
                axes[0].axvline(x=M_top20_per, color='red', linestyle='--', label=f'Top 20% : {int(M_top20_per)}')
                axes[0].set_title('Monetary Distribution')
                axes[0].legend()

                # frequency
                F_top20_per = np.percentile(final_df['frequency'], 80)
                axes[1].hist(final_df['frequency'], bins=20, alpha=0.5, color='blue', label='Frequency')
                axes[1].axvline(x=F_top20_per, color='red', linestyle='--', label = f'Top 20% : {int(F_top20_per)} ')
                axes[1].set_title('frequency Distribution')
                axes[1].legend()

                # Recency
                R_top20_per = np.percentile(final_df['recency'], 80)
                axes[2].hist(final_df['recency'], bins=20, alpha=0.5, color='blue', label='Recency')
                axes[2].axvline(x=R_top20_per, color='red', linestyle='--', label=f'Top 20% : {int(R_top20_per)}')
                axes[2].set_title('Recency Distribution')
                axes[2].legend()


                L_top20_per = np.percentile(final_df['ltv'], 80)
                # L_top40_per = np.percentile(final_df['ltv'], 60)
                axes[3].hist(final_df['ltv'], bins=20, alpha=0.5, color='blue', label='LTV')
                axes[3].axvline(x=L_top20_per, color='red', linestyle='--', label=f'Diamond(Top 20%) : {int(L_top20_per)}')
                # axes[3].axvline(x=L_top40_per, color='green', linestyle='--', label=f'Platinum : {int(L_top40_per)}')
                axes[3].set_title('LTV Distribution')
                axes[3].legend()


                plt.tight_layout()                
                st.pyplot(fig)


            st.write('''##### 세그먼트 나누기 ''')
            st.caption(''' 산출된 LTV 값, 파레토 법칙, RFM_LTV 값들을 그래프로 시각화하여 적절한 세그먼트를 나눠 보았습니다.''')
            hist(final_df)

            # R_top20_per = np.percentile(final_df['recency'], 80)            
            # F_top20_per = np.percentile(final_df['frequency'], 80)
            # M_top20_per = np.percentile(final_df['monetary_value'], 80)
            L_top20_per = np.percentile(final_df['ltv'], 80)
            
            # 향후 8개월 동안의 예상 LTV 합
            ltv_sum = round(final_df['ltv'].sum())

            st.write(f'''
                    * LTV 상위 20% : {int(L_top20_per)}
                    * (상위20%) diamond 
                    * (20-40) platinum
                    * (40-60) gold
                    * (나머지) silver

                ''')



    # -------------------------------------------------------------- 프로모션을 진행할 우선순위 독자 정하기 ------------------------------------------------------------- #            
   
    
    
    with st.container():
        st.subheader('🎁 프로모션을 진행할 우선순위 독자')
        st.markdown(''' 
                > 프로모션을 진행할시에 반응할 확률이 높은 독자는 누구일까요? 산출된 **고객 생애 가치(LTV)** 와 서비스를 주로 **이용하는 시간대**를 나눠서 아래와 같이 우선순위를 정해보았습니다.  
                
                ''')


        dia_user = final_df.groupby(['segment']).agg(
            monetary_value = pd.NamedAgg(column='monetary_value',aggfunc='mean'),
            ltv = pd.NamedAgg(column='ltv',aggfunc='mean'),
            morning = pd.NamedAgg(column='morning',aggfunc='sum'),
            day = pd.NamedAgg(column='day',aggfunc='sum'),
            night = pd.NamedAgg(column='night',aggfunc='sum')

        )

        col1, _ ,col2 = st.columns([1.5,0.1,1.5])
        with col1:

            st.write('''#### 📊 RFM chart  ''')
            st.caption(''' RFM 값을 조절하여 세그먼트와 웹툰을 보는 주시간대 별로 타겟층에 대한 분포를 확인할 수 있습니다.''') 


            with st.container():

                expander = st.expander('⚙️ RFM Chart Option')
                with expander:


                    with st.form(key="RFML_slider"):
                        c1, c2, c3, c4, c5= st.columns([2,2,2,2,1])
                        
                        # RFM,LTV 값을 상위% 범위에 맞게 조절하여 필터링합니다.
                        with c1: 
                            r_option = st.slider('Recency(상위%)', 1, 100, (1, 100))
                            r_percentile = np.percentile(final_df['recency'], [100 - int(r_option[0]), 100 - int(r_option[1])])

                        with c2:
                            f_option = st.slider('Frequency(상위%)', 1, 100, (1, 100))
                            f_percentile = np.percentile(final_df['frequency'], [100 - int(f_option[0]), 100 - int(f_option[1])])

                        with c3:
                            m_option = st.slider('Monetary(상위%)', 1, 100, (1, 100))
                            m_percentile = np.percentile(final_df['monetary_value'], [100 - int(m_option[0]), 100 - int(m_option[1])])

                        with c4:
                            l_option = st.slider('LTV(상위%)', 1, 100, (1, 100))
                            l_percentile = np.percentile(final_df['ltv'], [100 - int(l_option[0]), 100 - int(l_option[1])])


                        with c5:
                            submit_search = st.form_submit_button("확인")


                # 위 조건에 맞게 필터링 됩니다.
                filtered_df = final_df[(final_df['recency'].between(r_percentile[1], r_percentile[0]))
                                        & (final_df['frequency'].between(f_percentile[1], f_percentile[0]))
                                        & (final_df['monetary_value'].between(m_percentile[1], m_percentile[0]))
                                        & (final_df['ltv'].between(l_percentile[1], l_percentile[0]))
                                        ]


                # 웹툰을 이용하는 주시간대 정보를 분리하기위해
                # 오전+낮 비율이 50% 이상인 유저와 그 외 유저를 나눠줍니다.
                
                filtered_df['time'] = 'other'
                filtered_df.loc[filtered_df['morning_ratio'] + filtered_df['day_ratio'] >= 50,'time'] = 'morning/day'


                # 세그먼트와, 시간대 별로 그룹지어 계산
                group = filtered_df.groupby(['segment','time']).agg(
                    segment_cnt = pd.NamedAgg(column='segment',aggfunc='count'),
                ).reset_index()


                # 전체비용
                total_cost = group['segment_cnt'].sum() * 1000

                # "morning/day"기준 비용 
                morning_day_cost = group[group['time'] == 'morning/day']['segment_cnt'].sum() * 1000


                # 세그먼트,시간대별 데이터 시각화 및 테이블, 얘상비용 계산
                c1,c2 = st.columns([1,1.2])
                with c1:
                    st.write('''##### 📊 chart by segment ''')
                    st.bar_chart(group, x="segment", y="segment_cnt", color="time",use_container_width=True,width=400,height=500)
                with c2:
                    st.write('''##### 📖 table ''')
                    st.caption(''' 오전+낮의 비율이 50% 이상인 경우 morning/day  그 외에는 other로 분류''')
                    st.write(group)

                    st.write(f''' 
                            프로모션 진행 비용이 1명당 1000원이라고 가정시                                   
                            * 전체 비용 : {total_cost}원
                            * 아침/낮 독자 한정시 비용 : {morning_day_cost}원 
                            ''')        



        with col2:
            st.write('''### 🎯 타겟 독자 ''')
            st.caption(''' RFM Chart 를 활용하여 적절한 타겟층을 선정해 보았습니다. ''')



            st.write(''' ##### ① 충성 독자 ''')
            st.caption(''' RFM(1-40%) LTV (1-40%)''')
            st.write(''' > **RFM, LTV 모두 준수한 독자 (+ 오전/낮에 이용 비율이 50% 이상인 독자)**  
                            👉🏻 미래가치가 높은 고객이면서 아침/낮에 타겟으로 만들어진 해당 프로모션에 가장 잘 반응할 독자입니다.
                    ''')



            st.write('''##### ② 잠재 독자''')
            st.caption('''RF(1-30%) M(30-100%) ''')
            st.write('''                     
                    > **M 은 낮지만 R,F가 높은 독자 (+ 오전/낮에 이용 비율이 50% 이상인 독자)**  
                    👉🏻 지출한 금액은 적지만, 최근에 많이 활동한 독자 입니다. 프로모션에 따라 쿠키를 사용할 수 있는 잠재 독자라고 생각합니다.
                                                       
                    ''')



            st.divider()

            st.write(f'''
                    ### 💰 예상 비용
                    향후 8개월 동안의 예상 ltv 값은 `6,345,070`원입니다. 프로모션 진행 비용이 1명당 1000원이라고 가정 했을 때, 전체 독자들에게 해당 프로모션을 진행하면 `3,665,000`원의 비용이 필요합니다. 
                    하지만 위 독자들을 타겟으로 우선 실행시 예산을 효율적으로 사용하면서 목표 달성을 기대할 수 있습니다.
                    ''')

            st.write('''
                    * 충성 독자만 진행시 비용 `465,000`원 , 그 중 오전/오후에 이용하는 독자 우선 진행시 비용 `161,000`원  
                    * 잠재 독자만 진행시 비용 `442,000`원 , 그 중 오전/오후에 이용하는 독자 우선 진행시 비용 `186,000`원
                     ''')


        # 이외 아이디어..
        # st.markdown(''' 
        #     #### ② 목표를 부여하여 독자들의 참여도 올리기  
        #     웹툰 수익구조에 따르면 조회수 그리고 독자들의 참여도가 굉장히 중요하다는 것을 알 수 있습니다. 
        #     산출된 ltv 로 나눠진 세그먼트에 따라 열혈독자, 일반독자 랭크를 눈에 보이게 부여하면 어떨까요? 열혈독자를 달기 위한 일종의 목표를 만들어 줌으로써 기존의 기여도가 높은 독자 뿐만 아니라 다른 독자들의 참여도를 높히는것 입니다!
        #     게임처럼 LTV 수치가 일종에 경험치가 되고, 이는 독자의 참여도(댓글, 좋아요, 베스트 댓글 ,쿠키 사용 등)를 통해 등급이 올라 감으로서 성취감을 느끼게 한다면 독자들의 참여도가 더 높아질 수 있습니다.            
        #     ''')


    st.divider()




    # -------------------------------------------------------------- 쿠키가 가장 많이 사용된 에피소드 분석 ------------------------------------------------------------- #

    with st.container():            
            st.subheader('🍪 Episode By Cookie')
            st.caption(''' 쿠키사용량이 높았던 에피소드의 특징은 무엇일까요? 에피소드별(x:업로드된 날짜) 쿠키 사용량을 시각화하여 가장 가치가 높았던 에피소드를 찾아보고 독자들의 니즈를 파악해보았습니다.''')    
         
            cookie_by_ep = ltv_df.groupby(['chapter','episode','upload_at']).agg(
                total_cookie = pd.NamedAgg(column='cookie', aggfunc='sum')            
            ).reset_index().sort_values(by=['upload_at'])


            # 평균 쿠키
            mean_cookie = round(cookie_by_ep['total_cookie'].mean())

           # 데이터 변환
            nivo_data_cookie = []
            for index, row in cookie_by_ep.iterrows():
                nivo_data_cookie.append({'x': row['upload_at'], 'y': row['total_cookie']})

            nivo_data_cookie = [{
                "id": "cookie",
                "data": nivo_data_cookie
            }]
            

            top_cookie  = cookie_by_ep.sort_values(by=['total_cookie'],ascending=False)
            recent_data = main_data[main_data['down_at'] =='2024-03-06'][['episode','like_count','comment_count','score']] # 가장 최근 240306 기준의 에피소드 정보 결합
            top_cookie  = pd.merge(top_cookie,recent_data,on='episode',how='inner') 


            col1,col2 = st.columns([3,3])    

            # 쿠키 사용 차트, 에피소드 명예의 전당
            with col1:
                st.markdown('''#### 📈 Cookie Chart''')

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



            # 실험소
            with col2:
                st.markdown('''### 🧪 실험 가설  ''')
                st.write(''' 
                    > " **시리즈 형태의 에피소드**일수록 쿠키 사용량이 높을것 이다. "  
                    하루분량으로 끝나는 '단편 스토리'와 반대로 계속해서 이어지는 '시리즈 형태의 에피소드'의 경우 독자들의 입장에서
                    **뒷 내용에 대한 궁금증**이 유발되고 이에 따라 쿠키를 사용하지 않을까? 생각이 들었습니다.🤔 
                    ''')
                st.caption('''
                    * 초기에 미리보기할 웹툰이 없다는 점을 고려 + cookie 가 0 인 에피소드는 제외하였습니다.
                    * 2개 이상의 에피소드(A) 단편 에피소드(B) 두개의 집단으로 나누고 독립표본T 검정을 진행했습니다.
                         ''')


                # 제목 형식에 ' : ' 를 기준으로 분리
                # \s* 공백 \(\d+\) 괄호안의 숫자 제거
                cookie_by_ep['title'] = cookie_by_ep['episode'].apply(lambda x: re.sub(r'\s*\(\d+\)$', '', x.split(':')[1]).strip()) 
                mask = cookie_by_ep['chapter'] == 67
                cookie_by_ep.loc[mask, 'title'] = cookie_by_ep.loc[mask, 'title'].str[:4] # 67화 예외 처리 필요

                cookie_by_ep = cookie_by_ep[cookie_by_ep['total_cookie'] > 0]
                group = cookie_by_ep.groupby(['title']).agg(
                    cookie_mean = pd.NamedAgg(column='total_cookie',aggfunc='mean'),
                    series_cnt = pd.NamedAgg(column='episode',aggfunc='count'),
                ).reset_index()

                group_1 = group[group['series_cnt'] >= 2]['cookie_mean']
                group_2 = group[group['series_cnt'] == 1 ]['cookie_mean']

                c1,c2 = st.columns([1,1])
                with c1:            
                    st.markdown('''##### ① 정규성 및 등분산성 확인''')

                    # 정규성검정
                    fig = plt.figure(figsize=(8, 6))
                    sns.histplot(group['cookie_mean'], kde=True, color='blue', bins=8)
                    plt.title('Density Plot of cookie')
                    plt.xlabel('cookie_mean')
                    plt.ylabel('Density')
                    st.pyplot(fig)
 
 
                     # 등분산성 검정
                    _, p_levene = levene(group_1, group_2)
                    st.write(f'''
                              * 왜도가 심하지 않은 정규분포의 형태를 띄고 있습니다.
                              * Levene's p_value : {round(p_levene,3)} 으로 등분산성을 만족하지 않습니다. 
                              * Welch's t-test 사용 결정                          
                            ''') 


                with c2:                    
                    # 독립표본 t-검정
                    # t_statistic, p_value = ttest_ind(group_1, group_2)
                    t_statistic, p_value = ttest_ind(group_1, group_2, equal_var = False)

                    # 결과 출력
                    st.markdown('''##### ② 독립 표본 t-검정 ''')
                    # st.code('''
                    #     # Welch's t-test
                    #     t_statistic, p_value = ttest_ind(group_1, group_2, equal_var = False)''')
                    st.markdown(f'''
                                검정결과 **시리즈 형태의 에피소드 라고 쿠키 사용량이 높다고 볼 수는 없었습니다.**
                             
                            * 단순히 시리즈의 길이 보다 해당 에피소드의 **'재미도', '장르반전', '서비스신'** 같은 요소들이 쿠키 사용량에 따라 차이가 있지 않을까 생각이 들었습니다. 
                            * (상대적으로 인기가 없었던) 초기에 나온 에피소드와 현재의 에피소드를 같이 비교하기에는 한계가 있다고 생각이 들었습니다.                             
                            * 데이터 자체의 부족함 또한 영향이 있습니다.
                            * T-statistic : {round(t_statistic,3)}  
                             P-value : {round(p_value,3)}                               

                             
                                                         ''')
 

 
