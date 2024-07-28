# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 22:11:43 2024

@author: User
"""

# %%

from __future__ import print_function
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from typing import Dict, Optional
from dotenv import load_dotenv
from gpt_graph.core.component import Component
from gpt_graph.utils.load_env import load_env
import gpt_graph.utils as utils


class GoogleDriveUploader(Component):
    step_type = "node_to_node"
    input_schema = {"upload_file_path": {"type": str}}
    cache_schema = {}
    output_schema = {"upload_file_path": {"type": str}}
    output_format = "plain"

    def __init__(
        self,
        credentials_folder=None,
        google_service_account_file=None,
        if_service_account=True,
        **kwargs,
    ):
        self.scopes = ["https://www.googleapis.com/auth/drive.file"]
        self.service = None
        super().__init__(**kwargs)

        if credentials_folder and google_service_account_file:
            self._initialize(
                credentials_folder=credentials_folder,
                google_service_account_file=google_service_account_file,
                if_service_account=if_service_account,
            )

    def _authenticate(self):
        if self.if_service_account:
            self.service = self._authenticate_service_account()
        else:
            self.service = self._authenticate_oauth2()
        return self.service

    def _authenticate_service_account(self):
        """Authenticate using a service account and create a Google Drive service."""
        creds = service_account.Credentials.from_service_account_file(
            self.service_account_file, scopes=self.scopes
        )
        return build("drive", "v3", credentials=creds)

    def _authenticate_oauth2(self):
        """Authenticate the user and create a Google Drive service."""
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        # print(self.token_file)
        # print("valid:", creds.valid)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        return build("drive", "v3", credentials=creds)

    def list_files_in_folder(self, folder_id="root", level=0):
        """Lists all files and folders in a specific Google Drive folder recursively."""
        service = self.service or self._authenticate()
        results = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1000,
            )
            .execute()
        )
        items = results.get("files", [])

        if not items:
            print(" " * level * 4 + "No files found.")
        else:
            for item in items:
                print(" " * level * 4 + f"{item['name']} ({item['id']})")
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    self.list_files_in_folder(item["id"], level + 1)

    def _find_or_create_folder(self, service, folder_path, parent_id="root"):
        """Find or create a nested folder path on Google Drive."""
        parts = folder_path.split("/")
        current_parent_id = parent_id
        # parent_id = 'root'  # Start from the root directory

        for part in parts:
            if not part:
                continue  # Skip empty parts from leading or double slashes

            # Correctly use parent_id in the query
            query = f"mimeType='application/vnd.google-apps.folder' and name='{part}' and '{current_parent_id}' in parents and trashed=false"
            results = (
                service.files().list(q=query, fields="files(id, name)").execute()
            )  # , fields='files(id, name)'
            folders = results.get("files", [])
            print(
                f"Checking for folder '{part}' under parent ID {current_parent_id}: Found {len(folders)} folders"
            )

            if not folders:
                # No existing folder found, create a new one
                folder_metadata = {
                    "name": part,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [current_parent_id],
                }
                folder = (
                    service.files().create(body=folder_metadata, fields="id").execute()
                )
                print(f"Created folder '{part}', ID: {folder.get('id')}")
                current_parent_id = folder.get(
                    "id"
                )  # Update parent_id to the newly created folder's ID
            else:
                current_parent_id = folders[0].get(
                    "id"
                )  # Folder exists, use its ID as the new parent_id
                print(f"Found existing folder '{part}', ID: {parent_id}")

        return current_parent_id

    def delete_all_in_folder(self, folder_id):
        """Delete all files and folders within the specified Google Drive folder."""
        service = self.service or self._authenticate()
        items = self._list_all_items_in_folder(folder_id)

        # Recursively delete contents of subfolders first
        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                self.delete_all_in_folder(item["id"])

        # Delete the remaining items in this folder
        for item in items:
            try:
                service.files().delete(fileId=item["id"]).execute()
                print(f"Deleted '{item['name']}' (ID: {item['id']})")
            except Exception as e:
                print(f"Failed to delete '{item['name']}' (ID: {item['id']}): {e}")

        # Finally, delete the folder itself
        try:
            service.files().delete(fileId=folder_id).execute()
            print(f"Deleted folder (ID: {folder_id})")
        except Exception as e:
            print(f"Failed to delete folder (ID: {folder_id}): {e}")

    def _list_all_items_in_folder(self, folder_id):
        """List all items in a specified folder."""
        service = self.service
        page_token = None
        items = []
        while True:
            response = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                )
                .execute()
            )
            items.extend(response.get("files", []))
            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break
        return items

    def _initialize(
        self,
        credentials_folder: Optional[str] = None,
        google_service_account_file: Optional[str] = None,
        if_service_account: bool = True,
    ):
        self.credentials_folder = credentials_folder or os.environ.get(
            "CREDENTIALS_FOLDER"
        )

        self.credentials_folder = utils.resolve_rel_path(self.credentials_folder)

        self.if_service_account = if_service_account

        if if_service_account:
            google_service_account_file = google_service_account_file or os.environ.get(
                "GOOGLE_SERVICE_ACCOUNT_FILE"
            )
            self.service_account_file = os.path.join(
                self.credentials_folder, google_service_account_file
            )
        else:
            self.credentials_file = os.path.join(
                self.credentials_folder, "client_secret.apps.googleusercontent.com.json"
            )
            self.token_file = os.path.join(self.credentials_folder, "token.json")

        service = self._authenticate()
        self.service = service

    def run(
        self,
        upload_file_path: str,
        credentials_folder: Optional[str] = None,
        google_service_account_file: Optional[str] = None,
        if_service_account: bool = True,
        drive_file_name: Optional[str] = None,
        drive_folder_path: str = "",
        parent_folder_id: Optional[str] = None,
        mimetype: str = "audio/mp3",
        file_metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Upload a file to Google Drive.

        Args:
            upload_file_path (str): Path to the file to upload.
            credentials_folder (str, optional): Path to the folder containing credentials. If None, uses CREDENTIALS_FOLDER environment variable.
            google_service_account_file (str, optional): Name of the service account JSON file. If None, uses GOOGLE_SERVICE_ACCOUNT_FILE environment variable.
            if_service_account (bool, optional): Whether to use service account authentication. Default is True.
            drive_file_name (str, optional): Name for the file in Google Drive. If None, uses the original file name.
            drive_folder_path (str, optional): Path of the folder to upload the file into. Default is root folder.
            parent_folder_id (str, optional): ID of the parent folder in Google Drive. If None, uses GOOGLE_DRIVER_FOLDER environment variable.
            mimetype (str, optional): MIME type of the file. Default is "audio/mp3".
            file_metadata (Dict, optional): Additional metadata for the file. If None, a default metadata dict is created.

        Returns:
            str: Path of the uploaded file.

        Example:
            uploader = GoogleDriveUploader()
            result = uploader.run(
                upload_file_path="/path/to/file.mp3", # important
                credentials_folder="/path/to/creds",  # important
                google_service_account_file="service_account.json",  # important
                if_service_account=True,
                drive_file_name="my_custom_filename.mp3",
                drive_folder_path="MyFolder/SubFolder",  # important
                parent_folder_id="1234567890abcdef",  # important
                mimetype="audio/mp3",
                file_metadata={"description": "My audio file"}
            )
        """
        self._initialize(
            credentials_folder=credentials_folder,
            google_service_account_file=google_service_account_file,
            if_service_account=if_service_account,
        )

        service = self.service
        drive_file_name = drive_file_name or f"{os.path.basename(upload_file_path)}"
        parent_folder_id = parent_folder_id or os.environ.get("GOOGLE_DRIVER_FOLDER")

        # --------------------------------
        folder_id = self._find_or_create_folder(
            service, drive_folder_path, parent_id=parent_folder_id
        )

        if file_metadata is None:
            file_metadata = {
                "name": drive_file_name,
                "parents": [folder_id],
            }  # os.getenv("GOOGLE_DRIVE_FOLDER")]}

        media = MediaFileUpload(upload_file_path, mimetype=mimetype)
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        print(
            f"Uploaded file '{drive_file_name}' to Google Drive with ID: {file.get('id')}"
        )
        return upload_file_path


# %%
# Example usage
if __name__ == "__main__":
    from gpt_graph.core.pipeline import Pipeline

    test_folder = os.environ.get("TEST_FOLDER")
    upload_path = os.path.join(test_folder, r"inputs\accounting.pdf")
    p = Pipeline()
    uploader = GoogleDriveUploader()

    p | uploader
    p.run(input_data=upload_path, params={"drive_folder_path": r"test/"})
