import os
import json
import time
from datetime import datetime
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
from urllib.parse import urlparse
import signal
import sys
import requests
import logging

from src.utils.config import BASE_DIR, LOG_DIR
from src.utils.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__, 'crawling.log', level=logging.DEBUG)

def update_job_file(job_id, url, status):
    """
    Update the jobs file with the given job information, including a timestamp.

    Args:
    job_id (str): The unique identifier for the job
    url (str): The URL associated with the job
    status (str): The current status of the job
    """
    job_file = "jobs.json"  # Changed from "active_jobs.json"
    jobs = {}
    # Read existing jobs if the file exists
    if os.path.exists(job_file):
        try:
            with open(job_file, 'r') as f:
                jobs = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error reading {job_file}. File may be corrupted.")
            jobs = {}  # Reset to empty dict if file is corrupted
        except IOError:
            logger.error(f"IOError occurred while reading {job_file}.")
            return  # Exit the function if we can't read the file

    # Update or add the job with current timestamp
    current_time = datetime.now().isoformat()
    jobs[job_id] = {
        "url": url,
        "status": status,
        "timestamp": current_time
    }

    # Write updated jobs back to file
    try:
        with open(job_file, 'w') as f:
            json.dump(jobs, f, indent=2)
        logger.info(f"Updated job {job_id} in {job_file} with status: {status}")
    except IOError:
        logger.error(f"IOError occurred while writing to {job_file}.")

class FirecrawlScraper:
    def __init__(self):
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.app = FirecrawlApp(api_key=self.api_key)
        self.current_job_id = None
        self.interrupt_received = False
        self.api_base_url = "https://api.firecrawl.dev/v0"
        logger.debug("FirecrawlScraper initialized")


    def crawl_url(self, base_url, max_pages):
        self.base_url = base_url  # Store base_url as an instance variable
        params = {
            'url': base_url,
            'excludePaths': [
            ],
            'includePaths': ['**/reference/python/**'],  # You can add specific paths to include if needed
            'maxDepth': 5,
            'limit': max_pages,
            'allowBackwardLinks': True,
            'allowExternalLinks': False,
            'scrapeOptions': {
                'formats': ['markdown'],
                'onlyMainContent': True,
            }
        }

        logger.info(f"Starting crawl for: {base_url}")
        crawl_result = self.app.crawl_url(base_url, params=params, wait_until_done=False)
        self.current_job_id = crawl_result['jobId']

        logger.info(f"Crawl job started for {base_url}. Job ID: {self.current_job_id}")
        update_job_file(self.current_job_id, base_url, "pending")
        logger.info("Checking status every 30 seconds...")

        while not self.interrupt_received:
            time.sleep(30)
            status = self.app.check_crawl_status(self.current_job_id)
            logger.info(
                f"[STATUS] Job {self.current_job_id}: {status['status']} - {status['current']}/{status['total']} pages processed.")

            if status['status'] == 'completed':
                update_job_file(self.current_job_id, base_url, "completed")
                return status['data']
            if status['status'] == 'failed':
                update_job_file(self.current_job_id, base_url, "failed")
                raise Exception(f"Crawl job failed: {status.get('error', 'Unknown error')}")
            if self.interrupt_received:
                print("[INFO] Crawl interrupted by user.")
                return None

        logger.warning("Crawl interrupted by user.")
        update_job_file(self.current_job_id, base_url, "cancelled")
        return None


    def signal_handler(self, signum, frame):
        logger.warning("\n[INFO] Interrupt received. Cancelling job...")
        self.interrupt_received = True
        if self.current_job_id:
            self.cancel_job(self.current_job_id)
            sys.exit(0)  # Exit immediately after cancellation

    def cancel_job(self, job_id):
        url = f"{self.api_base_url}/crawl/cancel/{job_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            if result.get('status') == 'cancelled':
                logger.info(f"[INFO] Job {job_id} cancelled successfully.")
                update_job_file(job_id, self.base_url, "cancelled")
            else:
                logger.warning(f"[WARNING] Unexpected response when cancelling job {job_id}: {result}")
        except requests.RequestException as e:
            logger.error(f"[ERROR] Error cancelling job {job_id}: {str(e)}")

def save_raw_data(url, data):
    parsed_url = urlparse(url)
    logger.debug(f"Printing parsed url: {parsed_url}")
    base_name = parsed_url.netloc + parsed_url.path.replace('/', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(BASE_DIR, "src", "input_processing", "data", "raw", f"{base_name}_{timestamp}.json")
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    content = {
        "base_url": url,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }

    with open(filename, 'w') as f:
        json.dump(content, f, indent=2)

    return filename

def scrape_and_save(base_url, max_pages):
    scraper = FirecrawlScraper()
    signal.signal(signal.SIGINT, scraper.signal_handler)

    try:
        raw_data = scraper.crawl_url(base_url, max_pages)
        if raw_data:
            filename = save_raw_data(base_url, raw_data)
            logger.info(f"Crawl completed. Data saved to: {filename}")
            return filename
        else:
            logger.warning("Crawl was interrupted. No data saved.")
            return None
    except SystemExit:
        logger.info("Script terminated due to job cancellation.")
        return None

def view_results(filename):
    if not filename:
        logger.warning("No results to view.")
        print("No results to view.")
        return

    try:
        with open(filename, 'r') as f:
            crawled_data = json.load(f)

        if 'data' not in crawled_data or not crawled_data['data']:
            logger.warning("No crawled data found in the file.")
            print("No crawled data found in the file.")
            return

        # 1. Number of pages crawled
        total_pages = len(crawled_data['data'])
        logger.info(f"Total pages crawled: {total_pages}")
        print(f"\nCrawl Results:")
        print(f"URL: {crawled_data['base_url']}")
        print(f"Timestamp: {crawled_data['timestamp']}")
        print(f"Number of pages crawled: {total_pages}")

        # 2. Check for duplicate pages
        urls = [page.get('metadata', {}).get('sourceURL', '') for page in crawled_data['data']]
        unique_urls = set(urls)
        duplicate_count = len(urls) - len(unique_urls)
        logger.info(f"Number of duplicate pages: {duplicate_count}")
        print(f"Number of duplicate pages: {duplicate_count}")

        # 3. Save and display unique URLs
        unique_urls_file = os.path.join(os.path.dirname(filename), "unique_urls.txt")
        with open(unique_urls_file, 'w') as f:
            for url in sorted(unique_urls):
                f.write(f"{url}\n")
        logger.info(f"List of unique URLs saved to: {unique_urls_file}")
        print(f"List of unique URLs saved to: {unique_urls_file}")

        logger.info("Finished displaying crawl results summary.")

        return unique_urls_file
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from file: {filename}")
        print(f"Error decoding JSON from file: {filename}")
    except IOError:
        logger.error(f"Error reading file: {filename}")
        print(f"Error reading file: {filename}")
    except Exception as e:
        logger.error(f"Unexpected error processing results: {str(e)}")
        print(f"Unexpected error processing results: {str(e)}")

if __name__ == "__main__":
    base_url = "https://supabase.com/docs/reference/python/"
    result_file = scrape_and_save(base_url, max_pages=1)  # Set max_pages high enough to capture
    # all pages
    view_results(result_file)