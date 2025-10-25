-- Analytics Queries for French Jobs Data
-- Business Intelligence and Reporting Queries

-- ============================================
-- 1. TOP HIRING COMPANIES
-- ============================================
-- Find companies posting the most jobs
SELECT 
    company,
    COUNT(*) as job_count,
    AVG((salary_min + salary_max) / 2) as avg_salary,
    COUNT(CASE WHEN remote_type IN ('Remote', 'Hybrid') THEN 1 END) as remote_jobs,
    ARRAY_AGG(DISTINCT contract_type) as contract_types
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND posted_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY company
ORDER BY job_count DESC
LIMIT 20;


-- ============================================
-- 2. SALARY TRENDS BY REGION
-- ============================================
-- Analyze salary distribution across French regions
SELECT 
    region,
    COUNT(*) as job_count,
    MIN(salary_min) as min_salary,
    AVG((salary_min + salary_max) / 2) as avg_salary,
    MAX(salary_max) as max_salary,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (salary_min + salary_max) / 2) as median_salary
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND salary_min IS NOT NULL
    AND region IS NOT NULL
GROUP BY region
ORDER BY avg_salary DESC;


-- ============================================
-- 3. MOST IN-DEMAND SKILLS
-- ============================================
-- Skills appearing most frequently in job postings
WITH skill_counts AS (
    SELECT 
        jsonb_array_elements_text(required_skills) as skill,
        COUNT(*) as frequency,
        AVG((salary_min + salary_max) / 2) as avg_salary_for_skill
    FROM jobs_data.jobs
    WHERE is_active = TRUE
        AND required_skills IS NOT NULL
        AND posted_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY jsonb_array_elements_text(required_skills)
)
SELECT 
    skill,
    frequency as job_count,
    ROUND(avg_salary_for_skill, 0) as avg_salary_euros,
    ROUND(frequency * 100.0 / SUM(frequency) OVER (), 2) as percentage
FROM skill_counts
WHERE frequency > 5
ORDER BY frequency DESC
LIMIT 30;


-- ============================================
-- 4. REMOTE WORK STATISTICS
-- ============================================
-- Remote vs On-site job distribution
SELECT 
    remote_type,
    COUNT(*) as job_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
    AVG((salary_min + salary_max) / 2) as avg_salary,
    COUNT(DISTINCT company) as company_count
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND posted_date >= CURRENT_DATE - INTERVAL '60 days'
GROUP BY remote_type
ORDER BY job_count DESC;


-- ============================================
-- 5. CONTRACT TYPE DISTRIBUTION
-- ============================================
-- CDI, CDD, Stage, etc. breakdown
SELECT 
    contract_type,
    COUNT(*) as job_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
    AVG((salary_min + salary_max) / 2) as avg_salary
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND contract_type IS NOT NULL
GROUP BY contract_type
ORDER BY job_count DESC;


-- ============================================
-- 6. DAILY JOB POSTING TRENDS
-- ============================================
-- Track job posting volume over time
SELECT 
    DATE(posted_date) as date,
    COUNT(*) as jobs_posted,
    COUNT(DISTINCT company) as active_companies,
    AVG((salary_min + salary_max) / 2) as avg_salary
FROM jobs_data.jobs
WHERE posted_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(posted_date)
ORDER BY date DESC;


-- ============================================
-- 7. TOP CITIES FOR JOBS
-- ============================================
-- Cities with most job opportunities
SELECT 
    city,
    COUNT(*) as job_count,
    COUNT(DISTINCT company) as company_count,
    AVG((salary_min + salary_max) / 2) as avg_salary,
    COUNT(CASE WHEN remote_type != 'On-site' THEN 1 END) as remote_friendly_jobs
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND city IS NOT NULL
GROUP BY city
ORDER BY job_count DESC
LIMIT 20;


