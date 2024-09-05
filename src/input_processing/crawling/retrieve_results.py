import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urlparse
from src.input_processing.crawling.scraping import save_raw_data

# Load environment variables
load_dotenv()

# FireCrawl API configuration
API_KEY = os.getenv("FIRECRAWL_API_KEY")
API_BASE_URL = "https://api.firecrawl.dev/v0"
JOB_ID = "bac58466-c4e6-444d-a8b0-92d13e7177f1" # replace to retrieve the results
BASE_URL = "https://supabase.com/docs/"


def check_job_status(job_id):
    url = f"{API_BASE_URL}/crawl/status/{job_id}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def retrieve_and_save_results():
    print(f"Checking status for job {JOB_ID}...")
    status = check_job_status(JOB_ID)

    print(f"Job status: {status['status']}")
    print(f"Pages processed: {status['current']}/{status['total']}")

    if status['status'] == 'completed':
        print("Job completed. Saving results...")
        filename = save_raw_data(BASE_URL, status['data'])
        print(f"Results saved to {filename}")
        return filename
    elif status['status'] == 'failed':
        print(f"Job failed. Error: {status.get('error', 'Unknown error')}")
    else:
        print(f"Job is still {status['status']}. Please check again later.")
    return None


def view_results(filename):
    if not filename:
        print("No results to view.")
        return

    with open(filename, 'r') as f:
        crawled_data = json.load(f)

    print(f"\nCrawl Results:")
    print(f"URL: {crawled_data['base_url']}")
    print(f"Timestamp: {crawled_data['timestamp']}")
    print(f"Number of pages crawled: {len(crawled_data['data'])}")

    for i, page in enumerate(crawled_data['data'][:5], 1):  # Display first 5 pages
        print(f"\nPage {i}:")
        print(f"Title: {page['metadata']['title']}")
        print(f"URL: {page['metadata']['sourceURL']}")
        print(f"Markdown preview: {page['markdown'][:200]}...")  # Display first 200 characters of markdown

    if len(crawled_data['data']) > 5:
        print(f"\n... and {len(crawled_data['data']) - 5} more pages")


if __name__ == "__main__":
    result_file = retrieve_and_save_results()
    if result_file:
        view_results(result_file)