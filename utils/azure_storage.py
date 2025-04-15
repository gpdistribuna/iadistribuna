from azure.storage.blob import BlobServiceClient
import os
import json

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = "books-data"

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container_name)

def upload_blob(local_file_path, blob_name):
    try:
        with open(local_file_path, "rb") as data:
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(data, overwrite=True)
        return True
    except Exception as e:
        print(f"Error uploading blob: {str(e)}")
        return False

def download_blob(blob_name, local_file_path):
    try:
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        blob_client = container_client.get_blob_client(blob_name)
        with open(local_file_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        return True
    except Exception as e:
        print(f"Error downloading blob: {str(e)}")
        return False

def blob_exists(blob_name):
    blob_client = container_client.get_blob_client(blob_name)
    return blob_client.exists()

def save_json_to_blob(data, blob_name):
    try:
        json_data = json.dumps(data)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(json_data, overwrite=True)
        return True
    except Exception as e:
        print(f"Error saving JSON to blob: {str(e)}")
        return False

def load_json_from_blob(blob_name):
    try:
        blob_client = container_client.get_blob_client(blob_name)
        if not blob_client.exists():
            return {}
        downloaded_blob = blob_client.download_blob()
        json_data = downloaded_blob.readall().decode('utf-8')
        return json.loads(json_data)
    except Exception as e:
        print(f"Error loading JSON from blob: {str(e)}")
        return {}

def list_blobs(prefix=None):
    try:
        blob_list = []
        blobs = container_client.list_blobs(name_starts_with=prefix)
        for blob in blobs:
            blob_list.append(blob.name)
        return blob_list
    except Exception as e:
        print(f"Error listing blobs: {str(e)}")
        return []

def delete_blob(blob_name):
    try:
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        return True
    except Exception as e:
        print(f"Error deleting blob: {str(e)}")
        return False