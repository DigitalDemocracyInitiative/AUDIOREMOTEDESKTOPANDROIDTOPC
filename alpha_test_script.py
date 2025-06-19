# alpha_test_script.py
#
# Purpose:
# This script serves as an alpha test harness for the PC client application (`script.py`).
# It is designed to programmatically launch the client, simulate a period of interaction
# (or allow it to run for a fixed duration), capture its console output (stdout and stderr),
# and then terminate the client. This facilitates automated or semi-automated testing.
#
# Key Functionalities to be Included:
# 1. Launching the `script.py` (PC client) as a separate process.
# 2. Simulating user interaction by letting the client run for a specified duration.
# 3. Capturing and printing/logging the stdout and stderr from the client process.
# 4. Programmatically terminating the client process.
# 5. (Conceptual) Defining test points or checks based on expected log output or behavior.

import subprocess
import time
import sys # To use the same Python interpreter for the client script
import pyaudio # For audio simulation
import wave    # For WAV file handling
import numpy as np # For generating sine wave
import os      # For checking hypothetical file existence

# --- Test Configuration Constants ---
CONNECTION_WAIT_TIME = 10  # seconds, to wait for client to potentially connect
TEST_DURATION = 15         # seconds, to simulate client running time
TERMINATE_TIMEOUT = 5      # seconds, timeout for process.terminate()
COMMUNICATE_TIMEOUT = 5    # seconds, timeout for process.communicate()

# --- Constants for Generated WAV File ---
TEST_AUDIO_FILENAME = "temp_test_audio.wav"
TEST_AUDIO_DURATION = 2.0  # seconds
TEST_AUDIO_FREQUENCY = 440.0 # Hz (A4 note)
TEST_AUDIO_RATE = 44100
TEST_AUDIO_CHANNELS = 1
TEST_AUDIO_FORMAT = pyaudio.paInt16 # PyAudio format constant

try:
    p_temp_audio_init = pyaudio.PyAudio()
    TEST_AUDIO_SAMPLE_WIDTH = p_temp_audio_init.get_sample_size(TEST_AUDIO_FORMAT)
    p_temp_audio_init.terminate()
except Exception as e_audio_init:
    print(f"ERROR_TEST_SCRIPT: Could not determine PyAudio sample width. Defaulting to 2. Error: {e_audio_init}")
    TEST_AUDIO_SAMPLE_WIDTH = 2 # paInt16 is 2 bytes

# --- Constant for Hypothetical Client Output ---
EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME = "received_audio_segment.wav"

# --- Audio Simulation and Test Verification Functions ---

def simulate_audio_input():
    # Note: This function plays audio through the system's default output.
    # For script.py (PC client) to pick this up as microphone input,
    # a system audio loopback utility (e.g., VB-Cable, LoopBeAudio, Soundflower, or OS-level routing)
    # must be configured to route this output to the client's microphone input device.
    # This script does NOT handle that system-level audio routing.
    print(f"INFO_TEST_SCRIPT: Preparing to simulate audio input by generating and playing {TEST_AUDIO_FILENAME}...")
    p_sim = None
    wf_write_sim = None
    wf_read_sim = None
    stream_out_sim = None
    try:
        p_sim = pyaudio.PyAudio()
        num_samples = int(TEST_AUDIO_DURATION * TEST_AUDIO_RATE)
        t = np.linspace(0, TEST_AUDIO_DURATION, num_samples, endpoint=False)
        sine_wave = 0.5 * np.sin(2 * np.pi * TEST_AUDIO_FREQUENCY * t)
        audio_data_int = (sine_wave * 32767).astype(np.int16)
        audio_bytes = audio_data_int.tobytes()
        wf_write_sim = wave.open(TEST_AUDIO_FILENAME, 'wb')
        wf_write_sim.setnchannels(TEST_AUDIO_CHANNELS)
        wf_write_sim.setsampwidth(TEST_AUDIO_SAMPLE_WIDTH)
        wf_write_sim.setframerate(TEST_AUDIO_RATE)
        wf_write_sim.writeframes(audio_bytes)
        wf_write_sim.close()
        wf_write_sim = None
        print(f"INFO_TEST_SCRIPT: Generated {TEST_AUDIO_FILENAME} for audio simulation.")
        wf_read_sim = wave.open(TEST_AUDIO_FILENAME, 'rb')
        stream_out_sim = p_sim.open(format=p_sim.get_format_from_width(wf_read_sim.getsampwidth()),
                                channels=wf_read_sim.getnchannels(),
                                rate=wf_read_sim.getframerate(),
                                output=True)
        print(f"INFO_TEST_SCRIPT: Playing {TEST_AUDIO_FILENAME} through default output...")
        chunk_size = 1024
        data_frames = wf_read_sim.readframes(chunk_size)
        while len(data_frames) > 0:
            stream_out_sim.write(data_frames)
            data_frames = wf_read_sim.readframes(chunk_size)
        print(f"INFO_TEST_SCRIPT: Finished playing {TEST_AUDIO_FILENAME}.")
    except Exception as e:
        print(f"ERROR_TEST_SCRIPT: Failed to simulate audio input: {e}")
    finally:
        if wf_write_sim: wf_write_sim.close()
        if wf_read_sim: wf_read_sim.close()
        if stream_out_sim:
            if stream_out_sim.is_active(): stream_out_sim.stop_stream()
            stream_out_sim.close()
        if p_sim: p_sim.terminate()
        print("INFO_TEST_SCRIPT: Audio simulation resources cleaned up.")

