import os
import time
from azure.storage.blob import BlobServiceClient, ContainerClient

# --- CONFIGURATION ---
SOURCE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=fbbackupkhushi;AccountKey=***REMOVED_AZURE_KEY***==;EndpointSuffix=core.windows.net"
SOURCE_CONTAINER = "backup"


DEST_SAS_URL = "https://apifunctionsad76.blob.core.windows.net/backup?sp=rwdl&st=2026-03-17T14:59:06Z&se=2026-03-19T23:14:06Z&sv=2024-11-04&sr=c&sig=***REMOVED_SAS_SIG***" 

def migrate():
    if "..." in DEST_SAS_URL:
        print("ERROR: Please paste your complete Destination SAS URL into the script!")
        return

    print("🚀 Starting migration from fbbackupkhushi to apifunctionsad76...")
    
    source_service = BlobServiceClient.from_connection_string(SOURCE_CONNECTION_STRING)
    source_container = source_service.get_container_client(SOURCE_CONTAINER)
    
    dest_container = ContainerClient.from_container_url(DEST_SAS_URL)

    blobs = list(source_container.list_blobs())
    total = len(blobs)
    print(f"📦 Found {total} files to move.")
    
    for i, blob in enumerate(blobs, 1):
        print(f"[{i}/{total}] Copying: {blob.name}...", end="\r")

        source_blob_url = f"https://fbbackupkhushi.blob.core.windows.net/{SOURCE_CONTAINER}/{blob.name}"
        dest_blob = dest_container.get_blob_client(blob.name)
        
        from datetime import datetime, timedelta
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        
        sas_token = generate_blob_sas(
            account_name=source_service.account_name,
            container_name=SOURCE_CONTAINER,
            blob_name=blob.name,
            account_key=source_service.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        
        copy_source_url = f"{source_blob_url}?{sas_token}"
        dest_blob.start_copy_from_url(copy_source_url)
        
    print(f"\n Migration complete! {total} files processed.")

if __name__ == "__main__":
    migrate()
