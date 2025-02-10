from setuptools import setup, find_packages

setup(
    name='gcloud_cache',
    version='0.1.7',
    packages=find_packages(),
    install_requires=[
        'google-cloud-storage',
        'pyyaml',
        'fpdf',
    ],
    author='Your Name',
    author_email='lech.hubicki@gmail.com',
    description='A Python package for caching data and files in Google Cloud Storage.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/lechplace/gcloud-cache',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
