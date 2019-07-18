import os.path
from setuptools import setup, find_packages


def read_file(fn):
    with open(os.path.join(os.path.dirname(__file__), fn)) as f:
        return f.read()
setup(
    name="faastm",
    version="0.0.1",
    description="Experimental one-cell STM for FaaS",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="jang",
    author_email="faastm@ioctl.org",
    license="Apache 2",
    packages=find_packages(),

    entry_points={
        'console_scripts': [],
    },

    include_package_data=True,

    install_requires=[
        'cachetools',
        'dill',
        'fdk',
        'oci >= 2.2.18',
        'requests',
    ],

    tests_require=[
        "pytest",
        "flake8",
        "wheel",
    ],

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Serverless :: Fn",
        "Topic :: Communications :: Chat :: Slack",

    ],
)


