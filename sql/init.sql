-- Create jobs database
CREATE DATABASE jobs_db;

-- Connect to jobs_db
\c jobs_db;

-- Raw jobs table (scraped data)
CREATE TABLE IF NOT EXISTS raw_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    source VARCHAR(100) NOT NULL,
    url TEXT,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    salary_text TEXT,
    description TEXT,
    posting_date DATE,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data JSONB
);

CREATE INDEX idx_raw_jobs_source ON raw_jobs(source);
CREATE INDEX idx_raw_jobs_posting_date ON raw_jobs(posting_date);
CREATE INDEX idx_raw_jobs_scraped_at ON raw_jobs(scraped_at);

-- Cleaned jobs table (processed data)
CREATE TABLE IF NOT EXISTS cleaned_jobs (
    id SERIAL PRIMARY KEY,
    raw_job_id INTEGER REFERENCES raw_jobs(id),
    job_id VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    company_id INTEGER,
    location_id INTEGER,
    category VARCHAR(200),
    contract_type VARCHAR(100),
    experience_level VARCHAR(100),
    salary_min DECIMAL(10, 2),
    salary_max DECIMAL(10, 2),
    salary_avg DECIMAL(10, 2),
    salary_currency VARCHAR(10),
    description_clean TEXT,
    skills TEXT[],
    remote_type VARCHAR(50),
    posting_date DATE,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cleaned_jobs_category ON cleaned_jobs(category);
CREATE INDEX idx_cleaned_jobs_location_id ON cleaned_jobs(location_id);
CREATE INDEX idx_cleaned_jobs_company_id ON cleaned_jobs(company_id);
CREATE INDEX idx_cleaned_jobs_posting_date ON cleaned_jobs(posting_date);

-- Companies dimension table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL UNIQUE,
    normalized_name VARCHAR(500),
    industry VARCHAR(200),
    size_category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_companies_normalized_name ON companies(normalized_name);

-- Locations dimension table
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    city VARCHAR(200),
    region VARCHAR(200),
    department VARCHAR(100),
    country VARCHAR(100) DEFAULT 'France',
    normalized_location VARCHAR(500) UNIQUE,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_locations_city ON locations(city);
CREATE INDEX idx_locations_region ON locations(region);

-- Job categories dimension table
CREATE TABLE IF NOT EXISTS job_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(200) UNIQUE NOT NULL,
    parent_category VARCHAR(200),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job analytics table (aggregated data)
CREATE TABLE IF NOT EXISTS job_analytics (
    id SERIAL PRIMARY KEY,
    analysis_date DATE DEFAULT CURRENT_DATE,
    category VARCHAR(200),
    location VARCHAR(200),
    job_count INTEGER,
    avg_salary DECIMAL(10, 2),
    min_salary DECIMAL(10, 2),
    max_salary DECIMAL(10, 2),
    median_salary DECIMAL(10, 2),
    remote_percentage DECIMAL(5, 2),
    top_skills TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(analysis_date, category, location)
);

CREATE INDEX idx_job_analytics_date ON job_analytics(analysis_date);
CREATE INDEX idx_job_analytics_category ON job_analytics(category);

-- Salary trends table
CREATE TABLE IF NOT EXISTS salary_trends (
    id SERIAL PRIMARY KEY,
    period_start DATE,
    period_end DATE,
    category VARCHAR(200),
    location VARCHAR(200),
    experience_level VARCHAR(100),
    avg_salary DECIMAL(10, 2),
    sample_size INTEGER,
    trend_direction VARCHAR(20), -- up, down, stable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_salary_trends_period ON salary_trends(period_start, period_end);
CREATE INDEX idx_salary_trends_category ON salary_trends(category);

-- Add foreign key constraints
ALTER TABLE cleaned_jobs
ADD CONSTRAINT fk_company
FOREIGN KEY (company_id) REFERENCES companies(id);

ALTER TABLE cleaned_jobs
ADD CONSTRAINT fk_location
FOREIGN KEY (location_id) REFERENCES locations(id);

-- Insert sample job categories
INSERT INTO job_categories (category_name, parent_category) VALUES
('Développement Web', 'Informatique'),
('Data Science', 'Informatique'),
('Data Engineering', 'Informatique'),
('DevOps', 'Informatique'),
('Cybersécurité', 'Informatique'),
('Intelligence Artificielle', 'Informatique'),
('Développement Mobile', 'Informatique'),
('Cloud Computing', 'Informatique'),
('Marketing Digital', 'Marketing'),
('Ressources Humaines', 'RH'),
('Finance', 'Finance'),
('Ventes', 'Commercial')
ON CONFLICT (category_name) DO NOTHING;

-- Insert sample French locations
INSERT INTO locations (city, region, department, normalized_location) VALUES
('Paris', 'Île-de-France', '75', 'paris-ile-de-france-france'),
('Lyon', 'Auvergne-Rhône-Alpes', '69', 'lyon-auvergne-rhone-alpes-france'),
('Marseille', 'Provence-Alpes-Côte d''Azur', '13', 'marseille-provence-alpes-cote-d-azur-france'),
('Toulouse', 'Occitanie', '31', 'toulouse-occitanie-france'),
('Nice', 'Provence-Alpes-Côte d''Azur', '06', 'nice-provence-alpes-cote-d-azur-france'),
('Nantes', 'Pays de la Loire', '44', 'nantes-pays-de-la-loire-france'),
('Bordeaux', 'Nouvelle-Aquitaine', '33', 'bordeaux-nouvelle-aquitaine-france'),
('Lille', 'Hauts-de-France', '59', 'lille-hauts-de-france-france'),
('Strasbourg', 'Grand Est', '67', 'strasbourg-grand-est-france'),
('Rennes', 'Bretagne', '35', 'rennes-bretagne-france')
ON CONFLICT (normalized_location) DO NOTHING;

-- Create a view for easy analytics
CREATE OR REPLACE VIEW vw_job_summary AS
SELECT 
    cj.id,
    cj.title,
    c.name as company,
    l.city,
    l.region,
    cj.category,
    cj.contract_type,
    cj.experience_level,
    cj.salary_avg,
    cj.remote_type,
    cj.posting_date,
    cj.skills
FROM cleaned_jobs cj
LEFT JOIN companies c ON cj.company_id = c.id
LEFT JOIN locations l ON cj.location_id = l.id;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE jobs_db TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;
