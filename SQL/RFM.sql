
-- episode 정보가 들어있는 table 
-- upload_date 데이터 값 (20.06.01)을 %y-%m-%d 형태(20-06-01) date 타입으로 전처리  
with ep as (
SELECT title
      , episode
      , upload_at
      , PARSE_DATE('%y.%m.%d', upload_at) AS upload_date    
FROM WEBTOON.ep
)

-- episode 별로 유저들의 댓글 table 
-- 각 episode 에 여러개의 댓글을 남길 수 있기 때문에, 에피소드별 가장 처음 댓글을 남긴 날짜를 기준으로 결제금액을 측정해야한다.(즉, 한 에피소드당 하나의 댓글만 인정)
-- 결제여부 = "업로드된 날짜 > 댓글을 작성한 날짜", 업로드 되기전에 댓글을 작성한 유저의 경우 유료결제를 통해 '미리보기'를 한 것으로 볼 수 있음

, comment as (
  SELECT *
  FROM (SELECT  episode
        , user_id
        , DATE(comment_date) as comment_date
        , ROW_NUMBER() OVER(PARTITION BY episode,user_id ORDER BY comment_date) as comment_num
        , comment_like
  FROM WEBTOON.user) a
  WHERE comment_num = 1
)


# user_id 별 RFM 지표
SELECT user_id
      , MIN(comment_date) as first_comment_date
      , MAX(comment_date) as last_comment_date
      , DATE_DIFF(MAX(comment_date),MIN(comment_date),DAY) AS recency
      , COUNT(user_id) as frequncy
      , SUM(price) as monetary
FROM (SELECT C.episode
            , C.user_id
            , C.comment_date
            , C.comment_like
            , E.upload_date
            , CASE WHEN C.comment_date < E.upload_date THEN 500 ELSE 0 END AS price --
      FROM comment C
      JOIN ep E ON C.episode = E.episode ) a 
GROUP BY user_id

