import logging
import re
import time
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from .models import Job
from .serializers import JobSerializer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DevSuniteScraperService:
    """
    Professional DevSunite scraper service integrated into Django backend
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.base_url = "https://devsunite.com"
        self.jobs_url = f"{self.base_url}/jobs"
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with optimized settings"""
        try:
            chrome_options = Options()
            # Headless and optimized for codespace
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Anti-detection measures
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Performance optimizations
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("✅ Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebDriver: {e}")
            return False
    
    def close_driver(self):
        """Safely close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔒 WebDriver closed successfully")
            except Exception as e:
                logger.error(f"⚠️ Error closing WebDriver: {e}")
    
    def extract_job_cards(self, max_pages: int = 5) -> List[Dict]:
        """Extract job information from multiple pages using proven working logic"""
        try:
            logger.info(f"🔍 Loading DevSunite jobs page: {self.jobs_url}")
            self.driver.get(self.jobs_url)
            
            # Wait for React to render
            time.sleep(5)
            
            all_jobs = []
            page_num = 1
            previous_job_count = 0
            no_change_count = 0
            
            while page_num <= max_pages:
                logger.info(f"📄 Scraping page {page_num} of {max_pages}")
                
                # Get current page source and parse
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Find job cards - PROVEN WORKING SELECTORS
                job_cards = soup.find_all('div', class_=lambda x: x and 'rounded-lg' in x and 'border-neutral-800' in x and 'bg-black' in x)
                
                if not job_cards:
                    logger.info(f"🛑 No job cards found on page {page_num}, stopping pagination")
                    break
                
                logger.info(f"📋 Found {len(job_cards)} job cards on page {page_num}")
                
                # Check if job count hasn't increased (for infinite scroll detection)
                if len(job_cards) == previous_job_count:
                    no_change_count += 1
                    if no_change_count >= 2:
                        logger.info(f"🛑 Job count unchanged for {no_change_count} attempts, stopping pagination")
                        break
                else:
                    no_change_count = 0
                
                previous_job_count = len(job_cards)
                
                # Extract jobs from current page (only new ones for infinite scroll)
                start_index = len(all_jobs) if page_num > 1 else 0
                page_jobs = []
                
                for i, card in enumerate(job_cards[start_index:], start_index + 1):
                    try:
                        job_info = self.parse_job_card(card)
                        if job_info:
                            # Check for duplicates
                            is_duplicate = any(
                                existing_job['title'] == job_info['title'] and 
                                existing_job['company'] == job_info['company']
                                for existing_job in all_jobs
                            )
                            
                            if not is_duplicate:
                                logger.info(f"✅ Page {page_num} - Job {i}: {job_info['title']} at {job_info['company']}")
                                page_jobs.append(job_info)
                            else:
                                logger.info(f"⚠️  Skipping duplicate: {job_info['title']} at {job_info['company']}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error parsing job card {i} on page {page_num}: {e}")
                        continue
                
                all_jobs.extend(page_jobs)
                logger.info(f"📊 Page {page_num} added {len(page_jobs)} new jobs (Total: {len(all_jobs)})")
                
                # If no new jobs were added, we might have reached the end
                if len(page_jobs) == 0:
                    logger.info(f"🏁 No new jobs found on page {page_num}, stopping pagination")
                    break
                
                # Try to navigate to next page
                if page_num < max_pages:
                    logger.info(f"🔄 Attempting to navigate to page {page_num + 1}")
                    if self.navigate_to_next_page():
                        page_num += 1
                        time.sleep(3)  # Wait for new page to load
                        logger.info(f"✅ Successfully navigated to page {page_num}")
                    else:
                        logger.info(f"🏁 No more pages available after page {page_num}")
                        break
                else:
                    logger.info(f"🏁 Reached maximum pages limit ({max_pages})")
                    break
            
            logger.info(f"🎯 Total unique jobs extracted from {page_num} pages: {len(all_jobs)}")
            
            # Final summary
            if len(all_jobs) <= 15:
                logger.info("ℹ️  Small job count suggests DevSunite might be a single-page site or has limited jobs")
            elif len(all_jobs) > 20:
                logger.info("✅ Large job count suggests successful multi-page scraping")
            
            return all_jobs
            
        except Exception as e:
            logger.error(f"❌ Error extracting job cards: {e}")
            return []
    
    def navigate_to_next_page(self) -> bool:
        """Navigate to the next page using DevSunite-specific pagination"""
        try:
            # Get current job cards to compare later
            current_job_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="rounded-lg"][class*="border-neutral-800"][class*="bg-black"]')
            initial_job_count = len(current_job_cards)
            logger.info(f"🔍 Initial job count: {initial_job_count}")
            
            # Get the first job title to track changes
            initial_first_job_title = ""
            try:
                first_job_link = current_job_cards[0].find_element(By.CSS_SELECTOR, 'a[data-testid="job-title"]')
                initial_first_job_title = first_job_link.text.strip()
                logger.info(f"🔍 Initial first job: {initial_first_job_title}")
            except:
                pass
            
            # Method 1: Look for next page number button (DevSunite specific)
            logger.info("🔄 Looking for next page number button...")
            try:
                # First, determine current page
                current_page = 1
                page_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-[#2CEE91]')]")
                if page_buttons:
                    current_page_text = page_buttons[0].text.strip()
                    if current_page_text.isdigit():
                        current_page = int(current_page_text)
                        logger.info(f"📄 Currently on page {current_page}")
                
                # Look for next page button
                next_page = current_page + 1
                next_page_button = self.driver.find_elements(By.XPATH, f"//button[text()='{next_page}']")
                
                if next_page_button and next_page_button[0].is_enabled():
                    logger.info(f"🔄 Clicking page {next_page} button")
                    self.driver.execute_script("arguments[0].click();", next_page_button[0])
                    
                    # Wait for content to change with multiple checks
                    for wait_attempt in range(10):  # Wait up to 10 seconds
                        time.sleep(1)
                        
                        # Check if first job title changed
                        try:
                            new_job_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="rounded-lg"][class*="border-neutral-800"][class*="bg-black"]')
                            if new_job_cards:
                                first_job_link = new_job_cards[0].find_element(By.CSS_SELECTOR, 'a[data-testid="job-title"]')
                                new_first_job_title = first_job_link.text.strip()
                                
                                if new_first_job_title != initial_first_job_title:
                                    logger.info(f"✅ Successfully navigated to page {next_page}")
                                    logger.info(f"🔄 First job changed: '{initial_first_job_title}' → '{new_first_job_title}'")
                                    return True
                        except:
                            pass
                    
                    logger.info(f"⚠️ Page {next_page} clicked but content didn't change - might be same jobs or only one page of jobs")
                    return True  # Still return True since we clicked successfully
                else:
                    logger.info(f"❌ Page {next_page} button not found or not enabled")
                    
            except Exception as e:
                logger.info(f"⚠️ Error with page number navigation: {e}")
            
            # Method 2: Try right arrow/chevron navigation as fallback
            logger.info("🔄 Looking for right arrow/chevron buttons...")
            try:
                right_arrow_selectors = [
                    "button[class*='chevron-right']",
                    "button svg[class*='chevron-right']",
                    "button:has(svg[class*='chevron-right'])",
                    "//button[contains(@class, 'inline-flex')]//svg[contains(@class, 'lucide-chevron-right')]/.."
                ]
                
                for selector in right_arrow_selectors:
                    try:
                        if selector.startswith("//"):
                            right_arrow_buttons = self.driver.find_elements(By.XPATH, selector)
                        else:
                            right_arrow_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for right_arrow_btn in right_arrow_buttons:
                            if right_arrow_btn.is_enabled() and right_arrow_btn.is_displayed():
                                classes = right_arrow_btn.get_attribute("class")
                                if "disabled" not in classes.lower():
                                    logger.info("🔄 Clicking right arrow button")
                                    self.driver.execute_script("arguments[0].click();", right_arrow_btn)
                                    
                                    # Wait for content change
                                    for wait_attempt in range(8):
                                        time.sleep(1)
                                        new_job_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="rounded-lg"][class*="border-neutral-800"][class*="bg-black"]')
                                        
                                        if new_job_cards:
                                            try:
                                                first_job_link = new_job_cards[0].find_element(By.CSS_SELECTOR, 'a[data-testid="job-title"]')
                                                new_first_job_title = first_job_link.text.strip()
                                                
                                                if new_first_job_title != initial_first_job_title:
                                                    logger.info(f"✅ Right arrow worked! Content changed")
                                                    return True
                                            except:
                                                pass
                                    
                                    logger.info("⚠️ Right arrow clicked but no content change detected")
                                    return True
                    except:
                        continue
                        
            except Exception as e:
                logger.info(f"⚠️ Could not find right arrow button: {e}")
            
            # Method 3: Check if this is all the jobs available
            logger.info("🔍 Checking if all jobs are already loaded...")
            try:
                # Look for end-of-results indicators
                end_indicators = [
                    "No more jobs",
                    "End of results", 
                    "That's all folks",
                    "© 2025 DevsUnite"  # Footer indicates end of content
                ]
                
                page_text = self.driver.page_source.lower()
                for indicator in end_indicators:
                    if indicator.lower() in page_text:
                        logger.info(f"ℹ️  Found 'end of results' indicator - all jobs likely loaded")
                        return False
                        
                # If we only have 12 jobs, this might be all DevSunite has
                if initial_job_count <= 12:
                    logger.info(f"ℹ️  Small job count ({initial_job_count}) suggests DevSunite might be a single-page site or has limited jobs")
                    
            except Exception as e:
                logger.info(f"⚠️ Error checking for end indicators: {e}")
            
            logger.info("❌ No pagination method worked or all jobs already loaded")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in navigate_to_next_page: {e}")
            return False
    
    def parse_job_card(self, card) -> Optional[Dict]:
        """Parse individual job card element using proven working logic"""
        try:
            job_info = {
                'title': 'Unknown Position',
                'company': 'Unknown Company',
                'location': 'Remote',
                'experience': 'Not specified',
                'job_type': 'Full-time',
                'compensation': '',
                'view_details_url': '',
                'apply_url': '',
                'short_description': ''
            }
            
            # Extract company name - PROVEN WORKING SELECTOR
            company_elem = card.find('p', class_=lambda x: x and 'text-xs' in x and 'font-medium' in x and 'text-neutral-500' in x and 'uppercase' in x)
            if company_elem:
                job_info['company'] = company_elem.get_text(strip=True)
            
            # Extract job title - PROVEN WORKING SELECTOR
            title_elem = card.find('div', class_=lambda x: x and 'tracking-tight' in x and 'font-semibold' in x)
            if title_elem:
                job_info['title'] = title_elem.get_text(strip=True)
            
            # Extract location and experience - PROVEN WORKING LOGIC
            location_spans = card.find_all('span', class_=lambda x: x and 'font-medium' in x)
            for span in location_spans:
                text = span.get_text(strip=True)
                # Look for location indicators
                if any(loc in text.lower() for loc in ['bangalore', 'mumbai', 'delhi', 'pune', 'hyderabad', 'chennai', 'remote', 'india', 'usa', 'uk', 'gurgaon', 'gurugram', 'noida']):
                    job_info['location'] = text
                # Look for experience indicators
                elif 'year' in text.lower() or re.match(r'\d+\s*years?', text):
                    job_info['experience'] = text
            
            # Extract job type - PROVEN WORKING SELECTOR
            job_type_elem = card.find('div', class_=lambda x: x and 'inline-flex' in x and 'rounded-full' in x and 'border' in x)
            if job_type_elem:
                job_type_text = job_type_elem.get_text(strip=True).upper()
                if 'FULL TIME' in job_type_text:
                    job_info['job_type'] = 'FULL_TIME'
                elif 'PART TIME' in job_type_text:
                    job_info['job_type'] = 'PART_TIME'
                elif 'INTERNSHIP' in job_type_text:
                    job_info['job_type'] = 'INTERNSHIP'
                elif 'CONTRACT' in job_type_text:
                    job_info['job_type'] = 'CONTRACT'
                else:
                    job_info['job_type'] = job_type_text
            
            # Extract compensation - PROVEN WORKING SELECTOR
            comp_section = card.find('div', class_=lambda x: x and 'border-t' in x and 'border-neutral-800' in x)
            if comp_section:
                comp_span = comp_section.find('span', class_=lambda x: x and 'font-semibold' in x and 'text-neutral-200' in x)
                if comp_span:
                    job_info['compensation'] = comp_span.get_text(strip=True)
            
            # Extract view details URL - PROVEN WORKING SELECTOR
            view_details_link = card.find('a', href=lambda x: x and '/jobs/' in x and len(x.split('/')[-1]) > 10)
            if view_details_link:
                href = view_details_link.get('href')
                if href.startswith('/'):
                    job_info['view_details_url'] = self.base_url + href
                else:
                    job_info['view_details_url'] = href
            
            # Extract apply URL (external link)
            apply_links = card.find_all('a', href=True)
            for link in apply_links:
                href = link.get('href')
                text = link.get_text(strip=True).lower()
                if 'apply' in text and not href.startswith('/jobs/'):
                    job_info['apply_url'] = href
                    break
            
            # Extract short description
            desc_elem = card.find('p', class_=lambda x: x and 'text-sm' in x)
            if desc_elem:
                job_info['short_description'] = desc_elem.get_text(strip=True)
            
            # Only return if we have essential information
            if job_info['title'] != 'Unknown Position' and job_info['company'] != 'Unknown Company':
                return job_info
            else:
                return None
            
        except Exception as e:
            logger.error(f"❌ Error parsing job card: {e}")
            return None
    
    def clean_experience(self, experience_text: str) -> str:
        """Clean and normalize experience text"""
        if not experience_text:
            return "Not specified"
        
        # Extract years from text
        years_match = re.search(r'(\d+).*?years?', experience_text.lower())
        if years_match:
            return f"{years_match.group(1)} years"
        
        # Check for entry level indicators
        entry_indicators = ['entry', 'fresher', 'graduate', '0 year', 'no experience']
        if any(indicator in experience_text.lower() for indicator in entry_indicators):
            return "0 years"
        
        return experience_text.strip()
    
    def scrape_job_details(self, job_url: str) -> Dict:
        """Enhanced job details scraping with better skills extraction"""
        try:
            logger.info(f"🔍 Scraping job details from: {job_url}")
            self.driver.get(job_url)
            time.sleep(3)  # Wait for content to load
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract full job description with multiple fallback strategies
            full_description = ""
            
            # Strategy 1: Look for DevSunite-specific content containers
            devsunite_selectors = [
                'div[class*="job-description"]',
                'div[class*="description"]',
                'div[class*="content"]',
                'section[class*="job"]',
                'article',
                '.prose',  # Common for rich text content
                '[data-testid*="description"]',
                '[data-testid*="content"]'
            ]
            
            for selector in devsunite_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    # Remove unwanted elements
                    for unwanted in desc_elem.find_all(['script', 'style', 'nav', 'header', 'footer']):
                        unwanted.decompose()
                    
                    full_description = desc_elem.get_text(separator='\n', strip=True)
                    if len(full_description) > 100:  # Ensure we got substantial content
                        logger.info(f"📄 Found description using selector: {selector}")
                        break
            
            # Strategy 2: If no specific description found, get main content
            if not full_description or len(full_description) < 100:
                main_selectors = ['main', '[role="main"]', '#main', '.main-content', 'body']
                
                for selector in main_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        # Remove navigation, header, footer, and sidebar elements
                        for elem in main_content.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style']):
                            elem.decompose()
                        
                        # Also remove elements that are likely navigation or UI
                        for elem in main_content.find_all(class_=re.compile(r'nav|menu|sidebar|footer|header', re.I)):
                            elem.decompose()
                        
                        content = main_content.get_text(separator='\n', strip=True)
                        if len(content) > len(full_description):
                            full_description = content
                            logger.info(f"📄 Found description using main selector: {selector}")
                            break
            
            # Strategy 3: Extract from page title and meta if still no content
            if not full_description or len(full_description) < 50:
                title = soup.find('title')
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                
                title_text = title.get_text(strip=True) if title else ""
                meta_text = meta_desc.get('content', '') if meta_desc else ""
                
                full_description = f"{title_text}\n{meta_text}".strip()
                logger.info("📄 Using title and meta description as fallback")
            
            # Clean up the description
            if full_description:
                # Remove excessive whitespace and normalize
                full_description = re.sub(r'\n\s*\n', '\n\n', full_description)
                full_description = re.sub(r'[ \t]+', ' ', full_description)
                full_description = full_description.strip()
            
            # Extract skills from structured "Required Skills" sections on the job page
            skills = self._extract_required_skills_from_page(soup)
            
            logger.info(f"✅ Extracted job details: {len(full_description)} chars, {len(skills)} skills")
            
            return {
                'full_description': full_description,
                'skills_required': skills
            }
            
        except Exception as e:
            logger.error(f"❌ Error scraping job details from {job_url}: {e}")
            return {
                'full_description': "",
                'skills_required': []
            }
    
    def _extract_structured_skills(self, soup) -> List[str]:
        """Extract skills from structured page elements"""
        skills = set()
        
        # Look for skill tags or badges
        skill_selectors = [
            '.skill', '.tag', '.badge', '.chip',
            '[class*="skill"]', '[class*="tag"]', '[class*="badge"]',
            '.technology', '.tech', '[class*="tech"]'
        ]
        
        for selector in skill_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if self._is_valid_skill(text) and len(text) < 30:
                    skills.add(text)
        
        # Look for structured lists that might contain skills
        lists = soup.find_all(['ul', 'ol'])
        for list_elem in lists:
            # Check if this might be a skills list based on context
            list_context = ""
            prev_elem = list_elem.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'])
            if prev_elem:
                list_context = prev_elem.get_text(strip=True).lower()
            
            if any(keyword in list_context for keyword in ['skill', 'requirement', 'technology', 'tool', 'experience']):
                items = list_elem.find_all('li')
                for item in items[:10]:  # Limit to prevent noise
                    text = item.get_text(strip=True)
                    if self._is_valid_skill(text) and len(text) < 50:
                        skills.add(text)
        
        return list(skills)
    
    def _extract_required_skills_from_page(self, soup) -> List[str]:
        """Extract skills specifically from DevSunite's 'Required Skills' sections"""
        skills = set()
        
        # DevSunite-specific structure: Look for the exact HTML pattern
        # <div class="bg-gradient-to-br from-zinc-900/90 to-zinc-950/90 ...">
        #   <h2 class="text-xl font-bold text-white mb-6 ...">Required Skills</h2>
        #   <div class="flex flex-wrap gap-3">
        #     <span class="px-4 py-2 bg-[#2CEE91]/10 ...">Python</span>
        #     <span class="px-4 py-2 bg-[#2CEE91]/10 ...">LLMs</span>
        
        logger.info("🔍 Searching for DevSunite-specific Required Skills section...")
        
        # Method 1: Target the exact DevSunite skills container
        skills_containers = soup.find_all('div', class_=lambda x: x and 'bg-gradient-to-br' in x and 'from-zinc-900' in x)
        
        for container in skills_containers:
            # Check if this container has "Required Skills" heading
            heading = container.find('h2', string=re.compile(r'required\s+skills', re.I))
            if not heading:
                heading = container.find(['h1', 'h2', 'h3', 'h4'], string=re.compile(r'required\s+skills|skills\s+required|technical\s+skills|key\s+skills', re.I))
            
            if heading:
                logger.info(f"✅ Found DevSunite skills container with heading: {heading.get_text(strip=True)}")
                
                # Look for skill spans with the specific styling
                skill_spans = container.find_all('span', class_=lambda x: x and 'px-4' in x and 'py-2' in x and 'bg-[#2CEE91]' in x)
                
                for span in skill_spans:
                    skill_text = span.get_text(strip=True)
                    if skill_text and len(skill_text) < 50:
                        skills.add(skill_text)
                        logger.info(f"🎯 Found skill: {skill_text}")
                
                # Also check for any other spans in the flex container
                flex_container = container.find('div', class_=lambda x: x and 'flex' in x and 'flex-wrap' in x)
                if flex_container:
                    all_spans = flex_container.find_all('span')
                    for span in all_spans:
                        skill_text = span.get_text(strip=True)
                        if skill_text and len(skill_text) < 50 and self._looks_like_skill(skill_text):
                            skills.add(skill_text)
        
        # Method 2: Look for any section with "Required Skills" heading (fallback)
        if not skills:
            logger.info("🔍 Fallback: Looking for any Required Skills headings...")
            
            skills_headings = []
            for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                headings = soup.find_all(heading_tag)
                for heading in headings:
                    heading_text = heading.get_text(strip=True).lower()
                    if any(keyword in heading_text for keyword in [
                        'required skills', 'skills required', 'technical skills', 
                        'key skills', 'core skills', 'essential skills',
                        'must have skills', 'skills needed', 'technologies',
                        'tech stack', 'technology stack'
                    ]):
                        skills_headings.append(heading)
                        logger.info(f"🔍 Found skills section: '{heading.get_text(strip=True)}'")
            
            # Extract skills from sections following these headings
            for heading in skills_headings:
                skills_found_in_section = self._extract_skills_from_section(heading)
                skills.update(skills_found_in_section)
                logger.info(f"📋 Extracted {len(skills_found_in_section)} skills from section: {heading.get_text(strip=True)}")
        
        # Method 3: Look for skills in any structured elements (badges, tags, etc.)
        if not skills:
            logger.info("🔍 Fallback: Looking for structured skill elements...")
            structured_skills = self._extract_skills_from_structured_elements(soup)
            skills.update(structured_skills)
        
        # Method 4: Look for skills in data attributes
        attribute_skills = self._extract_skills_from_attributes(soup)
        skills.update(attribute_skills)
        
        # Clean and validate all found skills
        cleaned_skills = []
        for skill in skills:
            cleaned = self._clean_skill(skill)
            if cleaned and self._is_valid_skill(cleaned) and len(cleaned) >= 2:
                # Split concatenated skills
                split_skills = self._split_concatenated_skills(cleaned)
                for split_skill in split_skills:
                    if split_skill and len(split_skill) >= 2:
                        cleaned_skills.append(split_skill)
        
        # Remove duplicates and filter out concatenated versions when we have individual components
        final_skills = self._deduplicate_skills(cleaned_skills)
        final_skills = self._filter_concatenated_duplicates(final_skills)
        
        logger.info(f"🎯 Final skills extracted from DevSunite page: {len(final_skills)}")
        return final_skills[:20]  # Limit to top 20 skills
    
    def _extract_skills_from_section(self, heading) -> List[str]:
        """Extract skills from content following a skills heading"""
        skills = set()
        
        # Get the parent container of the heading
        section_container = heading.parent
        if not section_container:
            return list(skills)
        
        # Look for lists immediately following the heading
        next_elements = []
        
        # Method 1: Look for next siblings
        current = heading
        for _ in range(5):  # Check next 5 elements
            current = current.find_next_sibling()
            if current:
                next_elements.append(current)
            else:
                break
        
        # Method 2: Look within the parent container
        container_lists = section_container.find_all(['ul', 'ol'], limit=3)
        next_elements.extend(container_lists)
        
        # Method 3: Look for divs with skill-like content
        skill_divs = section_container.find_all('div', class_=re.compile(r'skill|tag|badge|chip', re.I), limit=10)
        next_elements.extend(skill_divs)
        
        # Extract skills from found elements
        for element in next_elements:
            if element.name in ['ul', 'ol']:
                # Extract from list items
                list_items = element.find_all('li')
                for item in list_items:
                    skill_text = item.get_text(strip=True)
                    # Split concatenated skills by common patterns
                    individual_skills = self._split_concatenated_skills(skill_text)
                    for skill in individual_skills:
                        if skill and len(skill) < 50:  # Reasonable skill length
                            skills.add(skill)
            
            elif element.name == 'div':
                # Check if this div contains skill-like content
                div_text = element.get_text(strip=True)
                
                # Split concatenated skills
                individual_skills = self._split_concatenated_skills(div_text)
                for skill in individual_skills:
                    if len(skill) < 30 and self._looks_like_skill(skill):
                        skills.add(skill)
                
                # Also check for nested spans or other elements
                skill_elements = element.find_all(['span', 'a', 'button'], limit=20)
                for skill_elem in skill_elements:
                    skill_text = skill_elem.get_text(strip=True)
                    individual_skills = self._split_concatenated_skills(skill_text)
                    for skill in individual_skills:
                        if skill and len(skill) < 30 and self._looks_like_skill(skill):
                            skills.add(skill)
            
            elif element.name == 'p':
                # For paragraphs, try to extract comma-separated skills
                para_text = element.get_text(strip=True)
                if len(para_text) < 200:  # Not too long
                    # Split by common delimiters and handle concatenated skills
                    potential_skills = re.split(r'[,;•|]|\sand\s|\sor\s', para_text)
                    for skill in potential_skills:
                        individual_skills = self._split_concatenated_skills(skill.strip())
                        for individual_skill in individual_skills:
                            if individual_skill and len(individual_skill) < 30 and self._looks_like_skill(individual_skill):
                                skills.add(individual_skill)
        
        return list(skills)
    
    def _split_concatenated_skills(self, text: str) -> List[str]:
        """Split concatenated skills like 'Pythonllmsai/Ml' into individual skills"""
        if not text or len(text) < 3:
            return [text] if text else []
        
        text = text.strip()
        
        # If it's already a clean single skill, return it
        if len(text) < 20 and ' ' not in text and self._is_single_clean_skill(text):
            return [text]
        
        # Common patterns to split concatenated skills
        skills = []
        
        # Pattern 1: Split by common delimiters first
        if any(delim in text for delim in [',', ';', '|', '•', '/', ' and ', ' & ']):
            parts = re.split(r'[,;|•/]|\sand\s|\s&\s', text)
            for part in parts:
                part = part.strip()
                if part and len(part) >= 2:
                    # Don't recursively split if it's already reasonable
                    if len(part) < 25 and self._looks_like_skill(part):
                        skills.append(part)
            return skills if skills else [text]
        
        # Pattern 2: Split by known technology names (exact matches) - Enhanced list
        known_techs = [
            # AI/ML Terms
            'AI/ML', 'AI', 'ML', 'Machine Learning', 'Deep Learning', 'LLMs', 'LLM',
            'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy',
            
            # Programming Languages
            'JavaScript', 'TypeScript', 'Python', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 
            'Go', 'Rust', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB',
            
            # Web Technologies
            'React.js', 'React', 'Angular', 'Vue.js', 'Vue', 'Next.js', 'Nuxt.js',
            'Node.js', 'Express.js', 'Express', 'Svelte', 'jQuery',
            'HTML5', 'HTML', 'CSS3', 'CSS', 'SASS', 'SCSS', 'Bootstrap', 'Tailwind',
            'Material-UI', 'Ant Design', 'Chakra UI',
            
            # Backend Frameworks
            'Django', 'Flask', 'FastAPI', 'Spring Boot', 'Spring', 'Laravel', 
            'Ruby on Rails', 'ASP.NET', 'Symfony', 'Koa.js',
            
            # Databases
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle',
            'SQL Server', 'DynamoDB', 'Cassandra', 'Elasticsearch', 'Neo4j',
            
            # Cloud & DevOps
            'AWS', 'Azure', 'GCP', 'Google Cloud', 'Docker', 'Kubernetes', 'Jenkins',
            'GitLab CI', 'GitHub Actions', 'Terraform', 'Ansible', 'Vagrant',
            
            # Version Control & Tools
            'Git', 'GitHub', 'GitLab', 'Bitbucket', 'JIRA', 'Confluence',
            'VS Code', 'IntelliJ', 'Eclipse', 'Postman', 'Swagger',
            
            # APIs & Protocols
            'GraphQL', 'REST API', 'REST', 'gRPC', 'JSON', 'XML', 'SOAP',
            
            # Testing
            'Jest', 'Mocha', 'Selenium', 'Cypress', 'JUnit', 'PyTest',
            'Unit Testing', 'Integration Testing', 'TDD', 'BDD',
            
            # Mobile
            'React Native', 'Flutter', 'iOS', 'Android', 'Xamarin', 'Ionic',
            
            # Build Tools
            'Webpack', 'Babel', 'Vite', 'Parcel', 'Rollup', 'Grunt', 'Gulp',
            
            # Methodologies
            'Agile', 'Scrum', 'Kanban', 'DevOps', 'CI/CD'
        ]
        
        # Sort by length (longest first) to match longer terms first
        known_techs_sorted = sorted(known_techs, key=len, reverse=True)
        
        found_skills = []
        remaining_text = text
        
        for tech in known_techs_sorted:
            # Look for exact matches (case insensitive)
            tech_lower = tech.lower()
            remaining_lower = remaining_text.lower()
            
            if tech_lower in remaining_lower:
                start_idx = remaining_lower.find(tech_lower)
                # Check if it's a word boundary match (not part of another word)  
                if start_idx != -1:
                    # For concatenated skills, be more flexible with boundaries
                    # Allow matching even if characters are adjacent (for concatenated strings)
                    is_word_start = start_idx == 0 or not remaining_text[start_idx-1].isalpha() or start_idx == 0
                    end_idx = start_idx + len(tech)
                    is_word_end = end_idx >= len(remaining_text) or not remaining_text[end_idx].isalpha() or end_idx == len(remaining_text)
                    
                    # For concatenated skills, we want to match even when letters are adjacent
                    if tech_lower in remaining_lower:
                        # Get the actual case from the original text
                        actual_match = remaining_text[start_idx:start_idx + len(tech)]
                        found_skills.append(tech)  # Use the standard capitalization
                        # Remove this match from remaining text
                        remaining_text = remaining_text[:start_idx] + remaining_text[end_idx:]
                        remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
                        break  # Important: break to avoid multiple matches of the same tech
        
        # Handle remaining text
        if remaining_text and len(remaining_text) >= 2:
            # Clean up remaining text
            remaining_text = re.sub(r'[^\w\s.-]', '', remaining_text).strip()
            if remaining_text and self._looks_like_skill(remaining_text):
                found_skills.append(remaining_text)
        
        # If we found skills through pattern matching, return them
        if found_skills:
            return found_skills
        
        # If no patterns matched and it's not too long, return the original
        if len(text) <= 30:
            return [text]
        
        # For very long concatenated strings, try camelCase splitting as last resort
        if len(text) > 8:  # Reduced threshold to catch more concatenated skills
            # Enhanced camelCase splitting for cases like "Reacthtml", "Nodejsgit"
            parts = re.findall(r'[A-Z][a-z]*\.?[a-z]*|[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', text)
            if len(parts) > 1:
                valid_parts = []
                
                # Try to reconstruct meaningful skills from parts
                i = 0
                while i < len(parts):
                    current_part = parts[i]
                    
                    # Check if current part combined with next part makes a known skill
                    if i + 1 < len(parts):
                        combined = current_part + parts[i + 1]
                        if any(tech.lower() == combined.lower() for tech in known_techs_sorted):
                            valid_parts.append(combined)
                            i += 2
                            continue
                        
                        # Also try with dots (like Node.js)
                        combined_with_dot = current_part + '.' + parts[i + 1]
                        if any(tech.lower() == combined_with_dot.lower() for tech in known_techs_sorted):
                            valid_parts.append(combined_with_dot)
                            i += 2
                            continue
                    
                    # Check if current part is valid on its own
                    if len(current_part) >= 2 and (
                        self._looks_like_skill(current_part) or 
                        any(tech.lower() == current_part.lower() for tech in known_techs_sorted)
                    ):
                        valid_parts.append(current_part)
                    
                    i += 1
                
                if len(valid_parts) >= 2:
                    return valid_parts
            
            # Alternative approach: try splitting known concatenations
            # Look for known patterns like "reacthtml", "nodejsgit", etc.
            text_lower = text.lower()
            for tech in known_techs_sorted:
                tech_lower = tech.lower()
                if tech_lower in text_lower and len(tech_lower) < len(text_lower):
                    # Found a technology in the text, try to split around it
                    before_tech = text_lower[:text_lower.find(tech_lower)]
                    after_tech = text_lower[text_lower.find(tech_lower) + len(tech_lower):]
                    
                    result_parts = []
                    
                    # Add the main technology
                    result_parts.append(tech)
                    
                    # Check if before/after parts are also technologies
                    if before_tech:
                        for other_tech in known_techs_sorted:
                            if other_tech.lower() == before_tech:
                                result_parts.insert(0, other_tech)
                                break
                    
                    if after_tech:
                        for other_tech in known_techs_sorted:
                            if other_tech.lower() == after_tech:
                                result_parts.append(other_tech)
                                break
                    
                    if len(result_parts) >= 2:
                        return result_parts
        
        return [text]
    
    def _is_single_clean_skill(self, text: str) -> bool:
        """Check if text is already a clean single skill"""
        if not text or len(text) < 2:
            return False
        
        # Common clean skills
        clean_skills = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node.js', 'express', 'django', 'flask', 'spring', 'html', 'css',
            'postgresql', 'mysql', 'mongodb', 'redis', 'git', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'graphql', 'rest', 'api', 'json', 'xml',
            'bootstrap', 'tailwind', 'sass', 'scss', 'webpack', 'babel', 'junit',
            'jest', 'mocha', 'cypress', 'selenium', 'jenkins', 'gitlab', 'github'
        ]
        
        return text.lower() in clean_skills or (len(text) <= 15 and not any(char.isdigit() for char in text))
    
    def _extract_skills_from_structured_elements(self, soup) -> List[str]:
        """Extract skills from structured page elements like tags, badges, chips"""
        skills = set()
        
        # Look for elements that typically contain skills
        skill_element_selectors = [
            # Class-based selectors for common skill UI elements
            '.skill', '.tag', '.badge', '.chip', '.pill',
            '[class*="skill"]', '[class*="tag"]', '[class*="badge"]',
            '[class*="chip"]', '[class*="pill"]',
            '.technology', '.tech', '[class*="tech"]',
            '.requirement', '[class*="requirement"]',
            # Data attributes
            '[data-skill]', '[data-tag]', '[data-technology]',
            # Specific to job sites
            '.job-skill', '.job-tag', '.job-requirement',
            '[class*="job-skill"]', '[class*="job-tag"]'
        ]
        
        for selector in skill_element_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    # Get text content
                    text = elem.get_text(strip=True)
                    if text and len(text) < 50 and self._looks_like_skill(text):
                        skills.add(text)
                    
                    # Also check data attributes
                    for attr in ['data-skill', 'data-tag', 'data-technology', 'title', 'alt']:
                        attr_value = elem.get(attr)
                        if attr_value and len(attr_value) < 50 and self._looks_like_skill(attr_value):
                            skills.add(attr_value)
            except Exception as e:
                continue
        
        return list(skills)
    
    def _extract_skills_from_attributes(self, soup) -> List[str]:
        """Extract skills from data attributes or other element attributes"""
        skills = set()
        
        # Look for elements with skill-related data attributes
        attribute_selectors = [
            '[data-skill]',
            '[data-skills]', 
            '[data-tag]',
            '[data-tags]',
            '[data-technology]',
            '[data-technologies]',
            '[data-requirement]',
            '[data-requirements]'
        ]
        
        for selector in attribute_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    for attr in ['data-skill', 'data-skills', 'data-tag', 'data-tags', 
                                'data-technology', 'data-technologies', 'data-requirement', 'data-requirements']:
                        attr_value = elem.get(attr)
                        if attr_value:
                            # Handle comma-separated values
                            if ',' in attr_value:
                                skill_list = [s.strip() for s in attr_value.split(',')]
                                for skill in skill_list:
                                    if skill and self._looks_like_skill(skill):
                                        skills.add(skill)
                            else:
                                if self._looks_like_skill(attr_value):
                                    skills.add(attr_value)
            except Exception as e:
                continue
        
        return list(skills)
    
    def _looks_like_skill(self, text: str) -> bool:
        """Quick check if text looks like a technical skill"""
        if not text or len(text.strip()) < 2:
            return False
        
        text = text.strip().lower()
        
        # Too long or too short
        if len(text) > 50 or len(text) < 2:
            return False
        
        # Common technical terms that indicate skills
        tech_indicators = [
            'python', 'java', 'javascript', 'react', 'node', 'sql', 'html', 'css',
            'aws', 'docker', 'kubernetes', 'git', 'api', 'rest', 'graphql',
            'mongodb', 'postgresql', 'mysql', 'redis', 'django', 'flask',
            'angular', 'vue', 'typescript', 'go', 'rust', 'swift', 'kotlin',
            'machine learning', 'ai', 'data science', 'devops', 'ci/cd',
            'agile', 'scrum', 'jenkins', 'terraform', 'ansible'
        ]
        
        # If it contains common tech terms, likely a skill
        if any(indicator in text for indicator in tech_indicators):
            return True
        
        # If it's short and doesn't contain common non-skill words, might be a skill
        non_skill_words = [
            'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'of',
            'is', 'are', 'be', 'have', 'has', 'will', 'can', 'must', 'should',
            'years', 'experience', 'knowledge', 'skills', 'ability', 'bachelor',
            'degree', 'certification', 'location', 'salary', 'remote', 'job',
            'position', 'role', 'company', 'team', 'work', 'candidate'
        ]
        
        words = text.split()
        if len(words) <= 3:  # Short phrases are more likely to be skills
            non_skill_count = sum(1 for word in words if word in non_skill_words)
            if non_skill_count == 0:  # No common non-skill words
                return True
        
        return False
    
    def extract_skills(self, soup, description_text: str) -> List[str]:
        """Enhanced skills extraction from job description with comprehensive patterns"""
        skills = set()  # Use set to avoid duplicates
        
        # 1. Look for structured skills sections
        skills_keywords = [
            'skills', 'requirements', 'technologies', 'qualifications', 'must have',
            'technical skills', 'key skills', 'required skills', 'core skills',
            'technology stack', 'tech stack', 'tools', 'experience with'
        ]
        
        for keyword in skills_keywords:
            # Find sections with skills-related headings
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'], 
                                   string=re.compile(keyword, re.I))
            
            for heading in headings:
                # Get the next siblings that contain skills
                current = heading.parent
                if current:
                    # Look for lists after the heading
                    next_elements = current.find_next_siblings(['ul', 'ol', 'div', 'p'], limit=3)
                    for element in next_elements:
                        skill_items = element.find_all(['li', 'span'])
                        for item in skill_items:
                            skill_text = item.get_text(strip=True)
                            if self._is_valid_skill(skill_text):
                                skills.add(skill_text)
        
        # 2. Enhanced tech skills pattern matching with more comprehensive coverage
        tech_patterns = {
            # Programming Languages
            'languages': r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|PHP|Ruby|Go|Rust|Kotlin|Swift|Scala|R|MATLAB|Perl|Shell|Bash)\b',
            
            # Web Technologies
            'web_frontend': r'\b(React|Angular|Vue\.js|Next\.js|Nuxt\.js|Svelte|HTML5?|CSS3?|SASS|SCSS|Less|Bootstrap|Tailwind|Material-UI|Ant Design)\b',
            'web_backend': r'\b(Node\.js|Express\.js|Django|Flask|FastAPI|Spring|Laravel|Ruby on Rails|ASP\.NET|Symfony|Koa\.js)\b',
            
            # Databases
            'databases': r'\b(MySQL|PostgreSQL|MongoDB|Redis|SQLite|Oracle|SQL Server|DynamoDB|Cassandra|Elasticsearch|InfluxDB|Neo4j)\b',
            
            # Cloud & DevOps
            'cloud': r'\b(AWS|Azure|GCP|Google Cloud|Docker|Kubernetes|Jenkins|GitLab CI|GitHub Actions|Terraform|Ansible|Vagrant)\b',
            'devops': r'\b(CI/CD|DevOps|Microservices|API|REST|GraphQL|gRPC|Nginx|Apache|Load Balancing)\b',
            
            # Data & AI
            'data_ai': r'\b(Machine Learning|Deep Learning|AI|Data Science|TensorFlow|PyTorch|Scikit-learn|Pandas|NumPy|Jupyter|Apache Spark|Hadoop|Kafka)\b',
            'analytics': r'\b(Power BI|Tableau|D3\.js|Chart\.js|Google Analytics|SQL|NoSQL|ETL|Data Mining|Statistics)\b',
            
            # Mobile
            'mobile': r'\b(React Native|Flutter|iOS|Android|Xamarin|Ionic|Cordova|Swift|Objective-C|Dart)\b',
            
            # Tools & Others
            'tools': r'\b(Git|GitHub|GitLab|Bitbucket|JIRA|Confluence|Slack|VS Code|IntelliJ|Eclipse|Postman|Swagger)\b',
            'testing': r'\b(Jest|Mocha|Selenium|Cypress|JUnit|PyTest|Unit Testing|Integration Testing|TDD|BDD)\b',
            
            # Methodologies
            'methodologies': r'\b(Agile|Scrum|Kanban|Waterfall|Lean|Six Sigma|ITIL|Prince2)\b'
        }
        
        for category, pattern in tech_patterns.items():
            matches = re.findall(pattern, description_text, re.IGNORECASE)
            for match in matches:
                skills.add(match)
        
        # 3. Extract skills from common patterns
        skill_patterns = [
            # "Experience with X, Y, Z"
            r'experience\s+with\s+([^.]+?)(?:\.|,|\n|$)',
            # "Knowledge of X, Y, Z"
            r'knowledge\s+of\s+([^.]+?)(?:\.|,|\n|$)',
            # "Proficient in X, Y, Z"
            r'proficient\s+in\s+([^.]+?)(?:\.|,|\n|$)',
            # "Familiar with X, Y, Z"
            r'familiar\s+with\s+([^.]+?)(?:\.|,|\n|$)',
            # "Working knowledge of X, Y, Z"
            r'working\s+knowledge\s+of\s+([^.]+?)(?:\.|,|\n|$)',
            # "Strong understanding of X, Y, Z"
            r'strong\s+understanding\s+of\s+([^.]+?)(?:\.|,|\n|$)',
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, description_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Split by common delimiters
                skill_list = re.split(r'[,;&]|and\s+|or\s+', match)
                for skill in skill_list:
                    cleaned_skill = skill.strip()
                    if self._is_valid_skill(cleaned_skill):
                        skills.add(cleaned_skill)
        
        # 4. Extract skills from bullet points and lists
        list_items = soup.find_all(['li'])
        for item in list_items:
            text = item.get_text(strip=True)
            if self._is_valid_skill(text) and len(text) < 50:
                skills.add(text)
        
        # 5. Clean and normalize skills
        cleaned_skills = []
        for skill in skills:
            cleaned = self._clean_skill(skill)
            if cleaned and len(cleaned) >= 2:
                cleaned_skills.append(cleaned)
        
        # 6. Remove duplicates and similar skills
        final_skills = self._deduplicate_skills(cleaned_skills)
        
        # Sort by length (shorter skills first, they're usually more specific)
        final_skills.sort(key=len)
        
        logger.info(f"🔧 Extracted {len(final_skills)} skills from job description")
        return final_skills[:15]  # Limit to top 15 skills
    
    def _is_valid_skill(self, skill_text: str) -> bool:
        """Check if extracted text is a valid skill"""
        if not skill_text or len(skill_text.strip()) < 2:
            return False
        
        skill = skill_text.strip().lower()
        
        # Too long (probably a sentence, not a skill)
        if len(skill) > 100:
            return False
        
        # Contains common non-skill indicators
        invalid_indicators = [
            'years', 'degree', 'bachelor', 'master', 'phd', 'certification', 
            'salary', 'location', 'remote', 'full time', 'part time',
            'we are', 'you will', 'the ideal', 'candidate', 'applicant',
            'company', 'team', 'role', 'position', 'job', 'work',
            'email', 'phone', 'contact', 'apply', 'send', 'resume',
            'privacy policy', 'terms of service', 'cookie policy',
            'rights reserved', 'all rights', 'copyright', 'inc.',
            'made with', 'powered by', 'about us', 'contact us',
            'sign up', 'log in', 'login', 'register', 'home', 'back',
            'next', 'previous', 'more info', 'learn more', 'read more'
        ]
        
        if any(indicator in skill for indicator in invalid_indicators):
            return False
        
        # Skip single letters or numbers
        if len(skill.strip()) <= 1:
            return False
        
        # Skip common UI/navigation terms
        ui_terms = [
            'home', 'about', 'contact', 'login', 'signup', 'dashboard',
            'profile', 'settings', 'help', 'support', 'faq', 'blog',
            'careers', 'news', 'events', 'services', 'products',
            'solutions', 'pricing', 'plans', 'features', 'benefits'
        ]
        
        if skill in ui_terms:
            return False
        
        # Too many common words (probably not a skill)
        common_words = ['the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'of', 'is', 'are', 'be', 'have', 'has']
        words = skill.split()
        common_word_count = sum(1 for word in words if word in common_words)
        if len(words) > 3 and common_word_count > len(words) * 0.5:
            return False
        
        return True
    
    def _clean_skill(self, skill: str) -> str:
        """Clean and normalize skill text"""
        # Remove extra whitespace and common prefixes/suffixes
        skill = re.sub(r'\s+', ' ', skill.strip())
        
        # Remove common prefixes
        prefixes = ['strong ', 'good ', 'excellent ', 'solid ', 'proven ', 'extensive ']
        for prefix in prefixes:
            if skill.lower().startswith(prefix):
                skill = skill[len(prefix):]
        
        # Remove common suffixes
        suffixes = [' experience', ' skills', ' knowledge', ' proficiency']
        for suffix in suffixes:
            if skill.lower().endswith(suffix):
                skill = skill[:-len(suffix)]
        
        # Capitalize properly
        skill = skill.strip()
        if skill:
            # Handle special cases for tech terms
            tech_capitalizations = {
                'javascript': 'JavaScript',
                'typescript': 'TypeScript',
                'nodejs': 'Node.js',
                'reactjs': 'React.js',
                'vuejs': 'Vue.js',
                'angularjs': 'Angular.js',
                'css3': 'CSS3',
                'html5': 'HTML5',
                'mysql': 'MySQL',
                'postgresql': 'PostgreSQL',
                'mongodb': 'MongoDB',
                'graphql': 'GraphQL',
                'restful': 'RESTful',
                'api': 'API',
                'aws': 'AWS',
                'gcp': 'GCP',
                'ai': 'AI',
                'ml': 'ML',
                'ci/cd': 'CI/CD'
            }
            
            skill_lower = skill.lower()
            if skill_lower in tech_capitalizations:
                return tech_capitalizations[skill_lower]
            elif skill.isupper() and len(skill) <= 5:  # Keep acronyms uppercase
                return skill
            else:
                return skill.title()
        
        return skill
    
    def _deduplicate_skills(self, skills: List[str]) -> List[str]:
        """Remove duplicate and very similar skills"""
        if not skills:
            return []
        
        # Convert to lowercase for comparison
        seen = set()
        deduplicated = []
        
        for skill in skills:
            skill_lower = skill.lower()
            
            # Check for exact duplicates
            if skill_lower in seen:
                continue
            
            # Check for very similar skills (>= 80% similarity)
            is_similar = False
            for existing_skill in deduplicated:
                similarity = self._calculate_similarity(skill_lower, existing_skill.lower())
                if similarity >= 0.8:
                    is_similar = True
                    # Keep the shorter one (usually more specific)
                    if len(skill) < len(existing_skill):
                        deduplicated.remove(existing_skill)
                        deduplicated.append(skill)
                    break
            
            if not is_similar:
                deduplicated.append(skill)
                seen.add(skill_lower)
        
        return deduplicated
        
    def _filter_concatenated_duplicates(self, skills: List[str]) -> List[str]:
        """Remove concatenated skills when we have the individual components"""
        if not skills:
            return []
        
        # Create a list to track which skills to keep
        filtered_skills = []
        
        for skill in skills:
            skill_lower = skill.lower()
            
            # Check if this skill looks like a concatenated version
            is_concatenated = False
            
            # If the skill is long and contains multiple known technologies
            if len(skill) > 6:  # Reduced threshold to catch more cases
                # Count how many other skills from our list are contained in this skill
                contained_skills = []
                for other_skill in skills:
                    if other_skill != skill and len(other_skill) >= 3:
                        if other_skill.lower() in skill_lower:
                            contained_skills.append(other_skill)
                
                # If this skill contains 2 or more other skills, it's likely concatenated
                if len(contained_skills) >= 2:
                    is_concatenated = True
                    logger.info(f"🔄 Filtering out concatenated skill '{skill}' (contains: {contained_skills})")
                
                # Special case: if this skill contains another skill + some extra characters, it might be concatenated
                elif len(contained_skills) == 1 and len(skill) > len(contained_skills[0]) + 2:
                    # Check if the remaining part might be another skill
                    remaining_part = skill_lower.replace(contained_skills[0].lower(), '')
                    if len(remaining_part) >= 3:
                        # Check if remaining part matches any other skill
                        for other_skill in skills:
                            if other_skill != skill and other_skill.lower() == remaining_part:
                                is_concatenated = True
                                logger.info(f"🔄 Filtering out concatenated skill '{skill}' (contains: {contained_skills[0]} + {other_skill})")
                                break
            
            if not is_concatenated:
                filtered_skills.append(skill)
        
        return filtered_skills
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using simple algorithm"""
        if str1 == str2:
            return 1.0
        
        # Simple character-based similarity
        longer = str1 if len(str1) > len(str2) else str2
        shorter = str2 if len(str1) > len(str2) else str1
        
        if len(longer) == 0:
            return 1.0
        
        # Count matching characters
        matches = 0
        for char in shorter:
            if char in longer:
                matches += 1
        
        return matches / len(longer)
        """Calculate similarity between two strings using simple algorithm"""
        if str1 == str2:
            return 1.0
        
        # Simple character-based similarity
        longer = str1 if len(str1) > len(str2) else str2
        shorter = str2 if len(str1) > len(str2) else str1
        
        if len(longer) == 0:
            return 1.0
        
        # Count matching characters
        matches = 0
        for char in shorter:
            if char in longer:
                matches += 1
        
        return matches / len(longer)
    
    def parse_compensation(self, compensation_text: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Parse compensation string to extract min and max salary"""
        if not compensation_text:
            return None, None
        
        # Remove common prefixes/suffixes
        comp = compensation_text.lower().replace('lpa', '').replace('₹', '').replace(',', '').strip()
        
        # Look for range patterns: "15-25", "15 to 25", "15 - 25"
        range_patterns = [
            r'(\d+(?:\.\d+)?)\s*[-to]+\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',
            r'between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)'
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, comp)
            if match:
                try:
                    min_sal = Decimal(match.group(1)) * 100000  # Convert LPA to annual
                    max_sal = Decimal(match.group(2)) * 100000
                    return min_sal, max_sal
                except:
                    continue
        
        # Look for single value: "25 LPA", "₹25L"
        single_patterns = [
            r'(\d+(?:\.\d+)?)\s*l?pa?',
            r'₹\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*lakhs?'
        ]
        
        for pattern in single_patterns:
            match = re.search(pattern, comp)
            if match:
                try:
                    salary = Decimal(match.group(1)) * 100000
                    return salary, salary
                except:
                    continue
        
        return None, None
    
    def save_job_to_database(self, job_info: Dict, job_details: Dict) -> Tuple[Optional[Job], bool]:
        """Save job to Django database"""
        try:
            # Combine basic info with detailed info
            full_description = job_details.get('full_description', job_info.get('short_description', ''))
            skills = job_details.get('skills_required', [])
            
            # Parse compensation for min/max salary
            min_salary, max_salary = self.parse_compensation(job_info.get('compensation', ''))
            
            # Create or update job
            job_obj, created = Job.objects.update_or_create(
                external_id=f"devsunite_{job_info['company'].replace(' ', '_')}_{job_info['title'].replace(' ', '_')}",
                defaults={
                    'role': job_info['title'],
                    'company_name': job_info['company'],
                    'location': job_info['location'],
                    'job_type': job_info['job_type'],
                    'min_salary': min_salary,
                    'max_salary': max_salary,
                    'salary_currency': 'INR',  # DevSunite shows LPA (Indian Rupees)
                    'experience_required': job_info['experience'],
                    'short_description': job_info.get('short_description', full_description[:300] if full_description else ''),
                    'full_description': full_description or job_info.get('short_description', ''),
                    'skills_required': skills,
                    'compensation': job_info.get('compensation', ''),
                    'apply_link': job_info.get('apply_url') or job_info.get('view_details_url', ''),
                    'view_details_link': job_info.get('view_details_url', ''),
                    'details_scraped': bool(job_details)
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"💾 {action} job: {job_info['title']} at {job_info['company']}")
            return job_obj, created
            
        except Exception as e:
            logger.error(f"❌ Error saving job to database: {e}")
            return None, False
    
    def scrape_jobs(self, max_jobs: int = 100, max_pages: int = 10, scrape_details: bool = True) -> Dict:
        """Main scraping method with enhanced multi-page support"""
        results = {
            'success': False,
            'jobs_scraped': 0,
            'jobs_saved': 0,
            'pages_scraped': 0,
            'errors': [],
            'message': ''
        }
        
        try:
            # Initialize WebDriver
            if not self.setup_driver():
                results['errors'].append("Failed to initialize WebDriver")
                return results
            
            logger.info(f"🚀 Starting DevSunite scraping process (max_jobs={max_jobs}, max_pages={max_pages}, details={scrape_details})")
            
            # Extract jobs from multiple pages
            jobs = self.extract_job_cards(max_pages=max_pages)
            
            if not jobs:
                results['errors'].append("No jobs found on any pages")
                return results
            
            # Limit jobs to scrape if specified
            jobs_to_process = jobs[:max_jobs] if max_jobs > 0 else jobs
            logger.info(f"🎯 Successfully extracted {len(jobs_to_process)} jobs from {len(jobs)} total found")
            
            jobs_saved = 0
            
            # Process each job
            for i, job_info in enumerate(jobs_to_process, 1):
                try:
                    logger.info(f"📝 Processing job {i}/{len(jobs_to_process)}: {job_info['title']}")
                    
                    job_details = {}
                    if scrape_details and job_info.get('view_details_url'):
                        job_details = self.scrape_job_details(job_info['view_details_url'])
                    
                    # Save to database
                    job_obj, created = self.save_job_to_database(job_info, job_details)
                    if job_obj:
                        jobs_saved += 1
                    
                except Exception as e:
                    error_msg = f"Error processing job {i}: {e}"
                    logger.error(f"❌ {error_msg}")
                    results['errors'].append(error_msg)
                    continue
            
            results.update({
                'success': True,
                'jobs_scraped': len(jobs_to_process),
                'jobs_saved': jobs_saved,
                'pages_scraped': min(max_pages, len(jobs)//12 + 1),  # Estimate pages scraped
                'message': f'Successfully scraped and saved {jobs_saved}/{len(jobs_to_process)} jobs from DevSunite across multiple pages!'
            })
            
            logger.info(f"🎉 Scraping completed! Saved {jobs_saved}/{len(jobs_to_process)} jobs")
            
        except Exception as e:
            error_msg = f"Critical error during scraping: {e}"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            
        finally:
            self.close_driver()
            
        return results


class JobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Job model with integrated scraping functionality
    """
    queryset = Job.objects.all().order_by('-created_at')
    serializer_class = JobSerializer
    
    @action(detail=False, methods=['post'])
    def scrape_devsunite(self, request):
        """
        API endpoint to trigger DevSunite scraping with multi-page support
        
        POST /api/jobs/scrape_devsunite/
        {
            "max_jobs": 100,       // 0 = no limit, default 100
            "max_pages": 10,       // Maximum pages to scrape, default 10
            "scrape_details": true // Scrape full job details, default true
        }
        """
        try:
            # Get parameters from request
            max_jobs = request.data.get('max_jobs', 100)
            max_pages = request.data.get('max_pages', 10)
            scrape_details = request.data.get('scrape_details', True)
            
            # Validate parameters
            if not isinstance(max_jobs, int) or max_jobs < 0 or max_jobs > 1000:
                return Response(
                    {'error': 'max_jobs must be an integer between 0 and 1000 (0 = no limit)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not isinstance(max_pages, int) or max_pages < 1 or max_pages > 50:
                return Response(
                    {'error': 'max_pages must be an integer between 1 and 50'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize scraper and run
            scraper = DevSuniteScraperService()
            results = scraper.scrape_jobs(max_jobs=max_jobs, max_pages=max_pages, scrape_details=scrape_details)
            
            # Return results
            if results['success']:
                return Response(results, status=status.HTTP_200_OK)
            else:
                return Response(results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"❌ Error in scrape_devsunite endpoint: {e}")
            return Response(
                {'error': f'Scraping failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """
        API endpoint to refresh jobs by triggering a scraping operation
        
        POST /api/jobs/refresh/
        """
        try:
            # Use default parameters for refresh - moderate scraping
            max_jobs = 50  # Reasonable default for refresh
            max_pages = 5  # 5 pages should be enough for a refresh
            scrape_details = True  # Always scrape details for complete job info
            
            logger.info(f"🔄 Jobs refresh triggered via API endpoint")
            
            # Initialize scraper and run
            scraper = DevSuniteScraperService()
            results = scraper.scrape_jobs(max_jobs=max_jobs, max_pages=max_pages, scrape_details=scrape_details)
            
            # Return results
            if results['success']:
                return Response({
                    'success': True,
                    'message': 'Jobs refreshed successfully',
                    'jobs_scraped': results.get('jobs_scraped', 0),
                    'jobs_saved': results.get('jobs_saved', 0),
                    'pages_scraped': results.get('pages_scraped', 0),
                    'errors': results.get('errors', [])
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Jobs refresh completed with some issues',
                    'jobs_scraped': results.get('jobs_scraped', 0),
                    'jobs_saved': results.get('jobs_saved', 0),
                    'pages_scraped': results.get('pages_scraped', 0),
                    'errors': results.get('errors', [])
                }, status=status.HTTP_200_OK)  # Still 200 since operation completed
                
        except Exception as e:
            logger.error(f"❌ Error in refresh endpoint: {e}")
            return Response(
                {'success': False, 'error': f'Refresh failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def scraping_stats(self, request):
        """
        Get scraping statistics
        
        GET /api/jobs/scraping_stats/
        """
        try:
            total_jobs = Job.objects.count()
            scraped_with_details = Job.objects.filter(details_scraped=True).count()
            recent_jobs = Job.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
            
            stats = {
                'total_jobs': total_jobs,
                'jobs_with_details': scraped_with_details,
                'recent_jobs_7_days': recent_jobs,
                'completion_rate': f"{(scraped_with_details/total_jobs*100):.1f}%" if total_jobs > 0 else "0%"
            }
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get stats: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['delete'])
    def clear_jobs(self, request):
        """
        Clear all jobs from database
        
        DELETE /api/jobs/clear_jobs/
        """
        try:
            count = Job.objects.count()
            Job.objects.all().delete()
            
            return Response(
                {'message': f'Cleared {count} jobs from database'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': f'Failed to clear jobs: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
