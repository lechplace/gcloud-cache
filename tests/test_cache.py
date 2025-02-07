import unittest
from gcloud_cache.cache import cache_result

class TestCache(unittest.TestCase):

    @cache_result
    def sample_function(self, param):
        return f'Processed {param}'

    def test_cache(self):
        result1 = self.sample_function('test')
        result2 = self.sample_function('test')
        self.assertEqual(result1, result2)

if __name__ == '__main__':
    unittest.main()
