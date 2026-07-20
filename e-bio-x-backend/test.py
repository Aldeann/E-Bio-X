from src.config.drive import drive_service
import os

folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
print("Folder ID:", folder_id)

try:
    result = drive_service.files().list(pageSize=1).execute()
    print(result)
except Exception as e:
    print(e)