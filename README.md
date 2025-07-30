# Scraplify

A modern job scraping and listing platform built with Django and React. The platform includes an advanced job scraper that extracts comprehensive job information from devsunite.com, including detailed descriptions and required skills from individual job pages.

## Project Structure

```
scraplify/
├── backend/           # Django backend
│   ├── scraplify/    # Main Django project
│   ├── jobs/         # Jobs app with advanced job scraper
│   └── manage.py
├── frontend/         # React frontend
└── README.md
```

## Job Scraper Features

- **Comprehensive Job Data**: Extracts complete job information including detailed descriptions and required skills
- **Smart Link Detection**: Automatically detects and follows "View Details" links to get complete job information
- **Selenium Integration**: Uses Selenium WebDriver with Chrome/Chromium for JavaScript-rendered content
- **Robust Error Handling**: Gracefully handles network issues and parsing errors
- **Customizable Extraction**: Adapts to different job board layouts with multiple selector strategies

## Backend Setup

1. Create and activate virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file in backend directory:
```
SECRET_KEY=your-django-secret-key
DEBUG=True
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

4. Install Chrome/Chromium for Selenium:
```bash
# On Ubuntu/Debian:
sudo apt-get update
sudo apt-get install -y chromium-browser

# On CentOS/RHEL:
sudo yum install -y chromium
```

## Testing the Scraper

Run the comprehensive test script to verify the scraper functionality:

```bash
cd backend
python test_scraper.py --all
```

To test specific components:

```bash
# Test job details extraction
python test_scraper.py --details

# Test API endpoint
python test_scraper.py --api

# Test with a specific job URL
python test_scraper.py --details --job-url https://devsunite.com/jobs/example-job-id
```

## Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env` file in frontend directory:
```
REACT_APP_API_URL=http://localhost:8000/api
```

3. Start development server:
```bash
npm start
```

## Running the Project

1. Start Django backend:
```bash
cd backend
python manage.py runserver
```

2. Start React frontend (in a new terminal):
```bash
cd frontend
npm start
```

3. Visit http://localhost:3000 to view the application