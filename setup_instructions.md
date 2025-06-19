# Setting Up and Running the Python PC Client on Windows

This guide will walk you through setting up Python, installing necessary libraries, configuring, and running the PC client script on your Windows computer. This script allows your PC to communicate with a WebSocket server running on your Android phone.

## 1. How to Install Python

Python is required to run the script. If you don't have it installed, follow these steps:

*   **Download Python:**
    *   Go to the official Python website: [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
    *   Download the latest stable Windows installer (e.g., "Windows installer (64-bit)").
*   **Run the Installer:**
    *   Open the downloaded installer.
    *   **Important:** Check the box that says **"Add Python to PATH"** or **"Add python.exe to PATH"** at the bottom of the first installer screen. This makes it easier to run Python from the command line.
    *   Click on "Install Now" (or "Customize installation" if you need specific settings, but default is usually fine).
    *   Wait for the installation to complete.
*   **Verify Installation (Optional):**
    *   Open a Command Prompt (search for `cmd` in the Start Menu).
    *   Type `python --version` and press Enter. You should see the installed Python version.
    *   Type `pip --version` and press Enter. You should see the pip version.

## 2. How to Install Required Libraries

The script requires two main libraries: `PyAudio` (for audio processing) and `websockets` (for WebSocket communication).

*   **Open Command Prompt or PowerShell:**
    *   Search for `cmd` or `PowerShell` in the Start Menu and open it.
*   **Install Libraries:**
    *   Copy and paste the following commands one by one and press Enter after each:
        ```bash
        pip install websockets
        pip install pyaudio
        ```

*   **Potential PyAudio Installation Issues on Windows:**
    *   `PyAudio` can sometimes be tricky to install on Windows because it requires C compilation. If you encounter errors during `pip install pyaudio`, try one of the following solutions:
        1.  **Install Microsoft Visual C++ Build Tools:**
            *   Go to the Visual Studio downloads page: [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
            *   Download the "Build Tools for Visual Studio".
            *   During installation, make sure to select "C++ build tools" or "Desktop development with C++".
            *   After installation, restart your command prompt and try `pip install pyaudio` again.
        2.  **Download a Pre-compiled PyAudio Wheel:**
            *   Go to Christoph Gohlke's Unofficial Windows Binaries for Python Extension Packages: [https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)
            *   Download the `.whl` file that matches your Python version (e.g., `cp310` for Python 3.10) and Windows architecture (win_amd64 for 64-bit, win32 for 32-bit).
            *   Open your command prompt, navigate to the directory where you downloaded the wheel file (e.g., `cd Downloads`), and install it using pip:
                ```bash
                pip install PyAudio‑0.2.14‑cp310‑cp310‑win_amd64.whl
                ```
                (Replace the filename with the exact name of the file you downloaded).

## 3. Script Configuration

You need to tell the script the IP address of your Android phone.

*   **Open the Script:**
    *   Open the Python script file (e.g., `pc_client.py`) in a text editor (like Notepad, VS Code, Sublime Text, etc.).
*   **Find and Update `ANDROID_PHONE_IP`:**
    *   Look for a line in the script similar to this:
        ```python
        ANDROID_PHONE_IP = "YOUR_ANDROID_PHONE_IP_HERE"
        ```
    *   Replace `"YOUR_ANDROID_PHONE_IP_HERE"` with the actual IP address of your Android phone on your local network (e.g., `"192.168.1.100"`). You can usually find your phone's IP address in its Wi-Fi settings.
*   **Check `ANDROID_PHONE_PORT` (Optional):**
    *   The script will also have a variable like `ANDROID_PHONE_PORT = 8765` (or similar).
    *   This port number must match the port number the server application is using on your Android phone. Usually, you don't need to change this unless the Android app specifies a different port.

## 4. How to Run the Script

*   **Save the Script:**
    *   If you haven't already, save the Python script with a `.py` extension (e.g., `pc_client.py`) in a folder on your computer (e.g., `C:\Users\YourName\Documents\PythonScripts`).
*   **Open Command Prompt or PowerShell:**
    *   Search for `cmd` or `PowerShell` in the Start Menu and open it.
*   **Navigate to the Script Directory:**
    *   Use the `cd` (change directory) command to go to the folder where you saved the script. For example:
        ```bash
        cd C:\Users\YourName\Documents\PythonScripts
        ```
        (Replace `C:\Users\YourName\Documents\PythonScripts` with the actual path to your script).
*   **Run the Script:**
    *   Type the following command and press Enter:
        ```bash
        python pc_client.py
        ```
        (If you named your script something else, use that name instead of `pc_client.py`).
    *   If everything is set up correctly, the script should start running and attempt to connect to your Android phone.

## 5. General Notes

*   **Android WebSocket Server:** For this script to work, a WebSocket server application **must be running on your Android phone** at the IP address and port you configured in the script. Ensure the Android server app is started and active on your Wi-Fi network.
*   **Firewall:** Your Windows Firewall might ask for permission for Python to access the network. Allow it if prompted.
*   **Network:** Both your PC and your Android phone must be connected to the same local network (e.g., the same Wi-Fi router) for them to communicate.

---

If you encounter any issues, double-check the IP address, port number, and ensure the Android server is running. Review any error messages in the command prompt for clues.
