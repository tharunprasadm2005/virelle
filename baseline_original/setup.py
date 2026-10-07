#!/usr/bin/env python3
"""
Setup script for Recipe Recommendation System
This script helps users set up the project environment and download sample data.
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
from pathlib import Path

def create_directories():
    """Create necessary directories."""
    directories = [
        "data/code/datasets",
        "data/processed", 
        "models",
        "reports"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def install_requirements():
    """Install required Python packages."""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing requirements: {e}")
        return False
    return True

def download_nltk_data():
    """Download required NLTK data."""
    print("Downloading NLTK data...")
    try:
        import nltk
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
        nltk.download('punkt', quiet=True)
        print("✓ NLTK data downloaded successfully")
    except ImportError:
        print("✗ NLTK not installed. Please install requirements first.")
        return False
    except Exception as e:
        print(f"✗ Error downloading NLTK data: {e}")
        return False
    return True

def main():
    """Main setup function."""
    print("=" * 60)
    print("Recipe Recommendation System - Setup")
    print("=" * 60)
    
    # Create directories
    create_directories()
    
    # Install requirements
    if not install_requirements():
        print("Setup failed. Please install requirements manually.")
        return
    
    # Download NLTK data
    download_nltk_data()
    
    print("\n" + "=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Place your datasets in data/code/datasets/:")
    print("   - RAW_recipes.csv")
    print("   - RAW_interactions.csv")
    print("\n2. Run preprocessing:")
    print("   python data/Scripts/preprocess_recipes_and_build_initial_models.py")
    print("\n3. Start the recommendation system:")
    print("   python data/Scripts/recommender_app.py")
    print("\nFor sample data and detailed instructions, see README.md")

if __name__ == "__main__":
    main()
