import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.file']
CLOUD_FOLDER_NAME = sys.argv[1]
FILE = sys.argv[2]

def get_gdrive_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('gcp_client_secret.json'):
        creds = Credentials.from_authorized_user_file('gcp_client_secret.json', SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('gcp_client_secret.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name="recordings"):
    """
    Searches for a folder by name. If it exists, returns its ID.
    If it doesn't exist, creates the folder and returns its ID.
    """
    # Search for an existing folder that is not in the trash
    query = (
        f"name = '{folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])

    if folders:
        print(f"Folder '{folder_name}' found. ID: {folders[0]['id']}")
        return folders[0]['id']

    # Folder does not exist, create it
    print(f"Folder '{folder_name}' not found. Creating a new one...")
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    print(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
    return folder.get('id')

def upload_file_to_folder(service, file_path, folder_id):
    """Uploads a local file to a designated Google Drive folder."""
    file_name = os.path.basename(file_path)
    
    # Metadata specifies the file name and parent folder ID
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    # MediaFileUpload manages streaming/resumable file upload
    media = MediaFileUpload(file_path, resumable=True)

    print(f"Uploading '{file_name}' to target folder...")
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name'
    ).execute()

    print(f"Upload complete! File ID: {uploaded_file.get('id')}")
    return uploaded_file.get('id')

# Usage
service = get_gdrive_service()

# Step 1: Get or create the "recordings" folder ID
folder_id = get_or_create_folder(service, folder_name=CLOUD_FOLDER_NAME)

# Step 2: Upload local file to that folder
local_file = FILE  # Path to your local file
 
if os.path.exists(local_file):
    upload_file_to_folder(service, local_file, folder_id)
else:
    print(f"File '{local_file}' not found locally. Please check the path.")