def verify_test_results(stdout_logs, stderr_logs): # Renamed
    print("\nINFO_TEST_SCRIPT: Verifying test results from captured logs...")

    conceptual_pass = True # Assume pass initially, set to False on failures

    # Log-based checks for client readiness and operation
    client_ready_to_receive_log = "Output audio stream opened for received audio" # From script.py's receive_audio_from_websocket
    websocket_connected_log = "WebSocket connection established." # From script.py's websocket_client_manager

    print("INFO_TEST_SCRIPT: Checking client stdout for key operational messages...")
    if stdout_logs:
        if websocket_connected_log in stdout_logs:
            print(f"  [PASS-Conceptual] Client log indicates: '{websocket_connected_log}'")
        else:
            print(f"  [FAIL-Conceptual] Client log does NOT indicate: '{websocket_connected_log}'")
            conceptual_pass = False

        if client_ready_to_receive_log in stdout_logs:
            print(f"  [PASS-Conceptual] Client log indicates readiness to receive audio: '{client_ready_to_receive_log}'")
        else:
            print(f"  [FAIL-Conceptual] Client log does NOT indicate readiness to receive audio (no '{client_ready_to_receive_log}' log).")
            conceptual_pass = False
    else:
        print("  [INFO] Client STDOUT logs were empty. Key operational messages not found.")
        conceptual_pass = False

    print("INFO_TEST_SCRIPT: Checking client stderr for errors...")
    if stderr_logs:
        print(f"  [WARN] Client STDERR Output was present (review manually):\n{stderr_logs[:300]}{'...' if len(stderr_logs)>300 else ''}")
        # For a stricter test, any stderr output could be considered a failure:
        # conceptual_pass = False
    else:
        print("  [PASS-Conceptual] Client STDERR was empty.")

    # Check for Hypothetical Saved Audio Segment
    print(f"INFO_TEST_SCRIPT: Checking for saved audio segment '{EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME}' (Note: PC client script modification is needed to implement actual saving of received audio).")
    # In a real test, if the client were saving audio:
    # if os.path.exists(EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME):
    #     print(f"  [INFO] Found hypothetical saved audio file: {EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME}.")
    #     # Further checks: load file, check duration, format, content (e.g., compare with expected sine wave).
    #     # Example:
    #     # try:
    #     #     with wave.open(EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME, 'rb') as wf_received:
    #     #         print(f"    Content: Channels={wf_received.getnchannels()}, Rate={wf_received.getframerate()}, Frames={wf_received.getnframes()}")
    #     #         # Add actual comparison logic here if server sends a known pattern
    #     # except Exception as e_wav:
    #     #     print(f"    [ERROR] Could not analyze hypothetical saved WAV: {e_wav}")
    #     #     conceptual_pass = False
    #     # os.remove(EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME) # Clean up test file
    # else:
    #     print(f"  [FAIL-Conceptual] Hypothetical saved audio file NOT found: {EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME}.")
    #     conceptual_pass = False # This part of a real test would fail as client doesn't save.
    print(f"  [INFO] This check is a placeholder. PC Client does not currently save received audio. Assuming '{EXPECTED_CLIENT_AUDIO_OUTPUT_FILENAME}' not found.")


    if conceptual_pass:
        print("[Conceptual] Overall Test Status: Some conceptual checks passed. Further validation needed for actual audio content.")
    else:
        print("[Conceptual] Overall Test Status: One or more conceptual checks FAILED or require review.")

    print("INFO_TEST_SCRIPT: Verification logic complete.")
    # In a real test, this function might return True/False or raise an assertion.
    pass