-- ============================================
-- 8. EXPERIENCE LEVEL DISTRIBUTION
-- ============================================
-- Jobs by experience level required
SELECT 
    experience_level,
    COUNT(*) as job_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
    AVG((salary_min + salary_max) / 2) as avg_salary
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND experience_level IS NOT NULL
GROUP BY experience_level
ORDER BY 
    CASE experience_level
        WHEN 'Junior' THEN 1
        WHEN 'Mid-level' THEN 2
        WHEN 'Senior' THEN 3
        ELSE 4
    END;


-- ============================================
-- 9. INDUSTRY ANALYSIS
-- ============================================
-- Job distribution across industries
SELECT 
    industry,
    COUNT(*) as job_count,
    AVG((salary_min + salary_max) / 2) as avg_salary,
    COUNT(DISTINCT company) as company_count
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND industry IS NOT NULL
GROUP BY industry
ORDER BY job_count DESC
LIMIT 15;


-- ============================================
-- 10. SKILL COMBINATIONS
-- ============================================
-- Find common skill combinations
WITH skill_pairs AS (
    SELECT 
        j1.skill_name as skill1,
        j2.skill_name as skill2,
        COUNT(*) as frequency
    FROM jobs_data.job_skills j1
    JOIN jobs_data.job_skills j2 ON j1.job_id = j2.job_id
    WHERE j1.skill_id < j2.skill_id  -- Avoid duplicates
    GROUP BY j1.skill_name, j2.skill_name
)
SELECT 
    skill1 || ' + ' || skill2 as skill_combination,
    frequency as appears_together
FROM skill_pairs
WHERE frequency > 10
ORDER BY frequency DESC
LIMIT 20;


-- ============================================
-- 11. SALARY COMPARISON BY SOURCE
-- ============================================
-- Compare job characteristics across sources
SELECT 
    source,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN salary_min IS NOT NULL THEN 1 END) as jobs_with_salary,
    AVG((salary_min + salary_max) / 2) as avg_salary,
    COUNT(CASE WHEN remote_type IN ('Remote', 'Hybrid') THEN 1 END) as remote_jobs,
    AVG(EXTRACT(DAY FROM CURRENT_DATE - posted_date)) as avg_days_old
FROM jobs_data.jobs
WHERE is_active = TRUE
GROUP BY source
ORDER BY total_jobs DESC;


-- ============================================
-- 12. WEEKLY COMPARISON
-- ============================================
-- Compare this week vs last week
WITH this_week AS (
    SELECT COUNT(*) as jobs_this_week
    FROM jobs_data.jobs
    WHERE posted_date >= DATE_TRUNC('week', CURRENT_DATE)
),
last_week AS (
    SELECT COUNT(*) as jobs_last_week
    FROM jobs_data.jobs
    WHERE posted_date >= DATE_TRUNC('week', CURRENT_DATE - INTERVAL '7 days')
        AND posted_date < DATE_TRUNC('week', CURRENT_DATE)
)
SELECT 
    jobs_this_week,
    jobs_last_week,
    jobs_this_week - jobs_last_week as difference,
    ROUND((jobs_this_week - jobs_last_week) * 100.0 / NULLIF(jobs_last_week, 0), 2) as percent_change
FROM this_week, last_week;


-- ============================================
-- 13. COMPANIES HIRING FOR REMOTE ROLES
-- ============================================
-- Find remote-friendly companies
SELECT 
    company,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN remote_type = 'Remote' THEN 1 END) as fully_remote,
    COUNT(CASE WHEN remote_type = 'Hybrid' THEN 1 END) as hybrid,
    ROUND(COUNT(CASE WHEN remote_type != 'On-site' THEN 1 END) * 100.0 / COUNT(*), 2) as remote_percentage
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND posted_date >= CURRENT_DATE - INTERVAL '60 days'
GROUP BY company
HAVING COUNT(CASE WHEN remote_type != 'On-site' THEN 1 END) > 0
ORDER BY remote_percentage DESC, total_jobs DESC
LIMIT 20;


