# encoding: utf-8
from setuptools import setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name="django-minio-storage",
    license="MIT",
    use_scm_version={
        "write_to": "minio_storage/version.py",
        "write_to_template": '__version__ = "{version}"\n',
        "tag_regex": r"^v(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$",
    },
    description="Django file storage using the minio python client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Thomas Frössman",
    author_email="thomasf@jossystem.se",
    url="https://github.com/py-pa/django-minio-storage",
    packages=[
        "minio_storage",
        "minio_storage/management/",
        "minio_storage/management/commands/",
    ],
    setup_requires=["setuptools_scm"],
    python_requires=">=3.8",
    install_requires=["django>=3.2", "minio>=7.1.12"],
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
