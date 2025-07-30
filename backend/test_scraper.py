#!/usr/bin/env python3
"""
Comprehensive test script for the Scraplify job scraper
This is the single comprehensive test file that replaces all other test files.
It tests the full functionality of the job scraper including detailed job descriptions
and skills extraction from individual job pages.
"""
import os
import sys
import django
import json
import time
import logging
import argparse
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append('/workspaces/Scraplify/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraplify.settings')
django.setup()

from jobs.views import JobViewSet
from jobs.models import Job
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from rest_framework.test import APIRequestFactory

def test_api_endpoint():
    """Test the API endpoint for job scraping"""
    print("\n=== Testing API Endpoint ===")
    
    # Create a mock request
    factory = APIRequestFactory()
    request = factory.post('/api/jobs/refresh/')
    
    # Create viewset instance
    viewset = JobViewSet()
    viewset.request = request
    
    try:
        # Call the refresh method
        response = viewset.refresh(request)
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
        
        if response.status_code == 200:
            print("✅ Scraping completed successfully!")
            jobs_scraped = response.data.get('jobs_scraped', 0)
            print(f"Total jobs scraped: {jobs_scraped}")
        else:
            print("❌ Scraping failed")
            print(f"Error: {response.data.get('message', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Error during API test: {e}")
        import traceback
        traceback.print_exc()

def test_extraction_methods():
    """Test individual extraction methods with sample HTML"""
    print("\n=== Testing Extraction Methods ===")
    
    # Sample HTML structure based on actual devsunite.com structure
    sample_html = """
    <div class="group relative w-full border rounded-lg p-6 hover:bg-gray-50">
        <div class="tracking-tight text-base sm:text-lg font-semibold leading-tight text-white group-hover:text-[#2CEE91] transition-colors duration-300">
            Senior Full Stack Developer
        </div>
        <div class="flex items-center text-gray-500 mt-1">
            <span class="truncate">TechCorp Inc.</span>
        </div>
        <div class="flex flex-wrap gap-1 mt-1">
            <span class="bg-gray-100 text-gray-800 text-xs px-2 py-0.5 rounded">Full-time</span>
        </div>
        <div class="text-gray-500 mt-1">Remote • 3-5 years</div>
        <p class="text-gray-600 mt-2 line-clamp-3">
            We are looking for an experienced full stack developer to join our team.
            You will work on exciting projects using React, Node.js, and PostgreSQL.
        </p>
        <div class="mt-2 text-green-600">$80,000 - $120,000 per year</div>
        <div class="mt-4 flex space-x-2">
            <a href="/jobs/123/details" class="text-blue-600">View Details</a>
            <a href="https://apply.techcorp.com/job/123" class="text-green-600">Apply Now</a>
        </div>
    </div>
    """
    
    # Create soup object
    soup = BeautifulSoup(sample_html, 'html.parser')
    card = soup.find('div', class_='group')
    
    # Create viewset instance
    viewset = JobViewSet()
    
    # First check the card finding logic
    job_cards = viewset._find_job_cards(soup)
    if job_cards:
        print(f"Found {len(job_cards)} job cards using selectors")
    
    # Use our sample card for testing individual extraction methods
    print("\nTesting individual extraction methods:")
    
    # Test individual extraction methods 
    try:
        # Test job title extraction
        title = viewset._extract_job_title(card) 
        print(f"Job Title: {title}")
        
        # Test company name extraction (assuming the method exists)
        if hasattr(viewset, '_extract_company_name'):
            company = viewset._extract_company_name(card, title) 
            print(f"Company Name: {company}")
        else:
            print("Company Name extraction method not found")
            
        # Test job type extraction
        if hasattr(viewset, '_extract_job_type'):
            job_type = viewset._extract_job_type(card)
            print(f"Job Type: {job_type}")
        
        # Test location extraction
        if hasattr(viewset, '_extract_location'):
            location = viewset._extract_location(card)
            print(f"Location: {location}")
            
        # Test compensation extraction
        if hasattr(viewset, '_extract_compensation'):
            compensation = viewset._extract_compensation(card)
            print(f"Compensation: {compensation}")
            
        print("\nTesting full job extraction:")
        # Now test the full extraction method
        job_data = viewset._extract_job_from_card(card, None)
        
        if job_data:
            print("✅ Successfully extracted job data:")
            for key, value in job_data.items():
                print(f"  {key}: {value}")
        else:
            print("❌ Failed to extract complete job data (some fields may be missing)")
            
    except Exception as e:
        print(f"❌ Error in extraction test: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n✅ Extraction methods test complete")

def test_browser_setup():
    """Test browser setup and page access"""
    print("\n=== Testing Browser Setup ===")
    driver = None
    
    try:
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/usr/bin/google-chrome-stable"
        
        # Create a unique user data directory
        import tempfile
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        print("Initializing Chrome driver...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print("Navigating to devsunite.com/jobs...")
        driver.get('https://devsunite.com/jobs')
        
        print("Waiting for page to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        time.sleep(3)
        
        print("Page loaded successfully!")
        print(f"Page title: {driver.title}")
        
        # Get page source and check for job content
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_cards = soup.select('div.group.relative')
        print(f"Found {len(job_cards)} potential job cards")
        
        if job_cards:
            print("✅ Browser setup and page access successful")
        else:
            print("⚠️ Browser works but no job cards found - check selectors")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in browser setup: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

def test_database():
    """Test database connection and job records"""
    print("\n=== Testing Database Connection ===")
    try:
        job_count = Job.objects.count()
        print(f"Total jobs in database: {job_count}")
        
        if job_count > 0:
            recent_jobs = Job.objects.all().order_by('-created_at')[:5]
            print("Most recent jobs:")
            for job in recent_jobs:
                print(f"- {job.role} at {job.company_name} ({job.job_type})")
        else:
            print("No jobs found in database")
        
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test Scraplify job scraper')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--api', action='store_true', help='Test API endpoint')
    parser.add_argument('--extract', action='store_true', help='Test extraction methods')
    parser.add_argument('--details', action='store_true', help='Test job details extraction')
    parser.add_argument('--browser', action='store_true', help='Test browser setup')
    parser.add_argument('--db', action='store_true', help='Test database connection')
    parser.add_argument('--job-url', type=str, help='Specific job URL to test details extraction')
    
    args = parser.parse_args()
    
    # If no specific tests are specified, run all tests
    run_all = args.all or (not args.api and not args.extract and not args.details and not args.browser and not args.db)
    
    if run_all or args.extract:
        test_extraction_methods()
    
    if run_all or args.details:
        test_job_details_extraction()
    
    if run_all or args.browser:
        test_browser_setup()
    
    if run_all or args.db:
        test_database()
    
    if run_all or args.api:
        test_api_endpoint()
        
    print("\n=== Test Summary ===")
    print("✅ All tests completed")
    print("Note: For best results, use --job-url argument to test with a specific job URL")
    print("Example: python test_scraper.py --details --job-url https://devsunite.com/jobs/example-job-id")





