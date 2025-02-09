from google.cloud import storage
import json
import yaml
import hashlib
import os
from google.api_core.exceptions import Forbidden, NotFound
from functools import wraps
import asyncio
import mimetypes
import base64
import zipfile
import io
import inspect

def serialize_args(args, kwargs):
    args_filtered = [base64.b64encode(arg).decode('utf-8') if isinstance(arg, bytes) else arg for arg in args]
    kwargs_filtered = {k: (base64.b64encode(v).decode('utf-8') if isinstance(v, bytes) else v) for k, v in kwargs.items()}
    return args_filtered, kwargs_filtered

try:
    with open('local/cloud_storage.yaml', 'r') as f:
        config = yaml.safe_load(f)
    BUCKET_NAME = config.get('bucket_name')
    CREDENTIALS_PATH = config.get('credentials_path')
except FileNotFoundError:
    print("Plik 'local/cloud_storage.yaml' nie został znaleziony.")
    BUCKET_NAME = None
    CREDENTIALS_PATH = None
except yaml.YAMLError as e:
    print(f"Błąd podczas odczytu pliku YAML: {e}")
    BUCKET_NAME = None
    CREDENTIALS_PATH = None

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
            print(f'Permission denied to create bucket {BUCKET_NAME}.')

def serialize_args_to_zip(func, args, kwargs):
    args_filtered = [base64.b64encode(arg).decode('utf-8') if isinstance(arg, bytes) else arg for arg in args]
    kwargs_filtered = {k: (base64.b64encode(v).decode('utf-8') if isinstance(v, bytes) else v) for k, v in kwargs.items()}
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        # Dodaj kod funkcji do pliku ZIP
        func_code = inspect.getsource(func)
        zip_file.writestr('function_code.py', func_code)
        
        for i, arg in enumerate(args_filtered):
            zip_file.writestr(f'arg_{i}.txt', str(arg))
        for k, v in kwargs_filtered.items():
            zip_file.writestr(f'kwarg_{k}.txt', str(v))
    
    zip_buffer.seek(0)
    return zip_buffer

def get_hash_from_zip(zip_buffer):
    hash_md5 = hashlib.md5()
    hash_md5.update(zip_buffer.read())
    zip_buffer.seek(0)
    return hash_md5.hexdigest()

def get_cached_response(hash_key):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"cache/{hash_key}.zip")
    if blob.exists():
        return blob.download_as_bytes()
    return None

def save_to_cache(hash_key, zip_buffer):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"cache/{hash_key}.zip")
    blob.upload_from_file(zip_buffer, content_type="application/zip")
    print(f"📤 Plik ZIP zapisany w Cloud Storage jako {blob.name}")

def cache_result(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        zip_buffer = serialize_args_to_zip(func, args, kwargs)
        hash_key = get_hash_from_zip(zip_buffer)
        cached_response = get_cached_response(hash_key)
        if cached_response is not None:
            print("Using cached result")
            return cached_response
        result = await func(*args, **kwargs)
        save_to_cache(hash_key, zip_buffer)
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        zip_buffer = serialize_args_to_zip(func, args, kwargs)
        hash_key = get_hash_from_zip(zip_buffer)
        cached_response = get_cached_response(hash_key)
        if cached_response is not None:
            print("Using cached result")
            return cached_response
        result = func(*args, **kwargs)
        save_to_cache(hash_key, zip_buffer)
        return result
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper