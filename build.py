import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """Clean up build directories"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # Clean spec file if it exists
    spec_file = 'ShortChat.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)

def create_virtual_env():
    """Create and activate virtual environment"""
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Determine the pip path based on the OS
    if sys.platform == "win32":
        pip_path = os.path.join("venv", "Scripts", "pip")
        python_path = os.path.join("venv", "Scripts", "python")
    else:
        pip_path = os.path.join("venv", "bin", "pip")
        python_path = os.path.join("venv", "bin", "python")
    
    # Upgrade pip
    subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Install requirements
    print("Installing requirements...")
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    
    return python_path

def create_spec_file(python_path):
    """Create PyInstaller spec file"""
    print("Creating spec file...")
    
    # Base command
    cmd = [
        python_path, "-m", "PyInstaller",
        "--name", "ShortChat",
        "--noconsole",
        "--clean",
    ]
    
    # Add platform-specific options
    if sys.platform == "win32":
        # Check if icon exists
        if os.path.exists("app_icon.ico"):
            cmd.extend(["--icon", "app_icon.ico"])
    elif sys.platform == "darwin":
        # Add macOS specific options if needed
        if os.path.exists("app_icon.icns"):
            cmd.extend(["--icon", "app_icon.icns"])
    
    # Add the main script
    cmd.append("shortchat.py")
    
    # Run PyInstaller
    subprocess.run(cmd, check=True)

def build_executable(python_path):
    """Build the executable"""
    print("Building executable...")
    subprocess.run([python_path, "-m", "PyInstaller", "ShortChat.spec"], check=True)

def main():
    try:
        # Clean previous build files
        clean_build_dirs()
        
        # Create virtual environment and get python path
        python_path = create_virtual_env()
        
        # Create spec file
        create_spec_file(python_path)
        
        # Build executable
        build_executable(python_path)
        
        print("\nBuild completed successfully!")
        print("The executable can be found in the 'dist' directory.")
        
        # Additional platform-specific instructions
        if sys.platform == "darwin":
            print("\nNOTE: On macOS, users will need to:")
            print("1. Grant accessibility permissions to the app")
            print("2. Go to System Preferences -> Security & Privacy -> Privacy -> Accessibility")
            print("3. Add the ShortChat application to the allowed applications")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError during build process: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()