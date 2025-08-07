import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get SAS URL
sas_url = os.getenv("SAS_URL")
if not sas_url:
    raise ValueError("SAS_URL environment variable is not set")

# Extract account and token from SAS URL
account_url = sas_url.split('?')[0]
sas_token = sas_url.split('?')[1]
container_name = account_url.split("/")[-1]

# Set your local base folder
local_base = "2025"

# Initialize Azure blob service client
blob_service_client = BlobServiceClient(account_url=account_url, credential=sas_token)
container_client = blob_service_client.get_container_client(container=container_name)

uploaded_count = 0

# Walk through all files in the local directory
for root, _, files in os.walk(local_base):
    for file in files:
        if file.lower().endswith((".pdf", ".txt")):
            local_path = os.path.join(root, file)

            relative_path = os.path.relpath(local_path, start=local_base).replace("\\", "/")

            blob_path = f"{local_base}/{relative_path}"

            if file.lower().endswith(".pdf"):
                content_type = "application/pdf"
            elif file.lower().endswith(".txt"):
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"

            print(f"📤 Uploading: {blob_path}")

            with open(local_path, "rb") as data:
                container_client.upload_blob(
                    name=blob_path,
                    data=data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )

            uploaded_count += 1

print(f"\n✅ Uploaded {uploaded_count} file(s) (.pdf/.txt) to Azure Blob Storage.")
