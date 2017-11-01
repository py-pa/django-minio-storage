# encoding: utf-8
from setuptools import setup

setup(
    name="django-minio-storage",
    license="MIT",
    use_scm_version=True,
    description="Django file storage using the minio python client",
    author="Tom Houlé",
    author_email="tom@kafunsho.be",
    url="https://github.com/py-pa/django-minio-storage",
    packages=['minio_storage'],
    setup_requires=['setuptools_scm'],
    install_requires=[
        "django>=1.8",
        "minio>=2.2.5",
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
        "Programming Language :: Python :: 3.6",
        "Framework :: Django",
    ],
)
