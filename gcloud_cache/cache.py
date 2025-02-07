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

def serialize_args(args, kwargs):
    args_filtered = [base64.b64encode(arg).decode('utf-8') if isinstance(arg, bytes) else arg for arg in args]
    kwargs_filtered = {k: (base64.b64encode(v).decode('utf-8') if isinstance(v, bytes) else v) for k, v in kwargs.items()}
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
    """Pobiera wynik z Google Cloud Storage, obsługując pliki binarne i JSON."""
    bucket = storage_client.bucket(BUCKET_NAME)
    
    # Sprawdź, czy istnieje plik binarny (plik .bin)
    blob_bin = bucket.blob(f"cache/{hash_key}.bin")
    if blob_bin.exists():
        # Pobieramy dane binarne bezpośrednio
        return blob_bin.download_as_bytes()

    # Sprawdź, czy istnieje plik JSON
    blob_json = bucket.blob(f"cache/{hash_key}.json")
    if blob_json.exists():
        return json.loads(blob_json.download_as_text())

    return None  # Brak danych w cache

def save_to_cache(hash_key, result):
    """Zapisuje wynik w Google Cloud Storage jako JSON lub plik binarny."""
    bucket = storage_client.bucket(BUCKET_NAME)

    if isinstance(result, bytes):  # Jeśli wynik to dane binarne
        blob = bucket.blob(f"cache/{hash_key}.bin")
        blob.upload_from_string(result, content_type="application/octet-stream")
        print(f"📤 Dane binarne zapisane w Cloud Storage jako {blob.name}")
    elif isinstance(result, str) and os.path.exists(result):  # Jeśli wynik to plik
        # Pobierz MIME na podstawie rozszerzenia pliku
        mime_type, _ = mimetypes.guess_type(result)
        mime_type = mime_type or "application/octet-stream"

        blob = bucket.blob(f"cache/{hash_key}.bin")
        blob.upload_from_filename(result, content_type=mime_type)
        
        print(f"📤 Plik {result} zapisany w Cloud Storage jako {blob.name} ({mime_type})")
    else:
        blob = bucket.blob(f"cache/{hash_key}.json")
        blob.upload_from_string(json.dumps(result), content_type="application/json")
        print(f"✅ Dane JSON zapisane w Cloud Storage jako {blob.name}")

def cache_result(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Filtruj argumenty, aby usunąć nieserializowalne obiekty
        filtered_args = [arg for arg in args if isinstance(arg, (str, int, float, bytes, list, dict, tuple))]
        filtered_kwargs = {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bytes, list, dict, tuple))}
        
        hash_key = get_hash(*filtered_args, **filtered_kwargs)
        cached_response = get_cached_response(hash_key)
        if cached_response is not None:
            print("Using cached result")
            return cached_response
        result = await func(*args, **kwargs)
        save_to_cache(hash_key, result)
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        # Filtruj argumenty, aby usunąć nieserializowalne obiekty
        filtered_args = [arg for arg in args if isinstance(arg, (str, int, float, bytes, list, dict, tuple))]
        filtered_kwargs = {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bytes, list, dict, tuple))}
        
        hash_key = get_hash(*filtered_args, **filtered_kwargs)
        cached_response = get_cached_response(hash_key)
        if cached_response is not None:
            print("Using cached result")
            return cached_response
        result = func(*args, **kwargs)
        save_to_cache(hash_key, result)
        return result
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper