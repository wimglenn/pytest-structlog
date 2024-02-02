from setuptools import setup

setup(
    name="pytest-structlog",
    version="0.6",
    url="https://github.com/wimglenn/pytest-structlog",
    description="Structured logging assertions",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst; charset=UTF-8",
    author="Wim Glenn",
    author_email="hey@wimglenn.com",
    license="MIT",
    install_requires=["pytest", "structlog"],
    entry_points={"pytest11": ["pytest-structlog=pytest_structlog"]},
    python_requires=">=3.7",
    classifiers=[
        "Framework :: Pytest",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    include_package_data=True,
)
