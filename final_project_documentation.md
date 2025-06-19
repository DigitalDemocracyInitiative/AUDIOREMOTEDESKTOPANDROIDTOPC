# Project Documentation: PC Client and Android WebSocket Server

This document provides a comprehensive overview of the PC client application and the requirements for its companion Android WebSocket server.

# 1. PC Client Application Analysis

## 1.1. Identified Dependencies

The Python PC client script requires the following non-standard libraries:

-   **PyAudio:** For capturing and playing audio.
    *   Installation: `pip install PyAudio`
-   **websockets:** For WebSocket communication with the Android server.
    *   Installation: `pip install websockets`

*(Note: The PC client script provided for review also imports `tkinter`, `asyncio`, `json`, `threading`, and `time`, which are part of the Python standard library.)*

## 1.2. Setup and Execution Instructions (Windows PC)

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
    *   If you haven't already, save the Python script with a `.py` extension (e.g., `pc_client.py`) in a folder on your computer (e.g., `C:\\Users\\YourName\\Documents\\PythonScripts`).
*   **Open Command Prompt or PowerShell:**
    *   Search for `cmd` or `PowerShell` in the Start Menu and open it.
*   **Navigate to the Script Directory:**
    *   Use the `cd` (change directory) command to go to the folder where you saved the script. For example:
        ```bash
        cd C:\\Users\\YourName\\Documents\\PythonScripts
        ```
        (Replace `C:\\Users\\YourName\\Documents\\PythonScripts` with the actual path to your script).
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


## 1.3. Suggestions for Error Handling and Robustness

### Suggestions for Error Handling and Robustness

Here's a list of specific suggestions for improving error handling and robustness in the PC client Python script:

#### 1. WebSocket Connection Issues

*   **Retry Strategy:** Implement an exponential backoff strategy for retries in `websocket_client_manager` (e.g., 1s, 2s, 4s, up to 30-60s) instead of a fixed 5-second delay. Reset on successful connection.
*   **Specific User Error Messages (GUI):**
    *   Update `status_label` via `schedule_gui_update` with specific reasons for connection failures:
        *   Connection refused / Host not found (from `ConnectionRefusedError`, `OSError`): "Connection refused by server." or "Host not found. Check IP."
        *   Connection timeout (from `asyncio.TimeoutError`): "Connection attempt timed out."
        *   Invalid server URI (from `websockets.exceptions.InvalidURI`): "Invalid server address format. Check IP." (Add explicit handling for this).
        *   Handshake failure (from `websockets.exceptions.InvalidHandshake`): "WebSocket handshake failed (server issue?)."
*   **GUI Notification for Repeated Failures:** After several (e.g., 3-5) consecutive failed retries, update GUI to indicate a persistent problem (e.g., "Connection failed multiple times. Please check server IP/port and network.") and consider pausing retries or using a much longer interval.
*   **Handle `InvalidURI`:** Add specific `try-except` for `websockets.exceptions.InvalidURI` before attempting `websockets.connect()` if the IP/port format is suspect.

#### 2. PyAudio Issues

*   **Specific `p.open()` Error Handling & GUI Feedback:**
    *   Catch specific `IOError`/`OSError` from `p.open()` for both input and output streams.
    *   Inspect error messages/codes to provide specific GUI feedback via `schedule_gui_update`: "Status: Error - No microphone found," "Status: Error - Microphone in use," or "Status: Error - Output audio device issue."
    *   If input/output stream opening is critical and fails, ensure `app_running` is set to `False` and GUI reflects that operation cannot continue.
*   **`audio_callback` Robustness:**
    *   If errors putting data into `audio_buffer_queue` are persistent, update GUI or attempt to stop recording.
    *   Log callback errors using the `logging` module.
    *   The `else` case for `if loop.is_running()` ("Event loop not running...") should be a critical logged error.
*   **Device Availability Check (Optional Enhancement):** Before starting, consider iterating `p.get_device_count()` and `p.get_device_info_by_index(i)` to check for suitable input/output devices and provide early user feedback if none are found.

#### 3. Asyncio Task Management

*   **Exception Propagation from Tasks:**
    *   For unexpected persistent exceptions in `send_audio_to_websocket` or `receive_audio_from_websocket` (not just `ConnectionClosed`), consider if they should also set `websocket_connection = None` to trigger a full reconnection cycle by the manager, rather than just sleeping and retrying internally.
