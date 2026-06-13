import os
import sys
import subprocess
import platform

def main():
    # Change working directory to the script's directory to ensure relative paths resolve correctly
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("--- Dashboard Launcher ---")
    
    # 1. Verify virtual environment
    venv_dir = os.path.join(script_dir, ".venv")
    if not os.path.isdir(venv_dir):
        print("Creating virtual environment (.venv)...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print("Virtual environment created successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to create virtual environment: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

    # 2. Determine paths to python and pip within the venv
    if platform.system() == "Windows":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
        venv_pip = os.path.join(venv_dir, "bin", "pip")

    # Double check executables exist, otherwise recreate venv
    if not os.path.exists(venv_python) or not os.path.exists(venv_pip):
        print("Error: Virtual environment executables not found. Recreating...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "--clear", ".venv"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to recreate virtual environment: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

    # 3. Install/update dependencies
    print("Verifying and installing dependencies...")
    try:
        # Upgrade pip first
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Install requirements
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("Dependencies verified successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Warning/Error during dependency installation: {e}")
        print("Attempting to run dashboard anyway...")

    # 4. Start Streamlit app
    print("Starting Streamlit Dashboard...")
    try:
        # Run streamlit as a module to avoid entrypoint script path resolution issues
        subprocess.run([venv_python, "-m", "streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\nDashboard stopped by user.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting dashboard: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