if __name__ == "__main__":
    CLIENT_SCRIPT_PATH = "script.py"
    command = [sys.executable, CLIENT_SCRIPT_PATH]

    print("INFO_TEST_SCRIPT: Initializing test script...")
    client_process = None

    try:
        print(f"INFO_TEST_SCRIPT: Attempting to launch client script: {' '.join(command)}")
        print("INFO_TEST_SCRIPT: Starting PC client process (script.py)...")
        client_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        print(f"INFO_TEST_SCRIPT: PC client process started with PID: {client_process.pid}")

        print(f"INFO_TEST_SCRIPT: Waiting {CONNECTION_WAIT_TIME}s for client to initialize (conceptual connection time)...")
        time.sleep(CONNECTION_WAIT_TIME)

        print("INFO_TEST_SCRIPT: Attempting to simulate audio input...")
        simulate_audio_input()
        print("INFO_TEST_SCRIPT: Audio input simulation step complete.")

        print(f"INFO_TEST_SCRIPT: Main test duration: Allowing client to run for {TEST_DURATION}s...")
        time.sleep(TEST_DURATION)
        print("INFO_TEST_SCRIPT: Main test duration complete.")

        print("INFO_TEST_SCRIPT: Attempting to terminate PC client process...")
        if client_process.poll() is None:
            client_process.terminate()
            try:
                client_process.wait(timeout=TERMINATE_TIMEOUT)
                print("INFO_TEST_SCRIPT: Client process terminated gracefully.")
            except subprocess.TimeoutExpired:
                print(f"INFO_TEST_SCRIPT: Client process did not terminate gracefully within {TERMINATE_TIMEOUT}s, killing...")
                client_process.kill()
                try:
                    client_process.wait(timeout=TERMINATE_TIMEOUT)
                    print("INFO_TEST_SCRIPT: Client process killed.")
                except subprocess.TimeoutExpired:
                    print("INFO_TEST_SCRIPT: Client process failed to die even after kill.")
            print("INFO_TEST_SCRIPT: PC client process termination attempt finished.")
        else:
            print("INFO_TEST_SCRIPT: Client process already terminated before explicit termination attempt.")

        print("INFO_TEST_SCRIPT: Capturing final stdout/stderr from PC client...")
        stdout_output = ""
        stderr_output = ""
        try:
            stdout_output, stderr_output = client_process.communicate(timeout=COMMUNICATE_TIMEOUT)
            print("INFO_TEST_SCRIPT: Log capture via communicate() successful.")
        except subprocess.TimeoutExpired:
            print(f"INFO_TEST_SCRIPT: Timeout during final log capture with communicate(timeout={COMMUNICATE_TIMEOUT}).")
            if client_process.poll() is None:
                print("INFO_TEST_SCRIPT: Forcing kill due to communicate() timeout.")
                client_process.kill()
                try:
                    stdout_output, stderr_output = client_process.communicate(timeout=1)
                except:
                    pass
        except Exception as e:
            print(f"INFO_TEST_SCRIPT: Error during communicate(): {e}")
        print("INFO_TEST_SCRIPT: Log capture complete.")

        print("\n--- Client STDOUT ---")
        print(stdout_output if stdout_output else "<No stdout captured or already read>")
        print("--- End Client STDOUT ---\n")

        print("--- Client STDERR ---")
        print(stderr_output if stderr_output else "<No stderr captured or already read>")
        print("--- End Client STDERR ---\n")

        if client_process.returncode is None:
            client_process.poll()
        print(f"INFO_TEST_SCRIPT: Client exited with return code: {client_process.returncode}")

        print("INFO_TEST_SCRIPT: Starting test results verification...") # Changed from conceptual
        verify_test_results(stdout_output, stderr_output) # Call renamed function
        print("INFO_TEST_SCRIPT: Test results verification complete.") # Changed from conceptual

    except FileNotFoundError:
        print(f"INFO_TEST_SCRIPT: Error - Client script '{CLIENT_SCRIPT_PATH}' not found. Make sure path is correct.")
    except Exception as e:
        print(f"INFO_TEST_SCRIPT: Error during test script execution: {e}")
        if client_process and client_process.poll() is None:
            print("INFO_TEST_SCRIPT: Test script error. Killing client...")
            client_process.kill()
            try: client_process.wait(timeout=TERMINATE_TIMEOUT)
            except subprocess.TimeoutExpired: print("INFO_TEST_SCRIPT: Client kill attempt after test script error timed out.")
            print("INFO_TEST_SCRIPT: Client killed due to test script error.")
    finally:
        if client_process and hasattr(client_process, 'pid') and client_process.poll() is None:
            print("INFO_TEST_SCRIPT: Test script ending. Final client kill check.")
            client_process.kill()
            try: client_process.wait(timeout=TERMINATE_TIMEOUT)
            except subprocess.TimeoutExpired: print(f"INFO_TEST_SCRIPT: Client PID {client_process.pid} very sticky on final kill.")
            print("INFO_TEST_SCRIPT: Client forcefully killed in finally if it was still running.")

    print("\nINFO_TEST_SCRIPT: Test script execution finished.")
