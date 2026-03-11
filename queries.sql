-- 1. From the two most commonly appearing regions, which is the latest datasource?

WITH top_regions AS (
    SELECT region
    FROM trips
    GROUP BY region
    ORDER BY COUNT(*) DESC
    LIMIT 2
),
latest_per_region AS (
    SELECT 
        t.region, 
        t.datasource,
        t.datetime,
        ROW_NUMBER() OVER (PARTITION BY t.region ORDER BY t.datetime DESC) as rn
    FROM trips t
    JOIN top_regions tr ON t.region = tr.region
)
SELECT region, datasource, datetime as latest_appearance
FROM latest_per_region
WHERE rn = 1;


-- 2. What regions has the "cheap_mobile" datasource appeared in?

SELECT DISTINCT region
FROM trips
WHERE datasource = 'cheap_mobile'
ORDER BY region;
