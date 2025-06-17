# 활성화 기준을 유저들이 댓글을 작성한 행위로 보았습니다. 
# DAU : 일별 활성화 고유한 유저수
# WAU : 주간 활성화 고유한 유저수 (기준 날짜 6일 전부터 해당 날짜까지 활성화된 유저)
# Stickiness : 기준 날짜의 독자 고착도

# 첫번째 방법. 자기 자신과 범위조인하여 dau, wau를 한테이블에 구하는 방법
with cte as (
  SELECT user_id
        , DATE(comment_date) as date -- 댓글을 작성한 날짜를 %Y-%m-%d 형태로 변환 
  FROM WEBTOON.user 
)

SELECT A.date as date
    , COUNT(DISTINCT A.user_id) as DAU
    , COUNT(DISTINCT W.user_id) as WAU
    , COUNT(DISTINCT A.user_id)/COUNT(DISTINCT W.user_id) AS Stickiness
FROM cte A
LEFT JOIN cte W ON W.date BETWEEN DATE_SUB(A.date, INTERVAL 6 DAY) AND A.date 
GROUP BY A.date


# 두번째 방법. dau와 wau 를 따로 테이블을 만들어서 결합
-- DAU
WITH daily AS (
  SELECT DATE(comment_date) AS date
        , COUNT(DISTINCT user_id) AS DAU
  FROM WEBTOON.user
  GROUP BY date
),

--WAU 
weekday AS (
  SELECT d1.date AS date
        , COUNT(DISTINCT d2.user_id) AS WAU
  FROM (
    SELECT DISTINCT DATE(comment_date) AS date
    FROM WEBTOON.user 
  ) d1 -- WAU 계산 시 기준이 되는 날짜 목록
  JOIN WEBTOON.user d2 ON DATE(d2.comment_date) BETWEEN DATE_SUB(d1.date, INTERVAL 6 DAY) AND d1.date
  GROUP BY d1.date
)

-- 결합
SELECT d.date
  , d.DAU
  , w.WAU
  , d.DAU / w.WAU AS Stickiness
FROM daily d
JOIN weekday w ON d.date = w.date
ORDER BY d.date
