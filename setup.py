from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="python-roschat-bot",
    version="0.1.1",
    author="Vladislav Dorofeev",
    author_email="vdorofeevdeveloper@gmail.com",
    description="A Python library for creating bots for RosChat platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FF7FSystem/python-roschat-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0,<3.0.0",
        "python-socketio>=5.0.0,<6.0.0",
        "pydantic>=2.0.0,<3.0.0",
        "pydantic-settings>=2.0.0,<3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
            "pylint>=2.0",
        ],
    },
)