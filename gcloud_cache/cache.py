import hashlib
import base64
import zipfile
import io
import inspect
import pickle
from google.cloud import storage
import yaml
import os
from google.api_core.exceptions import Forbidden, NotFound
from functools import wraps
import asyncio

# Load configuration
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

# Pomocnicza funkcja do zapisu deterministycznego do archiwum ZIP
def deterministic_writestr(zip_file, arcname, data):
    info = zipfile.ZipInfo(arcname)
    # Ustalony czas – na przykład 1980-01-01 00:00:00
    info.date_time = (1980, 1, 1, 0, 0, 0)
    # Ustalona metoda kompresji
    info.compress_type = zipfile.ZIP_DEFLATED
    zip_file.writestr(info, data)

def serialize_args(args, kwargs):
    args_filtered = [base64.b64encode(arg).decode('utf-8') if isinstance(arg, bytes) else arg for arg in args]
    kwargs_filtered = {k: (base64.b64encode(v).decode('utf-8') if isinstance(v, bytes) else v) for k, v in kwargs.items()}
    return args_filtered, kwargs_filtered

def serialize_args_to_zip(func, args, kwargs):
    args_filtered, kwargs_filtered = serialize_args(args, kwargs)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        # Dodaj kod funkcji do archiwum z ustalonymi metadanymi
        func_code = inspect.getsource(func)
        deterministic_writestr(zip_file, 'function_code.py', func_code)
        
        for i, arg in enumerate(args_filtered):
            deterministic_writestr(zip_file, f'arg_{i}.txt', str(arg))
        # Sortujemy kwargs, aby kolejność była deterministyczna
        for k, v in sorted(kwargs_filtered.items()):
            deterministic_writestr(zip_file, f'kwarg_{k}.txt', str(v))
    
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
        zip_buffer = io.BytesIO(blob.download_as_bytes())
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            with zip_file.open('result') as result_file:
                data = result_file.read()
                return pickle.loads(data)
    return None

def save_to_cache(hash_key, zip_buffer, result):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"cache/{hash_key}.zip")
    serialized_result = pickle.dumps(result)
    # Zapisz wynik do archiwum z tym samym, deterministycznym zapisem
    with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
        deterministic_writestr(zip_file, 'result', serialized_result)
    zip_buffer.seek(0)
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
        save_to_cache(hash_key, zip_buffer, result)
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
        save_to_cache(hash_key, zip_buffer, result)
        return result
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper