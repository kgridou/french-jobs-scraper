-- Sample SQL Queries for French Job Scraper Database
-- Connect to jobs_db and run these queries to explore the data

-- ============================================
-- BASIC QUERIES
-- ============================================

-- View recent job postings
SELECT 
    title, 
    company, 
    location, 
    salary_avg,
    posting_date
FROM vw_job_summary
ORDER BY posting_date DESC
LIMIT 20;

-- Count total jobs by source
SELECT 
    source, 
    COUNT(*) as total_jobs
FROM raw_jobs
GROUP BY source;

-- Jobs scraped today
SELECT COUNT(*) as jobs_today
FROM raw_jobs
WHERE scraped_at::date = CURRENT_DATE;

-- ============================================
-- SALARY ANALYSIS
-- ============================================

-- Average salary by category
SELECT 
    category,
    COUNT(*) as job_count,
    ROUND(AVG(salary_avg), 2) as avg_salary,
    ROUND(MIN(salary_min), 2) as min_salary,
    ROUND(MAX(salary_max), 2) as max_salary
FROM cleaned_jobs
WHERE salary_avg IS NOT NULL
GROUP BY category
ORDER BY avg_salary DESC;

-- Salary distribution by experience level
SELECT 
    experience_level,
    category,
    ROUND(AVG(salary_avg), 2) as avg_salary,
    COUNT(*) as job_count
FROM cleaned_jobs
WHERE salary_avg IS NOT NULL
GROUP BY experience_level, category
ORDER BY category, avg_salary DESC;

-- Top paying cities
SELECT 
    l.city,
    l.region,
    COUNT(*) as job_count,
    ROUND(AVG(cj.salary_avg), 2) as avg_salary
FROM cleaned_jobs cj
JOIN locations l ON cj.location_id = l.id
WHERE cj.salary_avg IS NOT NULL
GROUP BY l.city, l.region
HAVING COUNT(*) >= 5
ORDER BY avg_salary DESC
LIMIT 10;

-- ============================================
-- JOB MARKET TRENDS
-- ============================================

-- Most in-demand job categories
SELECT 
    category,
    COUNT(*) as job_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM cleaned_jobs
WHERE posting_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY category
ORDER BY job_count DESC;

-- Top hiring companies (last 30 days)
SELECT 
    c.name as company,
    COUNT(*) as job_postings,
    STRING_AGG(DISTINCT cj.category, ', ') as categories
FROM cleaned_jobs cj
JOIN companies c ON cj.company_id = c.id
WHERE cj.posting_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.name
ORDER BY job_postings DESC
LIMIT 15;

-- Remote work statistics
SELECT 
    remote_type,
    COUNT(*) as job_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM cleaned_jobs
GROUP BY remote_type
ORDER BY job_count DESC;

-- Jobs by contract type
SELECT 
    contract_type,
    COUNT(*) as job_count,
    ROUND(AVG(salary_avg), 2) as avg_salary
FROM cleaned_jobs
GROUP BY contract_type
ORDER BY job_count DESC;

-- ============================================
-- SKILLS ANALYSIS
-- ============================================

-- Most common skills across all jobs
SELECT 
    UNNEST(skills) as skill,
    COUNT(*) as frequency
FROM cleaned_jobs
WHERE skills IS NOT NULL
GROUP BY skill
ORDER BY frequency DESC
LIMIT 20;

-- Skills by category
SELECT 
    category,
    UNNEST(skills) as skill,
    COUNT(*) as frequency
FROM cleaned_jobs
WHERE category = 'Data Engineering'
  AND skills IS NOT NULL
GROUP BY category, skill
ORDER BY frequency DESC
LIMIT 10;

-- ============================================
-- GEOGRAPHIC ANALYSIS
-- ============================================

-- Job distribution by region
SELECT 
    l.region,
    COUNT(*) as job_count,
    COUNT(DISTINCT c.id) as unique_companies,
    ROUND(AVG(cj.salary_avg), 2) as avg_salary
FROM cleaned_jobs cj
JOIN locations l ON cj.location_id = l.id
LEFT JOIN companies c ON cj.company_id = c.id
GROUP BY l.region
ORDER BY job_count DESC;

-- Top cities with most tech jobs
SELECT 
    l.city,
    l.region,
    COUNT(*) as job_count
FROM cleaned_jobs cj
JOIN locations l ON cj.location_id = l.id
WHERE cj.category IN ('Développement Web', 'Data Science', 'Data Engineering', 'DevOps')
GROUP BY l.city, l.region
ORDER BY job_count DESC
LIMIT 10;

-- ============================================
-- TIME-BASED ANALYSIS
-- ============================================

-- Jobs posted per day (last 7 days)
SELECT 
    posting_date,
    COUNT(*) as jobs_posted
FROM cleaned_jobs
WHERE posting_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY posting_date
ORDER BY posting_date DESC;

-- Weekly job posting trends
SELECT 
    DATE_TRUNC('week', posting_date) as week_start,
    COUNT(*) as jobs_posted,
    COUNT(DISTINCT company_id) as unique_companies
FROM cleaned_jobs
WHERE posting_date >= CURRENT_DATE - INTERVAL '3 months'
GROUP BY week_start
ORDER BY week_start DESC;

-- ============================================
-- ANALYTICS TABLES
-- ============================================

-- Latest job analytics summary
SELECT 
    analysis_date,
    category,
    location,
    job_count,
    ROUND(avg_salary, 2) as avg_salary,
    remote_percentage
FROM job_analytics
WHERE analysis_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY analysis_date DESC, job_count DESC
LIMIT 20;

-- Salary trends over time
SELECT 
    period_start,
    category,
    location,
    experience_level,
    ROUND(avg_salary, 2) as avg_salary,
    sample_size,
    trend_direction
FROM salary_trends
WHERE period_start >= CURRENT_DATE - INTERVAL '6 months'
ORDER BY period_start DESC, category
LIMIT 30;

-- ============================================
-- DATA QUALITY CHECKS
-- ============================================

-- Check for duplicate job IDs
SELECT 
    job_id, 
    COUNT(*) as duplicate_count
FROM cleaned_jobs
GROUP BY job_id
HAVING COUNT(*) > 1;

-- Jobs with missing critical information
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE title IS NULL) as missing_title,
    COUNT(*) FILTER (WHERE company_id IS NULL) as missing_company,
    COUNT(*) FILTER (WHERE location_id IS NULL) as missing_location,
    COUNT(*) FILTER (WHERE category = 'Autre') as uncategorized
FROM cleaned_jobs;

-- Recent processing statistics
SELECT 
    DATE(processed_at) as process_date,
    COUNT(*) as jobs_processed,
    COUNT(*) FILTER (WHERE salary_avg IS NOT NULL) as jobs_with_salary,
    COUNT(DISTINCT category) as categories_found
FROM cleaned_jobs
WHERE processed_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(processed_at)
ORDER BY process_date DESC;

-- ============================================
-- ADVANCED QUERIES
-- ============================================

-- Companies with highest salary variance
SELECT 
    c.name as company,
    COUNT(*) as job_count,
    ROUND(AVG(cj.salary_avg), 2) as avg_salary,
    ROUND(STDDEV(cj.salary_avg), 2) as salary_stddev,
    ROUND(MIN(cj.salary_min), 2) as min_salary,
    ROUND(MAX(cj.salary_max), 2) as max_salary
FROM cleaned_jobs cj
JOIN companies c ON cj.company_id = c.id
WHERE cj.salary_avg IS NOT NULL
GROUP BY c.name
HAVING COUNT(*) >= 5
ORDER BY salary_stddev DESC
LIMIT 10;

-- Job market competitiveness (jobs per company)
SELECT 
    category,
    COUNT(DISTINCT company_id) as num_companies,
    COUNT(*) as total_jobs,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT company_id), 2) as jobs_per_company
FROM cleaned_jobs
GROUP BY category
HAVING COUNT(DISTINCT company_id) >= 5
ORDER BY jobs_per_company DESC;

-- Emerging job categories (growth over last 30 days)
WITH current_period AS (
    SELECT category, COUNT(*) as current_count
    FROM cleaned_jobs
    WHERE posting_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY category
),
previous_period AS (
    SELECT category, COUNT(*) as previous_count
    FROM cleaned_jobs
    WHERE posting_date >= CURRENT_DATE - INTERVAL '60 days'
      AND posting_date < CURRENT_DATE - INTERVAL '30 days'
    GROUP BY category
)
SELECT 
    c.category,
    c.current_count,
    COALESCE(p.previous_count, 0) as previous_count,
    c.current_count - COALESCE(p.previous_count, 0) as growth,
    CASE 
        WHEN p.previous_count > 0 THEN
            ROUND(100.0 * (c.current_count - p.previous_count) / p.previous_count, 2)
        ELSE NULL
    END as growth_percentage
FROM current_period c
LEFT JOIN previous_period p ON c.category = p.category
ORDER BY growth DESC;
