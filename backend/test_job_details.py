#!/usr/bin/env python3
"""
Test the enhanced job scraper that extracts detailed job descriptions and skills
"""
import os
import sys
import django
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

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

def test_job_details_extraction(job_url=None):
    """Test extraction of job details from individual job pages"""
    print("\n=== Testing Job Details Extraction ===")
    
    # Default test URL if none provided
    if not job_url:
        job_url = "https://devsunite.com/jobs/Lrb4x4zXLzb3fJQUxWCv"
    
    driver = None
    try:
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Create a driver instance
        print("Creating Chrome driver...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Create viewset instance to access the job details extraction method
        viewset = JobViewSet()
        
        # Test URL
        print(f"Testing job details extraction from: {job_url}")
        
        # Get job details using the _get_full_description_selenium method
        print("Fetching job details...")
        job_details = viewset._get_full_description_selenium(job_url, driver)
        
        if job_details:
            print("✅ Successfully extracted job details:")
            
            # Check if we got a full description
            if 'full_description' in job_details:
                desc_length = len(job_details['full_description'])
                print(f"Description: {desc_length} characters")
                if desc_length > 0:
                    print(f"Sample: {job_details['full_description'][:100]}...")
                else:
                    print("⚠️ Empty description")
            else:
                print("⚠️ No full description found")
                
            # Check if we got skills
            if 'skills_required' in job_details and job_details['skills_required']:
                skills_count = len(job_details['skills_required'])
                print(f"Skills: {skills_count} found")
                if skills_count > 0:
                    print(f"Skills list: {', '.join(job_details['skills_required'][:10])}")
                else:
                    print("⚠️ Empty skills list")
            else:
                print("⚠️ No skills found")
                
            # Print all extracted fields
            print("\nAll extracted fields:")
            for key, value in job_details.items():
                if isinstance(value, list):
                    print(f"- {key}: {', '.join(value[:5])}...")
                elif isinstance(value, str) and len(value) > 100:
                    print(f"- {key}: {value[:100]}...")
                else:
                    print(f"- {key}: {value}")
                    
            return True
        else:
            print("⚠️ No job details extracted")
            return False
            
    except Exception as e:
        print(f"❌ Error testing job details extraction: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test job details extraction')
    parser.add_argument('--job-url', type=str, help='URL of the job page to test')
    
    args = parser.parse_args()
    test_job_details_extraction(args.job_url)
