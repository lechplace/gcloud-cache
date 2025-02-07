# Cloud Cache

Cloud Cache is a Python package for caching data and files in Google Cloud Storage.

## Features

- Store and retrieve cached results from Google Cloud Storage
- Supports JSON and file-based caching
- Easy-to-use decorator for function caching
- Ensures the Cloud Storage bucket exists before usage

## Installation

```sh
pip install gcloud_cache
```

## Usage

### Basic Caching Example

```python
from cloud_cache import cache_result

@cache_result
def expensive_function(param):
    return {"result": f"Processed {param}"}

print(expensive_function("test"))  # First call - runs the function
print(expensive_function("test"))  # Second call - retrieves from cache
```

## Configuration

Cloud Cache requires a configuration file `cloud_storage.yaml`, which should be placed in the `local/` directory.

### Example `local/cloud_storage.yaml`:

```yaml
bucket_name: your-cache-bucket
credentials_path: local/pdf-converter-449809-b8ce9144eafa.json
```

- `bucket_name` - The name of the Google Cloud Storage bucket.
- `credentials_path` - The path to the service account JSON file for authentication.

Ensure that `local/cloud_storage.yaml` is **not** committed to your repository by adding `local/cloud_storage.yaml` to your `.gitignore` file.

## License

MIT License

