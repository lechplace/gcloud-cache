from google.cloud import storage
import yaml
import os
from google.api_core.exceptions import Forbidden, NotFound

def create_bucket(bucket_name):
    client = storage.Client()
    bucket = client.create_bucket(bucket_name)
    print(f"Bucket {bucket.name} created")

def ensure_bucket_exists():
    with open('cloud_storage.yaml', 'r') as f:
        config = yaml.safe_load(f)
    bucket_name = config.get('bucket_name')
    credentials_path = config.get('credentials_path')

    if credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

    client = storage.Client()
    try:
        client.get_bucket(bucket_name)
        print(f'Bucket {bucket_name} already exists.')
    except NotFound:
        print(f'Bucket {bucket_name} not found. Creating it...')
        try:
            create_bucket(bucket_name)
        except Forbidden:
            print(f'Error: Permission denied when trying to create the bucket {bucket_name}. Ensure the service account has the correct permissions.')
            raise

ensure_bucket_exists()
