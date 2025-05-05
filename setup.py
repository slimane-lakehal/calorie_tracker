#!/usr/bin/env python
"""Setup script for the Calorie Tracker application."""

from setuptools import setup, find_packages

# Main dependencies
REQUIRED = [
    "sqlalchemy>=2.0.0",
    "click>=8.0.0",
    "python-dotenv>=1.0.0",
]

# Optional dependencies
EXTRAS = {
    "dev": [
        "pytest>=6.0.0",
        "pytest-cov>=2.12.0",
        "black>=21.5b2",
        "mypy>=0.812",
    ],
    "viz": [
        "matplotlib>=3.5.0",
        "pandas>=1.3.0",
    ],
}

setup(
    name="calorie_tracker",
    version="0.1.0",
    description="A comprehensive calorie and nutrition tracking application",
    author="Slimane Lakehal",
    author_email="lakehalslimane.com",
    url="https://github.com/slimane-lakehal/calorie_tracker",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    entry_points={
        "console_scripts": [
            "calorie-tracker=calorie_tracker.cli.main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Health and Fitness",
    ],
    keywords="calorie, nutrition, health, fitness, tracking",
    project_urls={
        "Bug Reports": "https://github.com/slimane-lakehal/calorie_tracker/issues",
        "Source": "https://github.com/slimane-lakehal/calorie_tracker",
    },
)

