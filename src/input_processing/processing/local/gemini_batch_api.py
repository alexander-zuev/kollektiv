from google.cloud import bigquery
from google.cloud import aiplatform
import uuid
import time

# Set up clients
bq_client = bigquery.Client()
aiplatform.init(project='gemini-over-api', location='us-central1')

# Create a unique dataset and table names
dataset_id = f"gemini_batch_{uuid.uuid4().hex[:8]}"
input_table_id = f"{dataset_id}.input_table"
output_table_id = f"{dataset_id}.output_table"

# Create a new dataset
dataset = bigquery.Dataset(f"{bq_client.project}.{dataset_id}")
dataset = bq_client.create_dataset(dataset)

# Create input table and insert dummy data
schema = [
    bigquery.SchemaField("text_input", "STRING"),  # Use a single column for text input
]
table = bigquery.Table(input_table_id, schema=schema)
table = bq_client.create_table(table)

rows_to_insert = [
    {"text_input": "Summarize the benefits of exercise."},
    {"text_input": "Explain quantum computing in simple terms."},
    {"text_input": "What are the main causes of climate change?"},
    {"text_input": "Describe the process of photosynthesis."},
    {"text_input": "List 5 tips for effective time management."},
]

errors = bq_client.insert_rows_json(table, rows_to_insert)
if errors:
    print(f"Errors occurred while inserting rows: {errors}")
else:
    print("Rows inserted successfully")

# Create output table schema (adjust based on Gemini's output format)
output_schema = [
    bigquery.SchemaField("text_input", "STRING"),
    bigquery.SchemaField("prediction", "STRING"),  # Assuming Gemini returns text predictions
]

output_table = bigquery.Table(output_table_id, schema=output_schema)
bq_client.create_table(output_table)

# Create batch prediction job (replace with the correct Gemini model name)
batch_prediction_job = aiplatform.BatchPredictionJob.create(
    job_display_name=f"gemini_batch_job_{uuid.uuid4().hex[:8]}",
    model_name="projects/gemini-over-api/locations/us-central1/models/gemini-1.5-flash-001",  # Use the correct model ID
    instances_format="bigquery",
    predictions_format="bigquery",
    bigquery_source=f"bq://{bq_client.project}.{input_table_id}",
    bigquery_destination_prefix=f"bq://{bq_client.project}.{output_table_id}",
)

# Wait for the batch job to complete
print("Waiting for batch prediction job to complete...")
batch_prediction_job.wait()

if batch_prediction_job.state == aiplatform.JobState.JOB_STATE_SUCCEEDED:
    print("Batch prediction job completed successfully.")

    # Retrieve results
    query = f"""
    SELECT text_input, prediction
    FROM `{bq_client.project}.{output_table_id}`
    """
    query_job = bq_client.query(query)
    results = query_job.result()

    for row in results:
        print(f"Request: {row['text_input']}")
        print(f"Response: {row['prediction']}")
        print("---")
else:
    print(f"Batch prediction job failed with state: {batch_prediction_job.state}")

# Clean up (optional)
bq_client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)