*   **Graceful Task Cancellation:**
    *   Ensure `asyncio.CancelledError` is handled gracefully within `send_audio_to_websocket` and `receive_audio_from_websocket` if they manage resources needing explicit release beyond what the manager or their `finally` blocks already do. (The output stream `finally` is a good example).
*   **Awaiting `manager_task_future`:** In `run_audio_and_websocket_loop`, make the awaiting of `manager_task_future` more explicit during shutdown. The manager should respond to `app_running = False`. Ensure its completion or cancellation is properly handled.

#### 4. Graceful Shutdown

*   **Coordinated Shutdown in `on_closing`:**
    1.  Set `app_running = False`.
    2.  Explicitly wait for the `run_audio_and_websocket_loop` thread to finish (e.g., using `thread.join()`). This thread's `finally` block is responsible for its PyAudio stream, asyncio loop, and tasks.
    3.  After the thread has joined, then call `p.terminate()` and `root.destroy()`.
    4.  Update GUI to reflect "Status: Shutting down..." during this process.
*   **`stop_recording` Button State:** Ensure `start_button` is re-enabled (via `schedule_gui_update`) only after all resources are confirmed released (e.g., at the end of `run_audio_and_websocket_loop`'s `finally` block).
*   **Single `p.terminate()`:** Ensure `pyaudio.PyAudio().terminate()` is called only once globally, after all PyAudio streams are definitively closed. This could be at the end of `on_closing` after threads have been joined.
*   **`audio_callback` during Shutdown:** The `if loop.is_running():` check is good. If the loop is shutting down, `run_coroutine_threadsafe` might fail; ensure this is handled or that `recording` is `False` well before the loop stops.

#### 5. User Feedback (GUI Updates)

*   **Thread-Safe GUI Updates:** Consistently use `schedule_gui_update(lambda: ...)` for *all* GUI modifications (status labels, button states) that originate from background threads or asyncio tasks.
*   **Granular Status Updates:** Provide more detailed status updates for all stages: "Connecting to {IP}...", "Connection failed: {Reason}", "Reconnecting (attempt {X})...", "Streaming active.", "Microphone error: {Reason}", "Output device error: {Reason}", "Stopping recording...", "Shutting down application...", "Ready."

#### 6. Logging

*   **Implement `logging` Module:**
    *   Replace `print()` statements for error reporting and significant events with `logging.info()`, `logging.warning()`, `logging.error()`, and `logging.exception()`.
    *   Configure a logger (e.g., basic console/file logger with timestamps, levels, thread names).
    *   Log errors in `audio_callback`, WebSocket tasks, connection attempts, stream events, and thread/task lifecycles.
    *   Use `logging.exception()` or `exc_info=True` for error logs to include stack traces.

# 2. Companion Android WebSocket Server Requirements

# Android WebSocket Server Requirements for PC Client Integration

This document outlines the fundamental requirements for an Android WebSocket server designed to interact with the provided Python PC client script. The primary goal is to stream audio from the PC to a conceptual "Gemini Live" service on the Android device and stream Gemini Live's audio output back to the PC.

## 1. Server Type

*   **WebSocket Server:** The Android application must implement a WebSocket server.
*   **Binary Data Handling:** The server must be capable of receiving and sending raw binary data, as this will be the format for the audio chunks. It should not expect text-based WebSocket messages for the audio stream.

## 2. Core Responsibilities

The Android WebSocket server has several key responsibilities:

### a. Receiving Audio from PC Client

*   **Accept Connections:** Listen for incoming WebSocket connections from the PC client on the configured IP address and port.
*   **Receive Binary Audio Data:** Once a connection is established, the server must continuously receive binary audio data chunks sent by the PC client. These chunks represent the audio captured from the PC's microphone.

### b. Feeding Audio to "Gemini Live" (Conceptual & Speculative)

This is the most challenging and conceptual part, as a direct public API for streaming audio into a service like "Gemini Live" is not assumed to exist. The server would need to employ a strategy to make the received audio available to Gemini Live. Potential conceptual approaches include:

*   **Accessibility Services:**
    *   If Gemini Live utilizes Android's accessibility framework for audio input or can be made to listen to an audio source made available via accessibility features, this could be a path. This is highly dependent on Gemini Live's specific implementation.
*   **Virtual Microphone/Audio Routing:**
    *   **OS Level (Highly Speculative/Complex):** Attempting to create a virtual microphone device or reroute audio at the Android OS level so that Gemini Live (or the whole system) picks up the audio streamed from the PC. This typically requires low-level Android OS modifications or features, possibly root access, and is not generally feasible for standard app development.
    *   **App-Specific Integration:** If Gemini Live itself offered a mechanism (e.g., an Intent, API, or background service) to accept an audio stream from another app, this would be ideal, but is unknown.
*   **URI Schemes/Intents (Less Likely for Raw Streams):**
    *   While typically used for discrete actions or files, investigate if Gemini Live exposes any specific Android Intents or URI schemes that could be triggered to process audio data. This is unlikely to support a continuous raw audio stream.

**Acknowledgement:** The method for successfully feeding live audio into a third-party application like "Gemini Live" without a dedicated API is highly speculative and presents significant technical hurdles. The chosen method would be the core innovation of the Android server app.

### c. Capturing "Gemini Live's" Audio Output

The server must capture the audio output generated by Gemini Live in response to the input it received (or any other audio Gemini Live produces). Potential Android mechanisms include:

*   **`MediaProjection` API:**
    *   This API (Android 5.0 Lollipop and later) allows capturing the device's screen and/or system audio output.
    *   Requires explicit user permission each time the capture starts.
    *   The server could use `MediaProjection` to capture all audio played by the system (or a specific app if targeting improves in newer Android versions) while Gemini Live is active.
*   **Accessibility Services:**
    *   If Gemini Live's audio output is routed in a way that accessibility services can intercept or record it (less common for raw audio, more for UI events with sound).
*   **Internal Audio Recording (Limited & Problematic):**
    *   Some Android versions or OEM customizations might offer ways to record "internal" or "system" audio. These are often restricted, may require special permissions, root access, or might not work reliably across all devices.
    *   Privacy implications are significant here.
*   **Loopback Recording (with Virtual Audio Device - Highly Complex):**
    *   Conceptually similar to virtual microphone input, creating a loopback audio output that Gemini Live uses and the server records from. Extremely complex and likely requires OS-level capabilities.

**Acknowledgement:** Capturing audio output from another app also has significant challenges, primarily related to user permissions (`MediaProjection`), system limitations, and privacy concerns.

### d. Sending Captured Audio to PC Client

*   **Binary Audio Data Transmission:** The server must take the captured audio data (from Gemini Live's output) and send it back to the connected PC client via the active WebSocket connection.
*   **Continuous Streaming:** This should be done in chunks, similar to how it's received, to enable real-time (or near real-time) playback on the PC.

## 3. Connection Parameters

*   **Listening Port:** The WebSocket server must listen on port `8765` (TCP), as this is the default port configured in the PC client script. (Allowing user configuration of this port on both client and server would be a good enhancement).
*   **Network Discovery:** The server must be running on a device (the Android phone) connected to the same local area network (LAN) as the PC client. The PC client will connect to the server using the Android phone's IP address on this network.

## 4. Data Handling

*   **Raw Binary Audio:** All audio data transmitted between the PC client and the Android server (in both directions) is raw binary audio bytes.
*   **No Audio Format Interpretation (by Server for WebSocket):** The WebSocket server itself does not necessarily need to interpret the deep specifics of the audio format (e.g., sample rate (44100 Hz), channels (mono), format (16-bit PCM) as defined in the PC client). Its primary role is to act as a conduit for these bytes.
    *   The PC client is responsible for encoding its microphone audio into this format.
    *   The conceptual "Gemini Live" interaction layer on Android would need to handle or be configured for this format for input.
    *   The audio capture mechanism on Android for Gemini Live's output will determine the format of the captured audio. The server might need to perform resampling or reformatting if this captured format doesn't match what the PC client expects (though the PC client is also somewhat generic in its output playback). For simplicity, it's assumed the goal is to send back audio in a compatible format, ideally the same as the input.

## 5. Error Handling & Resilience (Basic Expectations)

*   **Connection Stability:** The server should be ableto handle multiple connection attempts from a client without crashing.
*   **Graceful Disconnections:** If a PC client disconnects, the server should handle this gracefully, cleaning up resources associated with that connection and be ready to accept new connections.
*   **Resource Management:** Properly manage resources like network sockets, audio buffers, and any resources used for interacting with "Gemini Live" or audio capture.
*   **Logging:** Implement basic logging on the Android server side (e.g., using Android's Logcat) to record server status, connection events, data transmission indicators, and any errors encountered. This is crucial for debugging.
*   **Permissions Handling:** If using APIs like `MediaProjection`, the server app must correctly handle the permission request flow with the user.

This outline provides a foundational set of requirements. The actual implementation, especially parts (2b) and (2c) involving "Gemini Live," will require significant research and development based on the capabilities and constraints of the Android OS and the (hypothetical) "Gemini Live" application.

# 3. Cross-Platform Considerations

This section discusses considerations for running the PC client and Android server scripts on different operating systems.

## 3.1. PC Client (`script.py`)

The PC client script is written in Python and utilizes several libraries. Its cross-platform compatibility is as follows:

*   **Core Python Libraries:**
    *   `asyncio`, `websockets`, `tkinter` (standard GUI library), `json` (standard), `threading` (standard), and `time` (standard) are generally cross-platform and should work on Windows, macOS, and Linux without major issues, provided a compatible Python version is installed.

*   **PyAudio:**
    *   **Cross-Platform Aim:** PyAudio is designed to be a cross-platform audio I/O library. It acts as a Python wrapper around the native PortAudio library.
    *   **Underlying APIs:**
        *   **Windows:** PyAudio typically uses MME, DirectSound, WASAPI, or other Windows audio APIs via PortAudio. Installation on Windows can sometimes require Microsoft Visual C++ Build Tools or pre-compiled wheels, as detailed in the setup instructions.
        *   **macOS:** PyAudio generally uses Core Audio through PortAudio. Users might need to install PortAudio using a package manager like Homebrew (e.g., `brew install portaudio`). Pip installation of PyAudio might then link against this.
        *   **Linux:** PyAudio uses ALSA or PulseAudio, again via PortAudio. Users typically need to install development packages for PortAudio and Python (e.g., `sudo apt-get install portaudio19-dev python3-pyaudio` or `sudo apt-get install libasound2-dev portaudio19-dev python3-pyaudio` depending on the distribution).
    *   **Dependencies:** The main challenge is ensuring the underlying PortAudio library and any necessary audio system development files are correctly installed and accessible when PyAudio is compiled or installed.

## 3.2. Android Server (`android_server.py`)

Running the Python-based WebSocket server on an Android device presents unique considerations:

*   **Python on Android:**
    *   The primary way to run Python scripts like this on Android is through environments such as **Termux**. Termux provides a Linux-like terminal environment and allows installation of Python and various packages.

*   **`websockets` and `numpy` Libraries:**
    *   These libraries are generally well-supported. `websockets` is pure Python (with some C extensions for performance, which usually compile fine). `numpy` has pre-built wheels for many architectures, including those used by Android devices (ARM), making installation via pip in Termux feasible.

*   **`pyaudio` on Android/Termux:**
    *   **Complexity:** This is the most challenging dependency for the Android server. Running PyAudio (and its PortAudio C library dependency) within Termux can be complex and sometimes unreliable.
    *   **Installation in Termux:**
        *   Users will typically need to install `portaudio` using Termux's package manager (e.g., `pkg install portaudio` or `apt install portaudio19-dev`).
        *   Additional build tools and dependencies might be required for `pip install pyaudio` to compile successfully (e.g., `pkg install python-dev libffi-dev clang build-essential`).
    *   **Audio Hardware Access:** Direct audio playback capabilities via PyAudio in Termux depend heavily on:
        *   The Android version and specific device manufacturer.
        *   Termux's ability to access the Android audio hardware and system mixer.
        *   Permissions granted to Termux.
        *   The audio might not always route as expected, or latency could be an issue.
    *   **Alternative for Production:** For a robust, production-ready audio application on Android, native Android development using Java or Kotlin with Android's native audio APIs (like `AudioTrack` for playback, `AudioRecord` for recording) is generally the recommended approach. PyAudio in Termux can be suitable for prototyping, personal projects, or controlled testing environments but might lack the stability and seamless integration of a native solution.

In summary, while the Python scripts aim for conceptual portability, the audio components (PyAudio) require careful attention to system-level dependencies and environment capabilities, especially when targeting Android via Termux.
