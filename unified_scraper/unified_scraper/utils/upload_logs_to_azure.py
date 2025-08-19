import os
import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv

load_dotenv()

sas_url = os.getenv("SAS_URL")
if not sas_url:
    raise ValueError("SAS_URL environment variable is not set")

account_url = sas_url.split('?')[0]
sas_token = sas_url.split('?')[1]
container_name = os.getenv("CONTAINER_NAME")


def upload_crawl_log(local_log_path: str, user_choice: str):
    """
    Uploads crawl.log file from local folder to Azure Blob Storage in the structure:
    year/month/day/{user_choice}/crawl_TIMESTAMP.log

    Args:
        local_log_path (str): Path to the local crawl.log file
        user_choice (str): Name of the pipeline (e.g., "delhc")
    """
    if not os.path.exists(local_log_path):
        print(f"No log file found at {local_log_path}. Skipping log upload.")
        return

    now = datetime.datetime.now()
    year, month, day = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    # Blob path -> year/month/day/user_choice/crawl_TIMESTAMP.log
    blob_log_path = f"{year}/{month}/{day}/{user_choice}/crawl_{timestamp}.log"

    blob_service_client = BlobServiceClient(account_url=account_url, credential=sas_token)
    container_client = blob_service_client.get_container_client(container=container_name)

    print(f"Uploading crawl.log to Azure: {blob_log_path}")

    try:
        with open(local_log_path, "rb") as data:
            container_client.upload_blob(
                name=blob_log_path,
                data=data,
                overwrite=True,
                content_settings=ContentSettings(content_type="text/plain")
            )
        print(" Successfully uploaded crawl.log to Azure.")
    except Exception as e:
        print(f" Failed to upload crawl.log: {e}")

    # Optional: delete local after upload
    try:
        os.remove(local_log_path)
        print(f" Deleted local log file: {local_log_path}")
    except Exception as e:
        print(f" Failed to delete local log file {local_log_path}: {e}")
