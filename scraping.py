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


# 데이터 수집 날짜
now = datetime.datetime.now()
now_time = now.strftime("%Y-%m-%d")


# 웹브라우저를 열지 않고 스크랩핑 하려면 headless 옵션을 주면 된다.
chrome_options = Options()
chrome_options.add_argument('--headless')  # 웹 브라우저를 헤드리스 모드로 실행할 경우 추가
driver = webdriver.Chrome(options=chrome_options) # options=chrome_options

# 에피소드별 댓글 정보 
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
