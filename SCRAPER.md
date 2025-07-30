# Job Scraper Documentation

## 1. Purpose of the Scraper

The Job Scraper is designed to extract comprehensive job listings from devsunite.com, a platform hosting various tech job opportunities. Its primary goals are:

- **Collect Job Listings**: Automatically retrieve all available job listings from the platform
- **Extract Detailed Information**: Gather comprehensive details about each job, including:
  - Job title/role
  - Company information
  - Job type (Full-time, Part-time, Contract, etc.)
  - Location (Remote, On-site, Hybrid)
  - Required experience
  - Detailed job descriptions
  - Required skills and technologies
  - Compensation details (when available)
  - Application links
- **Structure Data**: Convert the scraped information into a consistent format for storage in a database
- **Provide Regular Updates**: Support scheduled execution to keep job listings current
- **Ensure Resilience**: Handle website changes, network issues, and other potential failures gracefully

## 2. Architecture

The job scraper follows a modular architecture designed for robustness, maintainability, and adaptability:

### High-Level Architecture

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│                │     │                │     │                │
│  Web Browser   │────▶│  Job Scraper   │────▶│   Database     │
│  (Selenium)    │     │  (Extraction)  │     │   (Django ORM) │
│                │     │                │     │                │
└────────────────┘     └────────────────┘     └────────────────┘
```

### Key Architectural Elements

1. **Browser Layer**:
   - Uses Selenium WebDriver with Chrome/Chromium
   - Handles JavaScript-rendered content
   - Manages browser sessions and navigation

2. **Extraction Layer**:
   - Parses HTML content using BeautifulSoup
   - Contains specialized extractors for different data points
   - Implements fallback strategies for resilient extraction

3. **Data Management Layer**:
   - Converts extracted data to Django models
   - Handles data validation and normalization
   - Manages database operations (create/update records)

4. **Control Flow**:
   - Entry point via Django management command or API endpoint
   - Orchestrates the scraping process
   - Implements error handling and reporting

## 3. Key Components

### 3.1 Browser Component

The browser component is responsible for loading the job listing pages and handling JavaScript-rendered content:

```python
def _setup_browser(self):
    """Setup and return a browser instance for scraping"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Create browser instance
    return webdriver.Chrome(options=chrome_options)
```

### 3.2 Job Listing Extractor

This component handles extraction of job listings from the main job board page:

```python
def _find_job_cards(self, soup):
    """Extract job cards from the page using multiple selector strategies"""
    # Primary selector strategy
    job_cards = soup.select('div.group.relative')
    
    # Fallback selector if primary fails
    if not job_cards:
        job_cards = soup.select('div[class*="group"][class*="relative"]')
    
    return job_cards
```

### 3.3 Job Details Extractor

This specialized component extracts detailed information from individual job pages:

```python
def _extract_job_details(self, driver, job_url):
    """Extract detailed job information from the job details page"""
    try:
        driver.get(job_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Parse page content
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract detailed description
        description = self._extract_job_description(soup)
        
        # Extract required skills
        skills = self._extract_skills(soup, description)
        
        return {
            'description': description,
            'skills': skills
        }
    except Exception as e:
        logging.error(f"Error extracting job details: {e}")
        return {}
```

### 3.4 Data Processing Component

This component handles the transformation and storage of scraped job data:

```python
def _process_job_data(self, job_data):
    """Process and save job data to the database"""
    try:
        # Check if job already exists
        existing_job = Job.objects.filter(
            role=job_data['role'],
            company_name=job_data['company_name']
        ).first()
        
        if existing_job:
            # Update existing job
            for key, value in job_data.items():
                setattr(existing_job, key, value)
            existing_job.save()
            return existing_job, False
        else:
            # Create new job
            job = Job.objects.create(**job_data)
            return job, True
    except Exception as e:
        logging.error(f"Error processing job data: {e}")
        return None, False
```

### 3.5 Orchestration Component

The orchestration component manages the overall scraping process:

```python
def refresh(self, request):
    """API endpoint to refresh job listings"""
    try:
        driver = self._setup_browser()
        jobs_created = 0
        jobs_updated = 0
        
        try:
            # Navigate to jobs page
            driver.get('https://devsunite.com/jobs')
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
            
            # Extract job listings
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            job_cards = self._find_job_cards(soup)
            
            # Process each job listing
            for card in job_cards:
                job_data = self._extract_job_from_card(card, driver)
                if job_data:
                    job, is_new = self._process_job_data(job_data)
                    if job:
                        if is_new:
                            jobs_created += 1
                        else:
                            jobs_updated += 1
            
            return Response({
                "success": True,
                "jobs_scraped": jobs_created + jobs_updated,
                "jobs_created": jobs_created,
                "jobs_updated": jobs_updated
            })
        finally:
            driver.quit()
    except Exception as e:
        logging.error(f"Error in refresh: {e}")
        return Response({
            "success": False,
            "message": str(e)
        }, status=500)
```

## 4. Usage

The job scraper can be used in multiple ways:

### 4.1 Via Management Command

```bash
# Run from the backend directory
python manage.py scrapejobs
```

Optional arguments:
```bash
# Specify number of pages to scrape
python manage.py scrapejobs --pages 5

# Run in verbose mode
python manage.py scrapejobs --verbose
```

### 4.2 Via API Endpoint

```python
# Using requests library
import requests

response = requests.post("http://localhost:8000/api/jobs/refresh/")
print(response.json())
```

Example response:
```json
{
  "success": true,
  "jobs_scraped": 25,
  "jobs_created": 15,
  "jobs_updated": 10
}
```

### 4.3 Scheduled Execution

You can schedule the scraper to run automatically using Django's built-in scheduler or a cron job:

```python
# In your crontab
0 9 * * * cd /path/to/project/backend && python manage.py scrapejobs
```

### 4.4 Integration in Custom Code

```python
from jobs.views import JobViewSet
from rest_framework.request import Request

# Create a mock request
request = Request(HttpRequest())
request.method = 'POST'

# Initialize viewset
viewset = JobViewSet()

# Call refresh method
response = viewset.refresh(request)

# Process response
if response.data['success']:
    print(f"Scraped {response.data['jobs_scraped']} jobs")
else:
    print(f"Error: {response.data['message']}")
```

## 5. Error Handling

The scraper implements a comprehensive error handling strategy to ensure robustness:

### 5.1 Browser-Level Error Handling

```python
try:
    driver = self._setup_browser()
    # Scraping operations...
except WebDriverException as e:
    logging.error(f"Browser error: {e}")
    return Response({"success": False, "message": "Browser error"}, status=500)
finally:
    if driver:
        driver.quit()
```

### 5.2 Extraction Error Handling

```python
def _extract_job_title(self, card):
    """Extract job title with fallback mechanisms"""
    try:
        # Primary selector
        title_elem = card.select_one('div.tracking-tight')
        if title_elem and title_elem.text.strip():
            return title_elem.text.strip()
        
        # Fallback selectors
        title_elem = card.select_one('div[class*="font-semibold"]')
        if title_elem:
            return title_elem.text.strip()
            
        # Additional fallback
        title_elem = card.find('div', {'class': 'text-lg'})
        if title_elem:
            return title_elem.text.strip()
    except Exception as e:
        logging.warning(f"Error extracting job title: {e}")
    
    return "Unknown Position"  # Default value if all extraction attempts fail
```

### 5.3 Data Validation

```python
def _validate_job_data(self, job_data):
    """Validate job data before saving"""
    required_fields = ['role', 'company_name']
    
    # Check for required fields
    for field in required_fields:
        if not job_data.get(field):
            return False
    
    # Normalize data
    if job_data.get('job_type'):
        job_data['job_type'] = job_data['job_type'].lower()
    
    return True
```

### 5.4 Exception Logging

The scraper implements comprehensive logging:

```python
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
```

### 5.5 Graceful Degradation

The scraper is designed to continue functioning even when parts of the extraction process fail:

```python
# Attempt to extract job details but continue if it fails
try:
    job_details = self._extract_job_details(driver, job_url)
    job_data.update(job_details)
except Exception as e:
    logging.error(f"Error extracting job details: {e}")
    # Continue with basic job data even if details extraction fails
```

This ensures that basic job data is still collected even if detailed information extraction fails for some reason.
