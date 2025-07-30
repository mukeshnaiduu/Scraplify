from django.core.management.base import BaseCommand
from jobs.views import JobViewSet
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrape jobs from devsunite.com with detailed descriptions and skills'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of jobs to scrape'
        )
        parser.add_argument(
            '--skip-details',
            action='store_true',
            help='Skip scraping detailed job descriptions'
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        skip_details = options.get('skip_details', False)
        
        self.stdout.write(self.style.SUCCESS('Starting job scraper...'))
        
        viewset = JobViewSet()
        
        class MockRequest:
            def __init__(self, params=None):
                self.query_params = params or {}
                
        # Create a request with optional parameters
        request_params = {}
        if limit:
            request_params['limit'] = limit
        if skip_details:
            request_params['skip_details'] = 'true'
            
        request = MockRequest(request_params)
        viewset.request = request
        
        try:
            response = viewset.refresh(request)
            jobs_count = response.data.get('jobs_scraped', 0)
            
            self.stdout.write(self.style.SUCCESS(f'Successfully scraped {jobs_count} jobs'))
            
            if not skip_details:
                self.stdout.write(self.style.SUCCESS('Job details and skills were also scraped'))
                
            return jobs_count
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error scraping jobs: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return 0
