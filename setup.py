# encoding: utf-8
from setuptools import setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name="django-minio-storage",
    license="MIT",
    use_scm_version=True,
    description="Django file storage using the minio python client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Tom Houlé",
    author_email="tom@kafunsho.be",
    url="https://github.com/py-pa/django-minio-storage",
    packages=[
        "minio_storage",
        "minio_storage/management/",
        "minio_storage/management/commands/",
    ],
    setup_requires=["setuptools_scm"],
    install_requires=["django>=1.11", "minio>=4.0.21,<7"],
    extras_require={"test": ["coverage", "requests"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Framework :: Django",
    ],
)
