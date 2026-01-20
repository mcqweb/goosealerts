#!/usr/bin/env python3
"""
Setup script for Kwiff monitor
Creates virtual environment and installs dependencies
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get script directory
    script_dir = Path(__file__).parent.resolve()
    venv_dir = script_dir / ".venv"
    data_dir = script_dir / "data"
    
    print("=" * 60)
    print("Kwiff Monitor Setup")
    print("=" * 60)
    print()
    
    # Create data directory
    if not data_dir.exists():
        print(f"Creating data directory: {data_dir}")
        data_dir.mkdir(parents=True)
    
    # Create virtual environment
    if not venv_dir.exists():
        print(f"Creating virtual environment: {venv_dir}")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print()
    
    # Determine pip path
    if sys.platform == "win32":
        pip_path = venv_dir / "Scripts" / "pip.exe"
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
    
    # Install dependencies
    requirements_file = script_dir / "requirements.txt"
    if requirements_file.exists():
        print("Installing dependencies...")
        subprocess.run([str(pip_path), "install", "-r", str(requirements_file)], check=True)
        print()
    
    print("=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print()
    print("To run the monitor:")
    print(f"  {python_path} match_monitor.py")
    print()

if __name__ == "__main__":
    main()
