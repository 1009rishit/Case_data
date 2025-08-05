import aiohttp
import asyncio
import os
import csv
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings
from dotenv import load_dotenv
import ssl

load_dotenv()

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("BLOB_CONTAINER")  
CSV_FILE = "delhi_result.csv"

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


async def upload_pdf_from_url(session, blob_service_client, pdf_url):
    filename = pdf_url.split("/")[-1]

    try:
        async with session.get(pdf_url, ssl=ssl_context) as resp:
            if resp.status == 200:
                blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
                await blob_client.upload_blob(
                    data=resp.content,
                    blob_type="BlockBlob",
                    overwrite=True,
                    content_settings=ContentSettings(content_type="application/pdf")
                )
                print(f"✅ Uploaded: {filename}")
            else:
                print(f"Failed to fetch {pdf_url}, status: {resp.status}")
    except Exception as e:
        print(f"Error uploading {filename}: {e}")


async def main():
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

    async with aiohttp.ClientSession() as session:
        tasks = []

        with open(CSV_FILE, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                pdf_url = row["pdf_url"]
                tasks.append(upload_pdf_from_url(session, blob_service_client, pdf_url))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
