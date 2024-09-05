import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

JOB_FILE = "jobs.json"
API_BASE_URL = "https://api.firecrawl.dev/v0"


def load_jobs():
    if os.path.exists(JOB_FILE):
        with open(JOB_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_jobs(jobs):
    with open(JOB_FILE, 'w') as f:
        json.dump(jobs, f, indent=2)


def cancel_job(job_id, api_key):
    jobs = load_jobs()
    if job_id not in jobs or jobs[job_id]['status'] != 'pending':
        print(f"Job {job_id} is not pending and cannot be cancelled.")
        return

    url = f"{API_BASE_URL}/crawl/cancel/{job_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        if result.get('status') == 'cancelled':
            print(f"Job {job_id} cancelled successfully.")
            jobs[job_id]['status'] = 'cancelled'
            save_jobs(jobs)
        else:
            print(f"Unexpected response when cancelling job {job_id}: {result}")
    except requests.RequestException as e:
        print(f"Error cancelling job {job_id}: {str(e)}")


def list_jobs():
    jobs = load_jobs()
    for job_id, job_info in jobs.items():
        print(f"Job ID: {job_id}")
        print(f"  URL: {job_info['url']}")
        print(f"  Status: {job_info['status']}")
        print()


def cancel_all_pending_jobs(api_key):
    jobs = load_jobs()
    for job_id, job_info in jobs.items():
        if job_info['status'] == 'pending':
            cancel_job(job_id, api_key)


if __name__ == "__main__":
    api_key = os.getenv("FIRECRAWL_API_KEY")

    while True:
        print("\nJob Management Menu:")
        print("1. List all jobs")
        print("2. Cancel a specific job")
        print("3. Cancel all pending jobs")
        print("4. Exit")

        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            list_jobs()
        elif choice == '2':
            job_id = input("Enter the job ID to cancel: ")
            cancel_job(job_id, api_key)
        elif choice == '3':
            confirm = input("Are you sure you want to cancel all pending jobs? (y/n): ")
            if confirm.lower() == 'y':
                cancel_all_pending_jobs(api_key)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

    print("Exiting job management.")