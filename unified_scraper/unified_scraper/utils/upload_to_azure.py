import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv

load_dotenv()

sas_url = os.getenv("SAS_URL")

if not sas_url:
    raise ValueError("SAS_URL environment variable is not set")

account_url = sas_url.split('?')[0]
sas_token = sas_url.split('?')[1]

container_name = account_url.split("/")[-1]

local_base = "2025"

blob_service_client = BlobServiceClient(account_url=account_url, credential=sas_token)
container_client = blob_service_client.get_container_client(container=container_name)

uploaded_count = 0
for root, _, files in os.walk(local_base):
    for file in files:
        if file.lower().endswith(".pdf",".txt"):
            local_path = os.path.join(root, file)

            
            relative_path = os.path.relpath(local_path, start=local_base).replace("\\", "/")
            blob_path = f"{local_base}/{relative_path}"

            print(f"📤 Uploading: {blob_path}")

            with open(local_path, "rb") as data:
                container_client.upload_blob(
                    name=blob_path,
                    data=data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type="application/pdf")
                )

            uploaded_count += 1

print(f"\n Uploaded {uploaded_count} PDF(s) to Azure Blob Storage.")