-- ============================================
-- 14. SALARY RANGES BY CONTRACT TYPE
-- ============================================
-- Box plot data for salary by contract type
SELECT 
    contract_type,
    COUNT(*) as sample_size,
    MIN(salary_min) as min_salary,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY (salary_min + salary_max) / 2) as q1_salary,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (salary_min + salary_max) / 2) as median_salary,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY (salary_min + salary_max) / 2) as q3_salary,
    MAX(salary_max) as max_salary,
    AVG((salary_min + salary_max) / 2) as mean_salary
FROM jobs_data.jobs
WHERE salary_min IS NOT NULL
    AND contract_type IS NOT NULL
    AND is_active = TRUE
GROUP BY contract_type
ORDER BY median_salary DESC;


-- ============================================
-- 15. JOB GROWTH RATE BY REGION
-- ============================================
-- Regional job market growth
WITH monthly_stats AS (
    SELECT 
        region,
        DATE_TRUNC('month', posted_date) as month,
        COUNT(*) as job_count
    FROM jobs_data.jobs
    WHERE posted_date >= CURRENT_DATE - INTERVAL '6 months'
        AND region IS NOT NULL
    GROUP BY region, DATE_TRUNC('month', posted_date)
)
SELECT 
    region,
    month,
    job_count,
    LAG(job_count) OVER (PARTITION BY region ORDER BY month) as prev_month,
    job_count - LAG(job_count) OVER (PARTITION BY region ORDER BY month) as growth,
    ROUND(
        (job_count - LAG(job_count) OVER (PARTITION BY region ORDER BY month)) * 100.0 / 
        NULLIF(LAG(job_count) OVER (PARTITION BY region ORDER BY month), 0), 
        2
    ) as growth_percentage
FROM monthly_stats
ORDER BY region, month DESC;


-- ============================================
-- 16. JOBS REQUIRING MULTIPLE SKILLS
-- ============================================
-- Jobs requiring the most skills (complexity indicator)
SELECT 
    title,
    company,
    location,
    jsonb_array_length(required_skills) as skill_count,
    (salary_min + salary_max) / 2 as avg_salary,
    contract_type
FROM jobs_data.jobs
WHERE is_active = TRUE
    AND required_skills IS NOT NULL
    AND jsonb_array_length(required_skills) > 5
ORDER BY skill_count DESC, avg_salary DESC
LIMIT 50;


-- ============================================
-- 17. DATA QUALITY METRICS
-- ============================================
-- Monitor data completeness
SELECT 
    source,
    COUNT(*) as total_jobs,
    ROUND(COUNT(CASE WHEN title IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as title_completeness,
    ROUND(COUNT(CASE WHEN company IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as company_completeness,
    ROUND(COUNT(CASE WHEN salary_min IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as salary_completeness,
    ROUND(COUNT(CASE WHEN description IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as description_completeness,
    ROUND(COUNT(CASE WHEN required_skills IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as skills_completeness
FROM jobs_data.jobs
GROUP BY source
ORDER BY total_jobs DESC;


-- ============================================
-- 18. EMERGING SKILLS TREND
-- ============================================
-- Skills gaining popularity over time
WITH skill_timeline AS (
    SELECT 
        jsonb_array_elements_text(required_skills) as skill,
        DATE_TRUNC('month', posted_date) as month,
        COUNT(*) as frequency
    FROM jobs_data.jobs
    WHERE posted_date >= CURRENT_DATE - INTERVAL '6 months'
        AND required_skills IS NOT NULL
    GROUP BY jsonb_array_elements_text(required_skills), DATE_TRUNC('month', posted_date)
)
SELECT 
    skill,
    month,
    frequency,
    LAG(frequency) OVER (PARTITION BY skill ORDER BY month) as prev_month_freq,
    frequency - LAG(frequency) OVER (PARTITION BY skill ORDER BY month) as growth
FROM skill_timeline
WHERE skill IN (
    SELECT jsonb_array_elements_text(required_skills)
    FROM jobs_data.jobs
    WHERE posted_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY jsonb_array_elements_text(required_skills)
    ORDER BY COUNT(*) DESC
    LIMIT 20
)
ORDER BY skill, month DESC;
