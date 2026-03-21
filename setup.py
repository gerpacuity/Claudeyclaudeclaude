from setuptools import setup, find_packages

setup(
    name="dogvid",
    version="1.0.0",
    description="Automated long-form YouTube video generator for dogs — scientifically optimized",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24.0",
        "Pillow>=10.0.0",
        "google-api-python-client>=2.100.0",
        "google-auth-oauthlib>=1.1.0",
        "google-auth-httplib2>=0.1.1",
        "pyyaml>=6.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "scipy>=1.11.0",
    ],
    entry_points={
        "console_scripts": [
            "dogvid=dogvid.cli:main",
        ],
    },
)
