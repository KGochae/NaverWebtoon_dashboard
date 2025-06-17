# 활성화 기준을 유저들이 댓글을 작성한 행위로 보았습니다. 
# DAU, WAU, Stickiness

  with cte as (
  SELECT user_id
        , DATE(comment_date) as date -- 댓글을 작성한 날짜를 %Y-%m-%d 형태로 변환 
  FROM WEBTOON.user 
)


SELECT A.date as date
    , COUNT(DISTINCT A.user_id) as DAU
    , COUNT(DISTINCT W.user_id) as WAU
    , (COUNT(DISTINCT A.user_id)/COUNT(DISTINCT W.user_id))*100 AS Stickiness
FROM cte A
LEFT JOIN cte W ON W.date BETWEEN DATE_SUB(A.date, INTERVAL 6 DAY) AND A.date -- 기준 날짜 6일 전부터 해당 날짜까지 활성화된 유저의 date를 결합하여 wau 를 측정
GROUP BY A.date
