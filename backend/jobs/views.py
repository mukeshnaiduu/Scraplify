from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from bs4 import BeautifulSoup
import requests
import logging
import uuid
import shutil
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time

from .models import Job
from .serializers import JobSerializer

logger = logging.getLogger(__name__)

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all().order_by('-created_at')
    serializer_class = JobSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by job type
        job_type = self.request.query_params.get('job_type', None)
        if job_type:
            queryset = queryset.filter(job_type__in=job_type.split(','))
        
        # Filter by location
        location = self.request.query_params.get('location', None)
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        # Filter by experience
        experience = self.request.query_params.get('experience', None)
        if experience:
            queryset = queryset.filter(experience_required__icontains=experience)
        
        # Search by role or company
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(role__icontains=search) | 
                Q(company_name__icontains=search)
            )
        
        return queryset

    @action(detail=False, methods=['post'], url_path='refresh')
    def refresh(self, request):
        """Endpoint to trigger job scraping from devsunite.com using Selenium"""
        driver = None
        
        try:
            # Setup Chrome options for headless browsing in codespace environment
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Set the binary location to our installed Chrome
            chrome_options.binary_location = "/usr/bin/google-chrome-stable"
            
            # Create a unique user data directory
            import os
            import tempfile
            temp_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            
            # Initialize the driver with Chrome
            driver = webdriver.Chrome(options=chrome_options)
            
            base_url = 'https://devsunite.com/jobs'
            jobs_scraped_count = 0
            max_pages = 5  # Limit for testing
            
            # Since pagination doesn't change URL, we'll handle it with Selenium
            logger.info(f"Starting to scrape devsunite.com/jobs")
            driver.get(base_url)
            
            # Wait for the page to load and jobs to appear
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "main"))
                )
                time.sleep(3)  # Wait for dynamic content to load
                logger.info("Page loaded successfully")
            except TimeoutException:
                logger.warning("Timeout waiting for page to load")
                return Response({'status': 'error', 'message': 'Page load timeout'})
            
            # Process multiple pages using pagination
            current_page = 1
            while current_page <= max_pages:
                logger.info(f"Processing page {current_page}")
                
                # Get page source and parse with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find job cards based on devsunite structure
                job_cards = self._find_job_cards(soup)
                
                if not job_cards:
                    logger.info(f"No job cards found on page {current_page}. Ending scrape.")
                    break
                
                logger.info(f"Found {len(job_cards)} job cards on page {current_page}")
                
                # Process each job card
                for i, card in enumerate(job_cards):
                    try:
                        logger.info(f"Processing job card {i+1}/{len(job_cards)}")
                        job_data = self._extract_job_from_card(card, driver)
                        
                        if job_data and job_data.get('role') and job_data.get('company_name'):
                            job, created = Job.objects.update_or_create(
                                company_name=job_data['company_name'],
                                role=job_data['role'],
                                defaults=job_data
                            )
                            if created:
                                jobs_scraped_count += 1
                                logger.info(f"Created job: {job_data['role']} at {job_data['company_name']}")
                            else:
                                logger.info(f"Updated job: {job_data['role']} at {job_data['company_name']}")
                        
                    except Exception as e:
                        logger.error(f"Error processing job card {i+1}: {e}")
                        continue
                
                # Try to navigate to next page
                if not self._go_to_next_page(driver, current_page):
                    logger.info("No more pages to process")
                    break
                    
                current_page += 1
                time.sleep(2)  # Wait between pages
            
            return Response({'status': 'success', 'jobs_scraped': jobs_scraped_count})
            
        except Exception as e:
            logger.error(f"An unexpected error occurred during scraping: {e}")
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.debug(f"Error closing driver: {e}")

    def _find_job_cards(self, soup):
        """Find job cards in the devsunite.com page based on actual structure"""
        job_cards = []
        
        # Based on the provided HTML structure, the job cards have these patterns:
        selectors_to_try = [
            # Primary selector based on the actual structure
            'div.group.relative.w-full',  # Main card container
            'div[class*="group"][class*="relative"][class*="w-full"]',  # More flexible version
            'div[class*="rounded-lg"][class*="text-card-foreground"]:has(a[href*="/jobs/"])',  # Inner card with job links
            'div[class*="border"][class*="border-neutral-800"][class*="bg-black"]',  # Specific styling classes
            # Fallback selectors
            'div:has(a[href*="/jobs/"]):has(span:contains("View Details"))',  # Has job link and view details
            'div:has(span:contains("Apply Now")):has(span:contains("View Details"))',  # Has both buttons
            'div[class*="shadow"]:has(img[alt]):has(a[href^="/jobs/"])',  # Has company logo and job link
        ]
        
        for selector in selectors_to_try:
            try:
                job_cards = soup.select(selector)
                if job_cards and len(job_cards) > 0:
                    # Filter out cards that are actually job listings
                    filtered_cards = []
                    for card in job_cards:
                        # Check if card has the essential elements of a job listing
                        has_company = card.find('img', alt=True) or card.find(text=lambda text: text and any(word in text.upper() for word in ['COMPANY', 'CORP', 'INC', 'LTD', 'TECH', 'SOLUTIONS']))
                        has_role = card.find(text=lambda text: text and any(word in text.lower() for word in ['engineer', 'developer', 'designer', 'manager', 'analyst', 'specialist']))
                        has_buttons = card.find('a', string=lambda text: text and 'view details' in text.lower()) and card.find('a', string=lambda text: text and 'apply' in text.lower())
                        
                        if has_company or has_role or has_buttons:
                            filtered_cards.append(card)
                    
                    if filtered_cards:
                        logger.info(f"Found {len(filtered_cards)} job cards using selector: {selector}")
                        return filtered_cards
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        logger.warning("No job cards found with any selector")
        return []

    def _go_to_next_page(self, driver, current_page):
        """Handle pagination on devsunite.com"""
        try:
            # Look for next page button or pagination controls
            next_selectors = [
                'button[aria-label*="next"]',
                'button:contains("Next")',
                'a[aria-label*="next"]',
                'a:contains("Next")',
                '[class*="next"]:not([disabled])',
                '[class*="pagination"] button:last-child:not([disabled])',
                f'button[aria-label="Go to page {current_page + 1}"]',
                f'a[aria-label="Go to page {current_page + 1}"]'
            ]
            
            for selector in next_selectors:
                try:
                    # Use JavaScript to find and click next button
                    script = f"""
                    var elements = document.querySelectorAll('{selector}');
                    for (var i = 0; i < elements.length; i++) {{
                        var elem = elements[i];
                        if (elem.textContent.toLowerCase().includes('next') || 
                            elem.getAttribute('aria-label') && elem.getAttribute('aria-label').toLowerCase().includes('next')) {{
                            elem.click();
                            return true;
                        }}
                    }}
                    return false;
                    """
                    
                    result = driver.execute_script(script)
                    if result:
                        logger.info(f"Clicked next page button using selector: {selector}")
                        time.sleep(3)  # Wait for page to load
                        return True
                        
                except Exception as e:
                    logger.debug(f"Error with next selector {selector}: {e}")
                    continue
            
            # Try to find pagination by page numbers
            try:
                next_page_script = f"""
                var pageButtons = document.querySelectorAll('[class*="pagination"] button, [class*="pagination"] a');
                for (var i = 0; i < pageButtons.length; i++) {{
                    var btn = pageButtons[i];
                    if (btn.textContent.trim() === '{current_page + 1}') {{
                        btn.click();
                        return true;
                    }}
                }}
                return false;
                """
                
                result = driver.execute_script(next_page_script)
                if result:
                    logger.info(f"Navigated to page {current_page + 1} by clicking page number")
                    time.sleep(3)
                    return True
                    
            except Exception as e:
                logger.debug(f"Error with page number navigation: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False
    
    def _extract_job_from_card(self, card, driver):
        """Extract job information from a devsunite.com job card element"""
        try:
            # Initialize job data with defaults
            job_data = {
                'job_type': 'FULL_TIME',  # Default
                'location': 'Remote',  # Default
                'experience_required': 'Not specified',  # Default
                'skills_required': [],
                'short_description': '',
                'full_description': '',
                'apply_link': '',
                'compensation': '',
                'details_scraped': False  # Flag to track if we've scraped the details page
            }
            
            # Extract job title/role
            role = self._extract_job_title(card)
            if not role:
                logger.debug("No job title found in card")
                return None
            
            job_data['role'] = role
            logger.info(f"Found job: {role}")
            
            # Extract company name
            company_name = self._extract_company_name(card, role)
            if not company_name:
                logger.debug("No company name found in card")
                return None
            
            job_data['company_name'] = company_name
            logger.info(f"Company: {company_name}")
            
            # Extract job type (Full-time, Part-time, Internship, etc.)
            job_type = self._extract_job_type(card)
            if job_type:
                job_data['job_type'] = job_type
                logger.debug(f"Job type: {job_type}")
            
            # Extract location
            location = self._extract_location(card)
            if location:
                job_data['location'] = location
                logger.debug(f"Location: {location}")
            
            # Extract experience level
            experience = self._extract_experience(card)
            if experience:
                job_data['experience_required'] = experience
                logger.debug(f"Experience: {experience}")
            
            # Extract description
            description = self._extract_description(card)
            if description:
                job_data['short_description'] = description
                job_data['full_description'] = description
                logger.debug(f"Short description: {description[:50]}...")
            
            # Extract compensation
            compensation = self._extract_compensation(card)
            if compensation:
                job_data['compensation'] = compensation
                logger.debug(f"Compensation: {compensation}")
            
            # Extract skills
            skills = self._extract_skills(card)
            if skills:
                job_data['skills_required'] = skills
                logger.debug(f"Skills from card: {', '.join(skills[:5])}")
            
            # Extract apply link and view details link
            apply_link, view_details_link = self._extract_links(card)
            if apply_link:
                job_data['apply_link'] = apply_link
                logger.debug(f"Apply link: {apply_link}")
            
            # Always try to get additional info from the details page if we have a link
            # This ensures we get the full job description and skills
            if view_details_link:
                # Store the view details link even if we have an apply link
                job_data['view_details_link'] = view_details_link
                logger.info(f"View details link: {view_details_link}")
                
                if not apply_link:  # If no apply link, use view details as apply link
                    job_data['apply_link'] = view_details_link
                
                # Get complete job details from the job's dedicated page
                try:
                    logger.info(f"Getting additional data from: {view_details_link}")
                    additional_data = self._get_full_description_selenium(view_details_link, driver)
                    if additional_data:
                        # Log what we found from the job details page
                        data_keys = list(additional_data.keys())
                        logger.info(f"Found additional data fields: {', '.join(data_keys)}")
                        
                        # Check for critical fields we want from the details page
                        if 'full_description' in additional_data:
                            desc_length = len(additional_data['full_description'])
                            logger.info(f"Retrieved full job description ({desc_length} chars)")
                            
                        if 'skills_required' in additional_data:
                            skills = additional_data['skills_required']
                            logger.info(f"Retrieved {len(skills)} skills: {', '.join(skills[:5])}...")
                        
                        # Preserve existing data if additional data doesn't provide it
                        for key, value in additional_data.items():
                            if value:  # Only update if the additional data has a non-empty value
                                # For skills, merge lists if both exist
                                if key == 'skills_required' and job_data.get('skills_required'):
                                    combined_skills = list(set(job_data['skills_required'] + value))
                                    job_data[key] = combined_skills
                                    logger.debug(f"Combined skills: {len(combined_skills)} total")
                                else:
                                    job_data[key] = value
                        
                        job_data['details_scraped'] = True
                        logger.info(f"Successfully updated job data with fields from details page")
                except Exception as e:
                    logger.error(f"Error getting additional data from view details page: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning(f"No view details link found for job: {job_data['role']} at {job_data['company_name']}")
            
            # Include the external_id as a unique identifier for this job
            external_id = str(uuid.uuid4())
            job_data['external_id'] = external_id
            
            # Log success with detailed info
            if job_data.get('details_scraped', False):
                logger.info(f"✅ Scraped job with full details: {job_data['role']} at {job_data['company_name']}")
                desc_length = len(job_data.get('full_description', ''))
                skills_count = len(job_data.get('skills_required', []))
                logger.info(f"   - Description: {desc_length} chars, Skills: {skills_count}")
            else:
                logger.info(f"⚠️ Scraped job with basic info only: {job_data['role']} at {job_data['company_name']}")
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error extracting job from card: {e}")
            return None

    def _extract_job_title(self, card):
        """Extract job title from card based on devsunite structure"""
        # Based on the HTML: <div class="tracking-tight text-base sm:text-lg font-semibold leading-tight text-white group-hover:text-[#2CEE91] transition-colors duration-300">Software Engineer</div>
        title_selectors = [
            'div[class*="tracking-tight"][class*="font-semibold"][class*="text-white"]',  # Main title selector
            'div[class*="font-semibold"][class*="leading-tight"]',  # Alternative
            'div[class*="text-base"][class*="sm:text-lg"]',  # Size-based selector
            # Fallback selectors
            'h1', 'h2', 'h3', 'h4',
            '[class*="title"]',
            '[class*="job-title"]',
            'div[class*="font-semibold"]:not([class*="text-xs"])',  # Exclude small text like "Full Time"
        ]
        
        for selector in title_selectors:
            try:
                title_elem = card.select_one(selector)
                if title_elem:
                    title_text = title_elem.get_text().strip()
                    # Make sure it's not the job type badge or company name
                    if (title_text and len(title_text) > 3 and len(title_text) < 100 and
                        title_text.lower() not in ['full time', 'part time', 'internship', 'contract']):
                        return title_text
            except Exception:
                continue
        return None

    def _extract_company_name(self, card, role_text):
        """Extract company name from card based on devsunite structure"""
        # Based on the HTML: <p class="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">Irdeto</p>
        # And: <img alt="Irdeto" loading="lazy" ...>
        
        # Try to get company name from image alt text first (most reliable)
        try:
            img_elem = card.find('img', alt=True)
            if img_elem and img_elem.get('alt'):
                company_name = img_elem.get('alt').strip()
                if company_name and company_name != role_text and len(company_name) < 50:
                    return company_name
        except Exception:
            pass
        
        # Try specific selectors for company name
        company_selectors = [
            'p[class*="text-xs"][class*="font-medium"][class*="text-neutral-500"][class*="uppercase"]',  # Main company selector
            'p[class*="uppercase"][class*="tracking-wide"]',  # Alternative
            'p[class*="text-neutral-500"][class*="mb-1"]',  # Style-based
            # Fallback selectors
            '[class*="company"]',
            '[class*="employer"]',
            'p:first-of-type',
            'span:first-of-type'
        ]
        
        for selector in company_selectors:
            try:
                company_elem = card.select_one(selector)
                if company_elem:
                    company_text = company_elem.get_text().strip()
                    # Skip if it's the same as role or contains unwanted words
                    if (company_text and company_text != role_text and 
                        len(company_text) > 1 and len(company_text) < 50 and
                        not any(word in company_text.lower() for word in ['apply', 'view', 'details', 'ago', 'hours', 'days', 'full time', 'part time'])):
                        return company_text
            except Exception:
                continue
        return None

    def _extract_job_type(self, card):
        """Extract job type from card based on devsunite structure"""
        # Based on the HTML: <div class="inline-flex items-center rounded-full border px-2.5 py-0.5 font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-950 focus:ring-offset-2 border-neutral-700 bg-neutral-800 text-neutral-300 text-xs">Full Time</div>
        
        # Try specific selector for job type badge
        job_type_selectors = [
            'div[class*="inline-flex"][class*="rounded-full"][class*="px-2.5"][class*="py-0.5"]',  # Main job type badge
            'div[class*="border-neutral-700"][class*="bg-neutral-800"][class*="text-xs"]',  # Style-based
            'span[class*="rounded-full"][class*="px-2"]',  # Alternative badge style
            'div[class*="badge"]',  # Generic badge
        ]
        
        for selector in job_type_selectors:
            try:
                job_type_elem = card.select_one(selector)
                if job_type_elem:
                    job_type_text = job_type_elem.get_text().strip().lower()
                    
                    if 'full time' in job_type_text or 'full-time' in job_type_text:
                        return 'FULL_TIME'
                    elif 'part time' in job_type_text or 'part-time' in job_type_text:
                        return 'PART_TIME'
                    elif 'internship' in job_type_text or 'intern' in job_type_text:
                        return 'INTERNSHIP'
                    elif 'contract' in job_type_text or 'freelance' in job_type_text:
                        return 'CONTRACT'
            except Exception:
                continue
        
        # Fallback: check entire card text
        card_text = card.get_text().lower()
        if 'internship' in card_text or 'intern' in card_text:
            return 'INTERNSHIP'
        elif 'part-time' in card_text or 'part time' in card_text:
            return 'PART_TIME'
        elif 'contract' in card_text or 'freelance' in card_text:
            return 'CONTRACT'
        elif 'full-time' in card_text or 'full time' in card_text:
            return 'FULL_TIME'
        
        return 'FULL_TIME'  # Default

    def _extract_location(self, card):
        """Extract location from card based on devsunite structure"""
        # Based on the HTML: <span class="font-medium truncate">Noida</span> (inside location icon container)
        
        # Look for location near map pin icon
        location_selectors = [
            'svg[class*="lucide-map-pin"] + span',  # Span right after map pin icon
            'svg[class*="map-pin"] ~ span',  # Any span after map pin
            'div:has(svg[class*="map-pin"]) span[class*="font-medium"]',  # Font medium span in map pin container
            'span[class*="truncate"]',  # Truncate class often used for location
            # Fallback selectors
            '[class*="location"]',
            '[class*="place"]',
            '[class*="city"]'
        ]
        
        for selector in location_selectors:
            try:
                location_elem = card.select_one(selector)
                if location_elem:
                    location_text = location_elem.get_text().strip()
                    # Skip if it looks like experience or other data
                    if (location_text and len(location_text) < 50 and 
                        not any(word in location_text.lower() for word in ['year', 'month', 'experience', 'apply', 'view'])):
                        return location_text
            except Exception:
                continue
        
        # Fallback: check for common location patterns in text
        card_text = card.get_text().lower()
        if 'remote' in card_text:
            return 'Remote'
        elif 'onsite' in card_text or 'on-site' in card_text:
            return 'Onsite'
        elif 'hybrid' in card_text:
            return 'Hybrid'
        
        return 'Not specified'

    def _extract_experience(self, card):
        """Extract experience level from card based on devsunite structure"""
        # Based on the HTML: <span class="font-medium">0 years</span> (inside clock icon container)
        
        # Look for experience near clock icon
        experience_selectors = [
            'svg[class*="lucide-clock"] + span',  # Span right after clock icon
            'svg[class*="clock"] ~ span',  # Any span after clock
            'div:has(svg[class*="clock"]) span[class*="font-medium"]',  # Font medium span in clock container
            # Fallback patterns
            'span:contains("years")',
            'span:contains("experience")',
            'div:contains("years")',
        ]
        
        for selector in experience_selectors:
            try:
                exp_elem = card.select_one(selector)
                if exp_elem:
                    exp_text = exp_elem.get_text().strip()
                    # Skip if it's location or other data
                    if (exp_text and ('year' in exp_text.lower() or 'experience' in exp_text.lower()) and 
                        len(exp_text) < 30):
                        return exp_text
            except Exception:
                continue
        
        # Fallback: look for experience patterns in the entire card text
        card_text = card.get_text().lower()
        
        experience_patterns = [
            ('entry level', 'Entry Level'),
            ('junior', 'Junior'),
            ('senior', 'Senior'),
            ('mid level', 'Mid Level'),
            ('lead', 'Lead'),
            ('principal', 'Principal'),
            ('0 years', 'Entry Level'),
            ('0-1 years', 'Entry Level'),
            ('1-3 years', 'Junior'),
            ('3-5 years', 'Mid Level'),
            ('5+ years', 'Senior'),
            ('fresher', 'Entry Level'),
            ('experienced', 'Mid Level')
        ]
        
        for pattern, level in experience_patterns:
            if pattern in card_text:
                return level
        
        return 'Not specified'

    def _extract_description(self, card):
        """Extract job description from card based on devsunite structure"""
        # Based on the HTML: <p class="text-sm text-neutral-300 leading-relaxed line-clamp-3">Who we are: Irdeto is the world leader...</p>
        
        desc_selectors = [
            'p[class*="text-sm"][class*="text-neutral-300"][class*="leading-relaxed"]',  # Main description
            'p[class*="line-clamp-3"]',  # Clamped text (description)
            'p[class*="text-neutral-300"]:not([class*="text-xs"])',  # Neutral text that's not extra small
            # Fallback selectors
            '[class*="description"]',
            '[class*="summary"]',
            'p:not(:first-child):not(:last-child)',  # Middle paragraphs
            'p[class*="text-sm"]:not([class*="uppercase"])',  # Small text that's not uppercase (not company name)
        ]
        
        for selector in desc_selectors:
            try:
                desc_elem = card.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text().strip()
                    # Make sure it's substantial content and not metadata
                    if (desc_text and len(desc_text) > 50 and 
                        not any(word in desc_text.lower() for word in ['compensation', 'apply now', 'view details'])):
                        # Truncate if too long for short description
                        if len(desc_text) > 200:
                            return desc_text[:200] + '...'
                        return desc_text
            except Exception:
                continue
        
        return ''

    def _extract_compensation(self, card):
        """Extract compensation/salary from card based on devsunite structure"""
        # Based on the HTML: <span class="text-sm font-semibold text-neutral-200">6-12 LPA</span> (in compensation section)
        
        # Look for compensation section specifically
        comp_selectors = [
            'span[class*="text-sm"][class*="font-semibold"][class*="text-neutral-200"]',  # Specific styling
            # Look for compensation in border-t section (above buttons)
            'div[class*="border-t"] span[class*="font-semibold"]',
            'div[class*="py-3"] span[class*="font-semibold"]',
        ]
        
        for selector in comp_selectors:
            try:
                comp_elem = card.select_one(selector)
                if comp_elem:
                    comp_text = comp_elem.get_text().strip()
                    # Make sure it's not the label itself and contains salary indicators
                    if (comp_text and comp_text.lower() != 'compensation' and 
                        any(indicator in comp_text.lower() for indicator in ['lpa', 'ctc', '$', '₹', '€', '£', 'salary', 'k', 'lakhs'])):
                        return comp_text
            except Exception:
                continue
        
        # Alternative: look for text near "Compensation" label
        try:
            comp_sections = card.find_all('span', string=lambda text: text and 'compensation' in text.lower())
            for comp_section in comp_sections:
                # Look for the next span with salary info
                parent = comp_section.parent
                if parent:
                    salary_span = parent.find('span', class_=lambda classes: classes and 'font-semibold' in ' '.join(classes))
                    if salary_span:
                        salary_text = salary_span.get_text().strip()
                        if salary_text and salary_text.lower() != 'compensation':
                            return salary_text
        except Exception:
            pass
        
        # Fallback: use regex to find salary patterns in entire card
        card_text = card.get_text()
        
        import re
        salary_patterns = [
            r'\d+\s*-\s*\d+\s*LPA',  # Indian format like "6-12 LPA"
            r'\d+\s*LPA',  # Single LPA amount
            r'\$[\d,]+(?:\s*-\s*\$?[\d,]+)?(?:\s*(?:per|\/)\s*(?:year|yr|month|mo|hour|hr))?',
            r'₹[\d,]+(?:\s*-\s*₹?[\d,]+)?(?:\s*(?:per|\/)\s*(?:year|yr|month|mo|hour|hr))?',
            r'€[\d,]+(?:\s*-\s*€?[\d,]+)?(?:\s*(?:per|\/)\s*(?:year|yr|month|mo|hour|hr))?',
            r'£[\d,]+(?:\s*-\s*£?[\d,]+)?(?:\s*(?:per|\/)\s*(?:year|yr|month|mo|hour|hr))?'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, card_text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ''

    def _extract_skills(self, card):
        """Extract skills from card"""
        skills = []
        
        # Look for skill tags or badges (but exclude job type badges)
        skill_selectors = [
            '[class*="skill"]',
            '[class*="tag"]:not([class*="rounded-full"])',  # Exclude job type badges
            '[class*="badge"]:not([class*="rounded-full"])',  # Exclude job type badges
            '[class*="tech"]',
            '.bg-blue-100',
            '.bg-gray-100'
        ]
        
        for selector in skill_selectors:
            try:
                skill_elems = card.select(selector)
                for elem in skill_elems:
                    skill_text = elem.get_text().strip()
                    # Clean up the skill text and avoid duplicates
                    # Also exclude common non-skill text
                    if (skill_text and len(skill_text) < 30 and 
                        skill_text not in skills and
                        '\n' not in skill_text and
                        skill_text.lower() not in ['full time', 'part time', 'internship', 'contract', 'remote', 'onsite', 'hybrid']):
                        skills.append(skill_text)
            except Exception:
                continue
        
        return skills[:10]  # Limit to 10 skills

    def _extract_links(self, card):
        """Extract apply link and view details link from card based on devsunite structure"""
        # Based on the HTML from example:
        # <a class="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&amp;_svg]:pointer-events-none [&amp;_svg]:size-4 [&amp;_svg]:shrink-0 border hover:text-accent-foreground h-9 rounded-md px-3 flex-1 min-w-[120px] border-neutral-700 bg-neutral-900 hover:bg-neutral-800 hover:border-neutral-600 text-neutral-200 transition-all duration-300" href="/jobs/6rN07maF7MvYvJwuUFNh"><span class="whitespace-nowrap">View Details</span></a>
        
        apply_link = None
        view_details_link = None
        
        # Look for links in the card
        links = card.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            link_text = link.get_text().lower().strip()
            
            if not href:
                continue
                
            # Check for the exact class structure from the example
            class_attr = link.get('class', [])
            class_str = ' '.join(class_attr) if isinstance(class_attr, list) else str(class_attr)
            
            # Match link by text content first
            if 'view details' in link_text:
                logger.info(f"Found view details link by text: {href}")
                # Make sure it's a full URL
                if not href.startswith('http'):
                    if href.startswith('/'):
                        view_details_link = f"https://devsunite.com{href}"
                    else:
                        view_details_link = f"https://devsunite.com/{href}"
                else:
                    view_details_link = href
                    
            # Match apply link by text
            elif 'apply now' in link_text or 'apply' in link_text:
                logger.info(f"Found apply link by text: {href}")
                # Apply links are usually external (full URLs)
                apply_link = href
            
            # Also check link class attributes
            elif ('border-neutral-700' in class_str or 'bg-neutral-900' in class_str) and not view_details_link:
                # This matches the example class structure for view details link
                logger.info(f"Found view details link by class attributes: {href}")
                if not href.startswith('http'):
                    if href.startswith('/'):
                        view_details_link = f"https://devsunite.com{href}"
                    else:
                        view_details_link = f"https://devsunite.com/{href}"
                else:
                    view_details_link = href
                
            # Fallback: check href patterns
            elif '/jobs/' in href and not view_details_link:
                # If it contains /jobs/ it's likely a view details link
                logger.info(f"Found view details link by URL pattern: {href}")
                if not href.startswith('http'):
                    if href.startswith('/'):
                        view_details_link = f"https://devsunite.com{href}"
                    else:
                        view_details_link = f"https://devsunite.com/{href}"
                else:
                    view_details_link = href
        
        return apply_link, view_details_link
    
    def _get_full_description_selenium(self, job_url, driver):
        """Get full job description using Selenium based on the provided example HTML structure"""
        try:
            logger.info(f"Fetching detailed job information from: {job_url}")
            driver.get(job_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
            # Give extra time for all elements to render
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            details = {}
            
            # Extract job title if not already found - usually in the header section
            title_selectors = [
                'h1.text-3xl',  # Main job title based on devsunite pattern
                'h1', 
                '[class*="title"]',
                '[class*="job-title"]'
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    details['role'] = title_elem.get_text().strip()
                    break
            
            # Extract company name - usually near the title
            company_selectors = [
                'div.flex.items-center.gap-3 img[alt]',  # Company logo with alt text
                'div.flex.items-center.justify-between h2',  # Company heading
                'div[class*="company-info"] span',
                '[class*="company"]', 
                'h2', 
                'h3'
            ]
            for selector in company_selectors:
                company_elem = soup.select_one(selector)
                if company_elem:
                    if company_elem.name == 'img' and company_elem.has_attr('alt'):
                        text = company_elem['alt'].strip()
                    else:
                        text = company_elem.get_text().strip()
                    
                    if text and len(text) < 50:
                        details['company_name'] = text
                        break
            
            # Extract full job description from specific section
            # Based on the example: <div class="bg-gradient-to-br from-zinc-900/90 to-zinc-950/90 rounded-xl p-8 mb-8 border border-zinc-800/50">
            # with heading "Job Description"
            description = ""
            
            # Exact match for the div structure provided in the example
            job_desc_section = soup.find('h2', string=lambda text: text and 'job description' in text.lower())
            if job_desc_section:
                # Get the parent div containing the description - match the exact class from example
                parent_div = job_desc_section.find_parent('div', class_=lambda c: c and 'bg-gradient-to-br' in c and 'from-zinc-900' in c)
                if parent_div:
                    # Find the prose div that contains the actual description
                    prose_div = parent_div.find('div', class_='prose')
                    if prose_div:
                        description = prose_div.get_text(separator='\n').strip()
                        logger.info("Found description using exact devsunite.com structure")
            
            if not description:
                # Fallback selectors if the exact structure wasn't found
                desc_selectors = [
                    'div.prose.prose-invert',
                    'div.prose',
                    'div[class*="bg-gradient-to-br"] div.prose',
                    'div[class*="description"]',
                    'div[class*="job-details"]',
                    '[class*="content"]', 
                    'article'
                ]
                for selector in desc_selectors:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        description = desc_elem.get_text(separator='\n').strip()
                        logger.info(f"Found description using fallback selector: {selector}")
                        break
            
            if description:
                details['full_description'] = description
                # Create a concise summary for short description (first 200 chars)
                short_desc = ' '.join(description.split()[:30])
                if len(short_desc) > 200:
                    short_desc = short_desc[:200] + '...'
                else:
                    short_desc = short_desc + '...'
                details['short_description'] = short_desc
                logger.info(f"Extracted description: {len(description)} chars")
            
            # Extract skills from the specific "Required Skills" section
            # Based on the example: <div class="bg-gradient-to-br from-zinc-900/90 to-zinc-950/90 rounded-xl p-8 mb-8 border border-zinc-800/50">
            # with heading "Required Skills"
            skills = []
            
            # Exact match for the structure provided in the example
            skills_section = soup.find('h2', string=lambda text: text and ('required skills' in text.lower() or 
                                                                            'skills' in text.lower() or 
                                                                            'tech stack' in text.lower()))
            if skills_section:
                # Get the parent div containing the skills - match the exact class from example
                parent_div = skills_section.find_parent('div', class_=lambda c: c and 'bg-gradient-to-br' in c and 'from-zinc-900' in c)
                if parent_div:
                    # Try multiple skill selectors based on the example
                    skill_selectors = [
                        'div.flex.flex-wrap span[class*="bg-[#2CEE91]"]',  # Green background
                        'div.flex.flex-wrap span[class*="text-[#2CEE91]"]',  # Green text
                        'div.flex.flex-wrap span[class*="border-[#2CEE91]"]',  # Green border
                        'div.flex.flex-wrap span',  # Any span in a flex wrap container
                    ]
                    
                    for selector in skill_selectors:
                        skill_spans = parent_div.select(selector)
                        if skill_spans:
                            logger.info(f"Found {len(skill_spans)} skills using selector: {selector}")
                            for span in skill_spans:
                                skill_text = span.get_text().strip()
                                if skill_text and skill_text not in skills and len(skill_text) < 30:
                                    skills.append(skill_text)
                            
                            # If we found skills, no need to try other selectors
                            if skills:
                                break
            
            if not skills:
                # Fallback selectors if the specific structure wasn't found
                skill_selectors = [
                    # More specific based on the example structure
                    'div.flex.flex-wrap span[class*="text-[#2CEE91]"]',
                    'div.flex.flex-wrap span[class*="border-[#2CEE91]"]',
                    'div.flex.flex-wrap span',
                    # General fallbacks
                    'span[class*="bg-[#2CEE91]"]',
                    '[class*="skill"]', 
                    '[class*="tag"]', 
                    '[class*="badge"]',
                    'span[class*="rounded-lg"]', 
                    'ul li', 
                    '.tech-stack'
                ]
                for selector in skill_selectors:
                    skill_elems = soup.select(selector)
                    if skill_elems:
                        logger.info(f"Found {len(skill_elems)} skills using fallback selector: {selector}")
                        for elem in skill_elems:
                            skill_text = elem.get_text().strip()
                            if skill_text and len(skill_text) < 30 and skill_text not in skills:
                                skills.append(skill_text)
                        # If we found skills with this selector, stop trying others
                        if skills:
                            break
            
            if skills:
                details['skills_required'] = skills[:15]  # Allow up to 15 skills
                logger.info(f"Found {len(details['skills_required'])} skills: {', '.join(details['skills_required'])}")
            
            # Extract location information more accurately
            location_section = soup.find('div', string=lambda text: text and 'location' in text.lower())
            if location_section:
                next_elem = location_section.find_next('div')
                if next_elem:
                    details['location'] = next_elem.get_text().strip()
            else:
                # Try to extract location and job type from text
                page_text = soup.get_text().lower()
                if 'remote' in page_text:
                    details['location'] = 'Remote'
                elif 'onsite' in page_text or 'on-site' in page_text:
                    details['location'] = 'Onsite'
                elif 'hybrid' in page_text:
                    details['location'] = 'Hybrid'
            
            # Extract job type more accurately
            job_type_section = soup.find('div', string=lambda text: text and 'job type' in text.lower())
            if job_type_section:
                next_elem = job_type_section.find_next('div')
                if next_elem:
                    job_type_text = next_elem.get_text().strip().lower()
                    if 'full time' in job_type_text or 'full-time' in job_type_text:
                        details['job_type'] = 'FULL_TIME'
                    elif 'part time' in job_type_text or 'part-time' in job_type_text:
                        details['job_type'] = 'PART_TIME'
                    elif 'contract' in job_type_text:
                        details['job_type'] = 'CONTRACT'
                    elif 'internship' in job_type_text:
                        details['job_type'] = 'INTERNSHIP'
            else:
                # Fallback to page text
                page_text = soup.get_text().lower()
                if 'internship' in page_text:
                    details['job_type'] = 'INTERNSHIP'
                elif 'part-time' in page_text or 'part time' in page_text:
                    details['job_type'] = 'PART_TIME'
                elif 'contract' in page_text:
                    details['job_type'] = 'CONTRACT'
                elif 'full-time' in page_text or 'full time' in page_text:
                    details['job_type'] = 'FULL_TIME'
            
            # Try to extract compensation if available
            compensation_section = soup.find('div', string=lambda text: text and 'compensation' in text.lower())
            if compensation_section:
                next_elem = compensation_section.find_next('div')
                if next_elem:
                    details['compensation'] = next_elem.get_text().strip()
            
            logger.info(f"Successfully scraped detailed job information from: {job_url}")
            return details
            
        except Exception as e:
            logger.error(f"Error getting full description from {job_url}: {e}")
            return {}
