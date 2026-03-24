import os
from azure.storage.blob import BlobServiceClient, ContainerClient

# --- CONFIGURATION ---
AZURE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=fbbackupkhushi;AccountKey=***REMOVED_AZURE_KEY***==;EndpointSuffix=core.windows.net"
# NOTE: User should update this to their OWN connection string for apifunctionsad76 to check status properly
# or use the SAS URL.

DEST_SAS_URL = "https://apifunctionsad76.blob.core.windows.net/backup?sp=rwdl&st=2026-03-17T14:59:06Z&se=2026-03-19T23:14:06Z&sv=2024-11-04&sr=c&sig=***REMOVED_SAS_SIG***"

def check_status():
    print("🔍 Checking migration status on apifunctionsad76...")
    try:
        dest_container = ContainerClient.from_container_url(DEST_SAS_URL)
        blobs = list(dest_container.list_blobs())
        print(f"✅ Found {len(blobs)} files in your destination container.")
        
        pending = 0
        for blob in blobs:
            props = dest_container.get_blob_client(blob.name).get_blob_properties()
            if props.copy.status == 'pending':
                pending += 1
        
        if pending > 0:
            print(f"⏳ {pending} files are still being transferred by Azure (server-side).")
        else:
            print("✨ All files have finished transferring!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_status()
