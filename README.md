![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/55e631fb-3618-450e-8160-d677c195baed)


# NaverWebtoon_dashboard
* 평소에 즐겨보는 웹툰 !! 지발작가님의 '무직 백수 계백순'의 성과지표 대시보드를 만들어 보았습니다! 👉🏻 💻[대시보드](https://n-webtoon.streamlit.app/) 구경가기
* 👉🏻 정리된 요약본은 [PPT요약 디렉토리](https://github.com/KGochae/NaverWebtoon_dashboard/blob/main/PPT%EC%9A%94%EC%95%BD/%EC%9B%B9%ED%88%B0%20%EC%84%B1%EA%B3%BC%EC%A7%80%ED%91%9C%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C%20%EB%B0%8F%20%EB%B6%84%EC%84%9D.pdf)를 참고해주세요!
* 이 외에 약간의 TMI가 담긴 글은 해당 [시리즈](https://velog.io/@liveandletlive/series/naver-webtoon-dashboard)를 읽어주시면 감사하겠습니다🙇🏻‍♂️!! 

## 디렉토리 

```bash
├── 📁.streamlit
| └── config.toml 
├── 📁 PPT요약
│ └── PDF 요약본
├── 📁 img
│ └── thumbnail.png
├── .README.md
├── requirements.txt
├── scraping.py -------------- # 웹툰 데이터 스크래핑
├── webtoon.css -------------- # 일부 CSS 
└── webtoon_main.py ---------- # dashboard main # 데이터 전처리, 모델링, 대시보드 
```

## 프로젝트 목표

> 내가 웹툰 작가라면? 어떤 지표들이 궁금할까? 작품이 얼만큼 성장하고 있을까요?

어떤 서비스에서 사용자들이 얼마나 이용하는지 지표를 통해서 확인 하듯이 '웹툰'속 하나의 작품에서는 어떤 지표를 봐야하고 더 성장하기 위해서 독자들을 어떻게 관리하면 좋을지 고민했습니다.
제가 평소에 즐겨보는 '무직백수 계백순' 이라는 작품을 하나의 프로덕트로 보고 해당 웹툰의 핵심성과지표와 EDA를 통해 얻은 인사이트를 정리해보려고합니다.



## 데이터 수집 및 전처리

> 네이버 웹툰 공식 api가 없기 때문에 파이썬 (셀레니움)을 이용해서 데이터를 수집했습니다.

* Python - Selenium, Pandas
  




## 📊 유저 활성화 지표
*  활성화 유저의 기준을 '댓글을 남겼다' 라는 행동으로 보고 활성화 지표들을 계산하였습니다. 댓글과 좋아요는 웹툰을 보고 난 뒤, 즉 서비스를 이용했다는 가장 확실한 흔적이 라고 생각했습니다.
*  그 중에서 네이버 웹툰의 댓글의 경우 '닉네임(id***)' 같은 형식 이었기 때문에 어느정도 PK(Primary Key)로 볼 수 있다고 생각했습니다.
* '닉네임(id***)'이 같은 경우 동일 유저로 판단했습니다.

![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/013bb7ae-0894-4253-8731-a559bab9c842)

* 날짜를 지정하여 DAU, WAU, MAU 값을 볼 수 있습니다.
* 무직백수 계백순의 경우 '일요일,수요일'에 연재되는 웹툰입니다. 정해진 날짜에만 연재되는 서비스 특성상 일별 변동성이 매우 큰 편입니다. 




## 💚 고착도 (Stickiness) ( DAU/WAU )
> 주 2번 연재되는 작품 특성상 해당 연재일에 주로 들어오는 경향이 있었습니다. 이를 위해 연재되는 날짜의 평균 고착도를 볼 수 있도록 했습니다.

![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/aeba7cca-df30-4ed6-af62-4468b50f4370)

* 지발님의 작품 '무직백수 계백순'의 평균 고착도(DAU/WAU)는 32% 입니다.
* 큰 변동 없이 7일동안 사람당 평균 2.24번 댓글을 남긴다고 볼 수 있습니다.
* 한 주당 2번 연재되는 웹툰 시스템을 고려한다면 준수한 상태라고 생각합니다.😀


## 🤔 독자들이 가장 많이 보는 시간대?
> 웹툰의 조회수에대한 정확한 값은 알 수 없지만, 조회수와 댓글간의 상관성은 매우 높다고 생각했습니다. 독자들의 참여도 지표인 '댓글'을 남긴시간을 이용하여 이용 시간대를 구했습니다.

![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/cc9fb6ce-da09-457b-8fc8-954aef7b59cc)

* 주로 웹툰이 업로드가 되는 시간대인 밤(23시)부터 새벽 시간대에 가장 많은 독자들이 접속함을 볼 수 있었어요!
* 또한 상대적으로 완만하지만 오전 시간대(6시~8시) 그리고 점심 시간대(12시) 에 웹툰을 보는 독자들이 있었습니다.

## 🎖️ LTV를 활용하여, 프로모션 진행해보기

#### ✔️ 밤에 비해 오전, 낮시간대의 UV가 적은 것을 볼 수 있었습니다.

> #### 프로모션 세워보기
> 오전/낮 시간대의 더 많은 UV 확보하기 위해 **'등교/출근, 점심 시간대에 맞춘 n분 무료보기 및 쿠키 조조할인 혜택'** 프로모션을 진행하려고 하는데요! 이름하여 **출근/밥친구 이벤트** 입니다 (ㅋㅋ) 

#### ✔️ MISSION 
* 이벤트를 진행할 예산을 효율적으로 사용하여 목표를 달성할 수 있는 방법이 있을까요?  
* 이를 위해, 독자들이 **주로 이용하는 시간대의 그룹을 나누고 RFM, LTV** 를 활용하여 미래가치가 높은 독자들을 선별해 이벤트를 진행해보려고 합니다.

## 📖 RFM, LTV 를 산출하기


### 웹툰의 수익 모델?
해당 서비스에서 LTV를 구하려면 어떤 지표가 필요할까요🤔..? 먼저 해당 서비스(웹툰)의 수익 모델을 확인해보면 다음과 같습니다.

#### ① 수익성 분배 PPS(Page Profit Share)모델  
웹툰 하단의 이미지 광고, 미리보기 유료 판매 수익, 드라마/영화 영상화, IP(지적 재산권)기반 비즈니스를 통해 수익창출                              

#### ② 부분 유료화 수익 모델  
쿠키를 결제하여 아직 연재되지 않은 에피소드를 볼 수 있음.
                
> 그렇다면 "광고 노출수" = "웹툰 조회수" = "수익 창출" 큰 상관성이 있다고 볼 수 있습니다. 또한, 웹툰 조회수는 댓글수와 큰 상관성이 있으므로 댓글 지표를 이용하여 고객들의 LTV를 산출할 수 있습니다.



#### ① 변수추가 (독자별 price)
쿠키를 이용하여 미리보기를 한 유저의 경우 "업로드 날짜" 이전에 웹툰을 보고 "댓글을 작성" 한 점을 이용하여 '쿠키(유료결제)'이용 여부 산출했습니다. (즉, **'웹툰이 게시된 날짜' > '댓글이 작성된 날짜' 인 경우, 쿠키를 사용한 독자로 볼 수 있습니다.**)  

> **Monetary를 산출 하기위해 조건 추가**
> * 쿠키 1개 이용 = 1200원의 가치
> * 받은 좋아요 = 개당 1원의 가치
> * 댓글 작성수 = 개당 500원의 가치  

이 외에 독자들의 참여도를 알 수 있는 지표들을 가치화 하여 Monetary 지표를 구했는데요!
> why? 유료결제 뿐만 아니라 '댓글'과 '댓글 좋아요' 또한 작품의 관심, 인기도에 영향을 미치는 중요한 지표라고 생각했습니다. 가장 먼저 보여지는 베스트 댓글을 보고 또 다른 댓글을 남기기도 하고, 좋아요를 누르기도 하면서 독자들의 참여도를 이끌어 내는 지표라고 생각했기 때문에 어느정도 가치가 있다고 생각하여 금액으로 환산해 집계 했습니다.



#### ② BG/NBD, GammaGamma 모델링
파이썬에서 제공하는 Lifetimes 패키지의 BG/NBD, GammaGamma 모델을 이용하여 향후 8개월 동안의 LTV, 예상 구매횟수 및 금액을 산출해보았습니다. 

* 예측 구매 횟수의 평균 제곱오차 : ±0.364일
* 예측 구매 금액의 평균 제곱오차 : ±24085.169원
* 수집한 데이터가 약 8개월치 이므로, 8개월 동안의 예상 LTV를 산출했습니다.



#### 세그먼트 나누기
> LTV 분포, 파레토 법칙(80:20)을 활용하여 세그먼트를 'diamond' , 'platinum','gold,'silver' 4개로 나눴습니다.

![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/4dcb2087-b177-4388-ba5a-9e1ed8c3aa14)


### 🎁 프로모션을 진행할 독자

### RFM,LTV Chart
![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/9854a2c3-0d18-45b2-96a8-c9e47309cd0d)


### 🎯 타겟 독자
![image](https://github.com/user-attachments/assets/dcd9ddf2-6cf3-4155-8b62-2a765db211dc)



## 🍪 Episode By Cookie
쿠키사용량이 높았던 에피소드의 특징은 무엇일까요? 에피소드별(x:업로드된 날짜) 쿠키 사용량을 시각화하여 가장 가치가 높았던 에피소드를 찾아보고 독자들의 니즈를 파악해보았습니다.

![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/1964e91e-83ad-477b-a5ff-5f5b856b297f)


## 🧪실험실

![image](https://github.com/KGochae/NaverWebtoon_dashboard/assets/86241587/c2195019-1a50-4ae5-a544-8e795f3c585e)



> 가장 쿠키가 많이 사용된 top3 에피소드의 특징을 보면 다음과 같습니다.

##### ① 장르 반전
가장 높은 cookie 점수를 달성한 매너리즘 에피소드의 경우 해당 웹툰의 '1부 마무리'라는 이벤트의 영향도 있지만 
그 동안 단순히 **가벼운 개그물로 보아왔던 작품안에서 '진지함' '감동' 이라는 장르의 반전**을 추가하면서 독자들에게 큰 인상을 준것을 알 수 있습니다.
                        
 ##### ② 서비스신
무직백수 계백순 웹툰의 경우 **작화, 캐릭터가 예쁘다**는 큰 매력 포인트가 있습니다. 특히, 78화: 초대(1)의 에피소드의 경우 이를 극대화 하는 서비스 장면이 추가 되면서 독자들의 큰 반응을 이끈것으로 보입니다.
                            
 ##### ③ 그냥 웃기다.
이 외에 '개그' 장르 답게 **독자들의 웃음 코드를 잘 살리는 에피소드**의 경우 독자들의 반응이 좋은것을 볼 수 있습니다.
