from google.cloud import storage
import json
import yaml
import hashlib
import os
from google.api_core.exceptions import Forbidden, NotFound
from functools import wraps

def serialize_args(args, kwargs):
    args_filtered = [arg for arg in args if not hasattr(arg, '__dict__')]
    kwargs_filtered = {k: v for k, v in kwargs.items() if not hasattr(v, '__dict__')}
    return args_filtered, kwargs_filtered

with open('local/cloud_storage.yaml', 'r') as f:
    config = yaml.safe_load(f)
BUCKET_NAME = config.get('bucket_name')
CREDENTIALS_PATH = config.get('credentials_path')

if CREDENTIALS_PATH:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH

storage_client = storage.Client()

def create_bucket(bucket_name):
    bucket = storage_client.create_bucket(bucket_name)
    print(f"Bucket {bucket.name} created")

def ensure_bucket_exists():
    try:
        bucket = storage_client.get_bucket(BUCKET_NAME)
        print(f'Bucket {BUCKET_NAME} already exists.')
    except NotFound:
        print(f'Bucket {BUCKET_NAME} not found. Creating it...')
        try:
            create_bucket(BUCKET_NAME)
        except Forbidden:
            print(f'Error: Permission denied when trying to create the bucket {BUCKET_NAME}. Ensure the service account has the correct permissions.')
            raise

ensure_bucket_exists()

def get_hash(*args, **kwargs):
    args_filtered, kwargs_filtered = serialize_args(args, kwargs)
    hash_object = hashlib.sha256()
    hash_object.update(json.dumps((args_filtered, kwargs_filtered), sort_keys=True).encode())
    return hash_object.hexdigest()

def get_cached_response(hash_key):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"cache/{hash_key}.json")
    if blob.exists():
        return json.loads(blob.download_as_text())
    return None

def save_to_cache(hash_key, result):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"cache/{hash_key}.json")
    blob.upload_from_string(json.dumps(result), content_type="application/json")

def cache_result(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        hash_key = get_hash(*args, **kwargs)
        cached_response = get_cached_response(hash_key)
        if cached_response is not None:
            print("Using cached result")
            return cached_response
        result = func(*args, **kwargs)
        save_to_cache(hash_key, result)
        return result
    return wrapper
