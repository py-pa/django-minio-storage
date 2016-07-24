from setuptools import setup, find_packages

from minio_storage import __version__


version_str = ".".join(str(n) for n in __version__)


setup(
    name="django-minio-storage",
    version=version_str,
    license="MIT",
    description="Django file storage using the minio python client",
    author="Tom Houlé",
    author_email="tom@kafunsho.be",
    url="https://github.com/tomhoule/django-minio-storage",
    packages=['minio_storage'],
    install_requires=[
        "django>=1.9",
        "minio>=1.0.2",
    ],
    extras_require={
        "test": [
            "coverage",
            "requests",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Framework :: Django",
    ],
)
