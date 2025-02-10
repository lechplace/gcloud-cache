import io
import os
import tempfile
import unittest
import zipfile
from gcloud_cache.cache import get_hash_from_zip, deterministic_writestr, serialize_args_to_zip, cache_result

class TestGetHashFromZip(unittest.TestCase):
    def create_zip_buffer(self, entries):
        """
        Create a ZIP archive in a BytesIO buffer.
        :param entries: List of tuples (filename, content)
        :return: BytesIO buffer containing the ZIP archive
        """
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zip_file:
            for filename, content in entries:
                deterministic_writestr(zip_file, filename, content)
        buffer.seek(0)
        return buffer

    def test_same_zip_same_hash(self):
        entries = [
            ('file1.txt', 'Hello World'),
            ('file2.txt', 'Test Content')
        ]
        zip_buffer1 = self.create_zip_buffer(entries)
        zip_buffer2 = self.create_zip_buffer(entries)
        hash1 = get_hash_from_zip(zip_buffer1)
        hash2 = get_hash_from_zip(zip_buffer2)
        self.assertEqual(hash1, hash2, "Hashes should be equal for identical ZIP content")

    def test_different_zip_different_hash(self):
        entries1 = [
            ('file1.txt', 'Hello World'),
            ('file2.txt', 'Test Content')
        ]
        entries2 = [
            ('file1.txt', 'Hello World'),
            ('file2.txt', 'Different Content')
        ]
        zip_buffer1 = self.create_zip_buffer(entries1)
        zip_buffer2 = self.create_zip_buffer(entries2)
        hash1 = get_hash_from_zip(zip_buffer1)
        hash2 = get_hash_from_zip(zip_buffer2)
        self.assertNotEqual(hash1, hash2, "Hashes should differ for different ZIP content")

    def test_binary_content_same_zip_same_hash(self):
        entries = [
            ('binary_file.bin', b'\x00\x01\x02\x03'),
            ('binary_file2.bin', b'\xFF\xEE\xDD\xCC')
        ]
        zip_buffer1 = self.create_zip_buffer(entries)
        zip_buffer2 = self.create_zip_buffer(entries)
        hash1 = get_hash_from_zip(zip_buffer1)
        hash2 = get_hash_from_zip(zip_buffer2)
        self.assertEqual(hash1, hash2, "Hashes for identical binary content should be equal")

    def test_binary_content_different_hash(self):
        entries1 = [
            ('binary_file.bin', b'\x00\x01\x02\x03')
        ]
        entries2 = [
            ('binary_file.bin', b'\x03\x02\x01\x00')
        ]
        zip_buffer1 = self.create_zip_buffer(entries1)
        zip_buffer2 = self.create_zip_buffer(entries2)
        hash1 = get_hash_from_zip(zip_buffer1)
        hash2 = get_hash_from_zip(zip_buffer2)
        self.assertNotEqual(hash1, hash2, "Hashes for different binary content should differ")

    def test_serialize_args_to_zip_save_to_disk(self):
        # Define a dummy function for testing
        def dummy_func(*args, **kwargs):
            # Return value is not used by serialize_args_to_zip,
            # but we include it here to simulate different return types.
            if kwargs.get('binary'):
                return b"dummy_binary_result"
            return "dummy_text_result"

        # Prepare sample arguments (including binary and string types)
        args = (b'byte_arg', "string_arg")
        kwargs = {'kw1': b'byte_kw'}

        # Obtain a BytesIO ZIP archive from serialize_args_to_zip
        zip_buffer = serialize_args_to_zip(dummy_func, args, kwargs)

        # Save the ZIP archive to a temporary file on disk for manual inspection
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            temp_file.write(zip_buffer.getvalue())
            saved_path = temp_file.name

        print(f"ZIP archive saved to: {saved_path}")

        # Verify that the file exists and is non-empty
        self.assertTrue(os.path.exists(saved_path), "The ZIP file was not created on disk.")
        self.assertGreater(os.path.getsize(saved_path), 0, "The ZIP file is empty.")

    def test_dummy_func_return_types(self):
        # Expanded dummy function that returns text or binary based on input
        def dummy_func(*args, **kwargs):
            if kwargs.get('binary'):
                return b"dummy_binary_result"
            return "dummy_text_result"

        # Test when function should return text
        result_text = dummy_func(binary=False)
        self.assertIsInstance(result_text, str, "Expected the dummy function to return a text string")
        self.assertEqual(result_text, "dummy_text_result", "Unexpected text result from dummy function")

        # Test when function should return binary
        result_binary = dummy_func(binary=True)
        self.assertIsInstance(result_binary, bytes, "Expected the dummy function to return binary data")
        self.assertEqual(result_binary, b"dummy_binary_result", "Unexpected binary result from dummy function")

    def test_cache_result_decorator(self):
        # Define a dummy function to be decorated
        @cache_result
        def dummy_func(x, y):
            return x + y

        # Call the function with the same arguments and check if the result is cached
        result1 = dummy_func(1, 2)
        result2 = dummy_func(1, 2)
        self.assertEqual(result1, result2, "The cached result should be the same as the initial result")

        # Call the function with different arguments and check if the result is not cached
        result3 = dummy_func(2, 3)
        self.assertNotEqual(result1, result3, "The result should not be cached for different arguments")

if __name__ == '__main__':
    unittest.main()