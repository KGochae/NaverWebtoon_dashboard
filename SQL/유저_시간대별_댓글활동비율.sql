
WITH CTE as (
SELECT user_id 
    , comment_date
    , DATE(comment_date) as date
    , EXTRACT(HOUR FROM comment_date) as hour
    , CASE WHEN EXTRACT(HOUR FROM comment_date) BETWEEN 6 AND 12 THEN 1 ELSE 0 END AS morning 
    , CASE WHEN EXTRACT(HOUR FROM comment_date) BETWEEN 12 AND 18 THEN 1 ELSE 0 END AS day 
    , CASE WHEN EXTRACT(HOUR FROM comment_date) BETWEEN 0 AND 6 
                OR EXTRACT(HOUR FROM comment_date) BETWEEN 18 AND 24  THEN 1 ELSE 0 END AS night       
FROM WEBTOON.user)


  
  SELECT user_id
    , SUM(morning) as morning_cnt
    , SUM(day) as day_cnt
    , SUM(night) as night_cnt
    , COUNT(user_id) AS total_cnt
    , ROUND(SUM(morning)*100/ COUNT(user_id),2) as morning_ratio
    , ROUND(SUM(day)*100/ COUNT(user_id),2) as day_ratio
    , ROUND(SUM(night)*100/ COUNT(user_id),2) as night_ratio
FROM CTE
GROUP BY user_id 
