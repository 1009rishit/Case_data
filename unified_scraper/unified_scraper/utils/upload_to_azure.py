import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from Database.models import MetaData
import os
import shutil

load_dotenv()

sas_url = os.getenv("SAS_URL")
if not sas_url:
    raise ValueError("SAS_URL environment variable is not set")

account_url = sas_url.split('?')[0]
sas_token = sas_url.split('?')[1]
container_name = os.getenv('CONTAINER_NAME')


def upload_to_azure(session: Session, downloaded_files,local_base):
    """
    Uploads PDF and TXT files from downloaded_files list to Azure Blob Storage.
    Marks the DB record is_downloaded=True only after PDF upload success.
    
    Args:
        session (Session): SQLAlchemy DB session
        downloaded_files (list of dict): Each dict must have 'id', 'case_id', 'pdf_path'
    """

    blob_service_client = BlobServiceClient(account_url=account_url, credential=sas_token)
    container_client = blob_service_client.get_container_client(container=container_name)

    uploaded_count = 0

    for item in downloaded_files:
        pdf_path = item["pdf_path"]
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found: {pdf_path}, skipping.")
            continue

        # Upload PDF
        relative_pdf_path = os.path.relpath(pdf_path, start=local_base).replace("\\", "/")
        blob_pdf_path = f"{local_base}/{relative_pdf_path}"

        print(f"📤 Uploading PDF: {blob_pdf_path}")
        try:
            with open(pdf_path, "rb") as data:
                container_client.upload_blob(
                    name=blob_pdf_path,
                    data=data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type="application/pdf")
                )
            uploaded_count += 1

            # After PDF upload, mark DB record as downloaded
            session.query(MetaData).filter(MetaData.id == item["id"]).update({"is_downloaded": True})
            session.commit()
        except Exception as e:
            print(f"❌ Failed to upload PDF {pdf_path}: {e}")
            continue

        # Upload TXT if exists
        txt_path = os.path.splitext(pdf_path)[0] + ".txt"
        if os.path.exists(txt_path):
            relative_txt_path = os.path.relpath(txt_path, start=local_base).replace("\\", "/")
            blob_txt_path = f"{local_base}/{relative_txt_path}"

            print(f"📤 Uploading TXT: {blob_txt_path}")
            try:
                with open(txt_path, "rb") as data:
                    container_client.upload_blob(
                        name=blob_txt_path,
                        data=data,
                        overwrite=True,
                        content_settings=ContentSettings(content_type="text/plain")
                    )
                uploaded_count += 1
                
            except Exception as e:
                print(f"Failed to upload TXT {txt_path}: {e}")

    print(f"\nUploaded {uploaded_count} file(s) (.pdf/.txt) to Azure Blob Storage.")

    if os.path.exists(local_base):
        try:
            shutil.rmtree(local_base)
            print(f"Deleted local folder and all contents: {local_base}")
        except Exception as e:
                print(f"Failed to delete folder {local_base}: {e}")
