import tkinter as tk
import pyaudio
import asyncio
import websockets
# import json # Not used currently
import threading
import time
import argparse
import wave

# --- Configuration ---
ANDROID_PHONE_IP = "YOUR_ANDROID_PHONE_IP_ADDRESS"
ANDROID_PHONE_PORT = 8765

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# --- Global Variables ---
CLIENT_LOG_PREFIX = "CLIENT_LOG:" # For consistent logging
audio_stream = None
websocket_connection = None
recording = False
app_running = True
args = None # Parsed command-line arguments

# Global PyAudio instance, initialized once and terminated once.
p = pyaudio.PyAudio()

# --- GUI Elements (global for easy access by update functions) ---
root = tk.Tk()
root.title("PC Audio Client")
root.geometry("400x250")

# --- Thread-Safe GUI Update Function ---
def schedule_gui_update(root_tk_instance, callable_to_run, **kwargs_for_callable):
    """Schedules a callable for execution on the main Tkinter thread."""
    if root_tk_instance and root_tk_instance.winfo_exists():
        root_tk_instance.after(0, lambda: callable_to_run(**kwargs_for_callable))
    else:
        if root_tk_instance and root_tk_instance.winfo_exists() and app_running:
             print(f"{CLIENT_LOG_PREFIX} [WARN] GUI update scheduled but root window is gone or invalid.")

status_label = tk.Label(root, text="Status: Ready", font=("Arial", 12))
status_label.pack(pady=10)

# --- Helper function to save audio data to WAV file ---
def save_buffered_audio_to_wav(filename, audio_data_bytes, channels, sample_width, rate):
    """Saves a byte string of audio data to a WAV file."""
    global args, root, status_label, CLIENT_LOG_PREFIX
    try:
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(audio_data_bytes)
        wf.close()
        duration_text = f"~{args.save_duration}s" if args and hasattr(args, 'save_duration') else "segment"
        print(f"{CLIENT_LOG_PREFIX} [INFO] Successfully saved {duration_text} of received audio to {filename}")
        base_filename = filename.split('/')[-1].split('\\')[-1] # Show only filename in GUI
        schedule_gui_update(root, status_label.config, text=f"Status: Saved audio to {base_filename}")
    except Exception as e:
        base_filename = filename.split('/')[-1].split('\\')[-1]
        print(f"{CLIENT_LOG_PREFIX} [ERROR] Failed to save received audio to {filename}: {e}")
        schedule_gui_update(root, status_label.config, text=f"Status: Error saving to {base_filename}")

# --- GUI Control Functions ---
def start_recording_wrapper():
    """Handles 'Start Streaming' button click: sets flags and starts the main background thread."""
    global recording, app_running, root, status_label, start_button, stop_button, CLIENT_LOG_PREFIX
    print(f"{CLIENT_LOG_PREFIX} [INFO] Start recording/streaming requested.")
    if recording:
        print(f"{CLIENT_LOG_PREFIX} [DEBUG] Start request ignored, already recording.")
        return

    recording = True
    app_running = True

    schedule_gui_update(root, status_label.config, text="Status: Initializing...")
    schedule_gui_update(root, start_button.config, state=tk.DISABLED)
    schedule_gui_update(root, stop_button.config, state=tk.NORMAL)

    # Main operations (audio and WebSocket) run in a separate thread to keep GUI responsive.
    threading.Thread(target=run_audio_and_websocket_loop, daemon=True).start()

def stop_recording_wrapper():
    """Handles 'Stop Streaming' button click: sets flags to terminate background operations."""
    global recording, app_running, root, status_label, stop_button, CLIENT_LOG_PREFIX
    print(f"{CLIENT_LOG_PREFIX} [INFO] Stop recording/streaming requested.")

    if not app_running and not recording:
        print(f"{CLIENT_LOG_PREFIX} [DEBUG] Stop request ignored, already stopped or stopping.")
        return

    schedule_gui_update(root, status_label.config, text="Status: Stopping...")
    schedule_gui_update(root, stop_button.config, state=tk.DISABLED)

    recording = False
    app_running = False


# --- Audio Processing and WebSocket Communication (executed in a background thread) ---
def audio_callback(in_data, frame_count, time_info, status_flags):
    """PyAudio callback: Called by PortAudio thread when new audio data is available."""
    global audio_buffer_queue, CLIENT_LOG_PREFIX
    if recording and app_running:
        try:
            # Get the asyncio event loop of the background thread.
            loop = getattr(threading.current_thread(), 'websocket_loop', None)
            if loop and loop.is_running():
                # Thread-safely put audio data into the asyncio queue.
                asyncio.run_coroutine_threadsafe(audio_buffer_queue.put(in_data), loop)
            # else: # Can be noisy during shutdown
                # print(f"{CLIENT_LOG_PREFIX} [DEBUG] Audio callback: Loop not running/found.")
        except Exception as e:
            print(f"{CLIENT_LOG_PREFIX} [ERROR] Audio callback error: {e}")
        return (in_data, pyaudio.paContinue) # Tell PyAudio to continue streaming.
    else:
        return (None, pyaudio.paComplete) # Tell PyAudio to stop the stream.

async def send_audio_to_websocket():
    """Coroutine: Gets audio from queue and sends it over WebSocket."""
    global websocket_connection, recording, app_running, root, status_label, audio_buffer_queue, CLIENT_LOG_PREFIX
    print(f"{CLIENT_LOG_PREFIX} [INFO] Send audio task started.")
    try:
        while app_running:
            if websocket_connection and recording:
                try:
                    data = await asyncio.wait_for(audio_buffer_queue.get(), timeout=0.1)
                    if data:
                        await websocket_connection.send(data)
                        print(f"{CLIENT_LOG_PREFIX} [DEBUG] Sent audio chunk of {len(data)} bytes.")
                    audio_buffer_queue.task_done()
                except asyncio.TimeoutError: # Normal if queue is empty
                    continue
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"{CLIENT_LOG_PREFIX} [WARN] WebSocket connection closed during send: {e}")
                    schedule_gui_update(root, status_label.config, text="Status: Connection lost (send).")
                    websocket_connection = None
                    break # Exit task, manager will handle reconnection.
                except Exception as e:
                    print(f"{CLIENT_LOG_PREFIX} [ERROR] Error sending audio via WebSocket: {e}")
                    schedule_gui_update(root, status_label.config, text="Status: Error sending audio.")
                    await asyncio.sleep(0.1)
            elif not app_running:
                break
            else:
                await asyncio.sleep(0.01) # Wait if not recording or no connection.
    finally:
        print(f"{CLIENT_LOG_PREFIX} [INFO] Send audio task finishing.")

async def receive_audio_from_websocket():
    """Coroutine: Receives audio from WebSocket, plays it, and optionally saves it."""
    global websocket_connection, app_running, p, root, status_label, args, RATE, FORMAT, CHANNELS, CLIENT_LOG_PREFIX
    output_stream_local = None
    is_saving_audio_active_session = False
    saved_frames_this_session = 0
    max_frames_to_save_this_session = 0
    audio_buffer_for_saving = []
    sample_width = p.get_sample_size(FORMAT)

    if args and args.save_received_audio:
        is_saving_audio_active_session = True
        max_frames_to_save_this_session = args.save_duration * RATE
        print(f"{CLIENT_LOG_PREFIX} [INFO] Will save up to {args.save_duration}s of received audio to {args.save_received_audio}")

    print(f"{CLIENT_LOG_PREFIX} [INFO] Receive audio task started.")
    try:
        try:
            output_stream_local = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
            print(f"{CLIENT_LOG_PREFIX} [STATUS] Speaker stream opened for received audio.")
        except IOError as e:
            print(f"{CLIENT_LOG_PREFIX} [ERROR] PyAudio Error (Output): {e}")
            error_str = str(e).lower()
            user_msg = "Error: Could not open speaker. Check audio settings."
            if "invalid output device" in error_str or "no default output device" in error_str:
                user_msg = "Error: No speaker found or invalid output device."
            elif "device unavailable" in error_str or "device or resource busy" in error_str:
                user_msg = "Error: Speaker is busy or unavailable."
            print(f"{CLIENT_LOG_PREFIX} [ERROR] Failed to open speaker: {user_msg}")
            schedule_gui_update(root, status_label.config, text=user_msg)
            return
        except Exception as e:
            print(f"{CLIENT_LOG_PREFIX} [ERROR] Fatal: Unexpected error opening output audio stream: {e}")
            schedule_gui_update(root, status_label.config, text="Status: Error - Cannot play audio (unexpected).")
            return

        while app_running:
            if websocket_connection:
                try:
                    data = await asyncio.wait_for(websocket_connection.recv(), timeout=0.1)
                    if data: # If data is not None or empty
                        if output_stream_local and output_stream_local.is_active():
                            output_stream_local.write(data)
                            print(f"{CLIENT_LOG_PREFIX} [DEBUG] Played received audio chunk of {len(data)} bytes.")

                        if is_saving_audio_active_session:
                            audio_buffer_for_saving.append(data)
                            frames_in_chunk = len(data) // (sample_width * CHANNELS)
                            saved_frames_this_session += frames_in_chunk

                            if saved_frames_this_session >= max_frames_to_save_this_session:
                                print(f"{CLIENT_LOG_PREFIX} [INFO] Collected approximately {args.save_duration}s of audio for {args.save_received_audio}. Saving now...")
                                all_audio_bytes = b''.join(audio_buffer_for_saving)
                                save_buffered_audio_to_wav(
                                    args.save_received_audio,
                                    all_audio_bytes, CHANNELS,
                                    sample_width, RATE
                                )
                                audio_buffer_for_saving = []
                                is_saving_audio_active_session = False # Stop collecting for this session
                except asyncio.TimeoutError: # Normal if no data received
                    continue
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"{CLIENT_LOG_PREFIX} [WARN] WebSocket connection closed during receive: {e}")
                    schedule_gui_update(root, status_label.config, text="Status: Connection lost (receive).")
                    websocket_connection = None
                    break # Exit task, manager will handle.
                except Exception as e:
                    print(f"{CLIENT_LOG_PREFIX} [ERROR] Error receiving/playing audio from WebSocket: {e}")
                    schedule_gui_update(root, status_label.config, text="Status: Error receiving audio.")
                    await asyncio.sleep(0.1)
            elif not app_running:
                break
            else: # No connection
                await asyncio.sleep(0.01)
    finally:
        if output_stream_local:
            try:
                if output_stream_local.is_active(): output_stream_local.stop_stream()
                output_stream_local.close()
                print(f"{CLIENT_LOG_PREFIX} [INFO] Output audio stream (for received audio) closed.")
            except Exception as e: print(f"{CLIENT_LOG_PREFIX} [ERROR] Error closing output stream for received audio: {e}")

        # Save any remaining buffered audio if saving was active and cut short
        if args and args.save_received_audio and len(audio_buffer_for_saving) > 0 and is_saving_audio_active_session:
            print(f"{CLIENT_LOG_PREFIX} [INFO] Task ending. Saving partially collected audio to {args.save_received_audio}.")
            all_audio_bytes = b''.join(audio_buffer_for_saving)
            save_buffered_audio_to_wav(
                args.save_received_audio, all_audio_bytes,
                CHANNELS, sample_width, RATE
            )
            audio_buffer_for_saving = []
    print(f"{CLIENT_LOG_PREFIX} [INFO] Receive audio task finishing.")

async def websocket_client_manager():
    """Coroutine: Manages WebSocket connection lifecycle and sub-tasks (send/receive)."""
    global websocket_connection, app_running, ANDROID_PHONE_IP, ANDROID_PHONE_PORT, root, status_label, CLIENT_LOG_PREFIX, args
    send_task = None
    receive_task = None
    INITIAL_RETRY_DELAY = 1.0
    MAX_RETRY_DELAY = 30.0
    current_retry_delay = INITIAL_RETRY_DELAY
    print(f"{CLIENT_LOG_PREFIX} [INFO] WebSocket client manager started.")
    while app_running:
        if not websocket_connection:
            if current_retry_delay == INITIAL_RETRY_DELAY: # Only show "Connecting..." on first attempt post-disconnect
                 schedule_gui_update(root, status_label.config, text=f"Status: Connecting to {ANDROID_PHONE_IP}...")
            print(f"{CLIENT_LOG_PREFIX} [INFO] Attempting WebSocket connection to ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT}")
            try:
                ws_connect_coro = websockets.connect(f"ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT}", open_timeout=5)
                websocket_connection = await asyncio.wait_for(ws_connect_coro, timeout=6.0)
                print(f"{CLIENT_LOG_PREFIX} [STATUS] WebSocket connection established.")

                # Set status based on whether saving is active
                if args and args.save_received_audio:
                    schedule_gui_update(root, status_label.config, text=f"Status: Connected (Saving to {args.save_received_audio.split('/')[-1]})")
                else:
                    schedule_gui_update(root, status_label.config, text="Status: Connected. Streaming...")

                current_retry_delay = INITIAL_RETRY_DELAY # Reset on success

                # Clean up old tasks before creating new ones (important after a reconnect)
                if send_task and not send_task.done(): send_task.cancel()
                if receive_task and not receive_task.done(): receive_task.cancel()
                if send_task: await asyncio.gather(send_task, return_exceptions=True) # Ensure they are awaited
                if receive_task: await asyncio.gather(receive_task, return_exceptions=True)

                send_task = asyncio.create_task(send_audio_to_websocket())
                receive_task = asyncio.create_task(receive_audio_from_websocket())
            except asyncio.TimeoutError:
                msg = f"Status: Connection timed out. Retrying in {int(current_retry_delay)}s..."
                print(f"{CLIENT_LOG_PREFIX} [ERROR] WebSocket connection to ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT} timed out. Retrying in {int(current_retry_delay)}s...")
                schedule_gui_update(root, status_label.config, text=msg)
                websocket_connection = None
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * 2, MAX_RETRY_DELAY)
            except websockets.exceptions.ConnectionRefusedError as e:
                msg = f"Status: Connection refused. Retrying in {int(current_retry_delay)}s..."
                print(f"{CLIENT_LOG_PREFIX} [ERROR] WebSocket connection refused by server (ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT}). Retrying in {int(current_retry_delay)}s...")
                schedule_gui_update(root, status_label.config, text=msg)
                websocket_connection = None
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * 2, MAX_RETRY_DELAY)
            except OSError as e: # Catches host not found, network unreachable, etc.
                msg = f"Status: Network error ({type(e).__name__}). Retrying in {int(current_retry_delay)}s..."
                print(f"{CLIENT_LOG_PREFIX} [ERROR] WebSocket OS error ({type(e).__name__}: {e}) for ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT}. Retrying in {int(current_retry_delay)}s...")
                schedule_gui_update(root, status_label.config, text=msg)
                websocket_connection = None
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * 2, MAX_RETRY_DELAY)
            except Exception as e:
                msg = f"Status: Connection error. Retrying in {int(current_retry_delay)}s..."
                print(f"{CLIENT_LOG_PREFIX} [ERROR] Unexpected WebSocket connection error ({type(e).__name__}: {e}) for ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT}. Retrying in {int(current_retry_delay)}s...")
                schedule_gui_update(root, status_label.config, text=msg)
                websocket_connection = None
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * 2, MAX_RETRY_DELAY)
        else: # If connection exists, ping it
            try:
                await asyncio.wait_for(websocket_connection.ping(), timeout=3.0)
                current_retry_delay = INITIAL_RETRY_DELAY # Reset if ping successful
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                print(f"{CLIENT_LOG_PREFIX} [WARN] WebSocket ping failed or connection closed ({type(e).__name__}). Attempting to reconnect...")
                schedule_gui_update(root, status_label.config, text=f"Status: Connection lost. Retrying in {int(current_retry_delay)}s...")
                websocket_connection = None
                if send_task and not send_task.done(): send_task.cancel()
                if receive_task and not receive_task.done(): receive_task.cancel()
            except Exception as e: # Other errors during ping
                print(f"{CLIENT_LOG_PREFIX} [ERROR] Error during WebSocket ping: {e}. Assuming connection lost.")
                schedule_gui_update(root, status_label.config, text=f"Status: Connection error (ping). Retrying in {int(current_retry_delay)}s...")
                websocket_connection = None
                if send_task and not send_task.done(): send_task.cancel()
                if receive_task and not receive_task.done(): receive_task.cancel()
            await asyncio.sleep(1) # Interval for pinging active connection

    # Shutdown sequence for the manager
    print(f"{CLIENT_LOG_PREFIX} [INFO] WebSocket client manager initiating shutdown...")
    tasks_to_cancel = []
    if send_task and not send_task.done(): tasks_to_cancel.append(send_task)
    if receive_task and not receive_task.done(): tasks_to_cancel.append(receive_task)
    for task in tasks_to_cancel: task.cancel() # Signal cancellation
    if tasks_to_cancel:
        print(f"{CLIENT_LOG_PREFIX} [INFO] Waiting for {len(tasks_to_cancel)} sub-tasks (send/receive) to cancel...")
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True) # Wait for them to finish
        print(f"{CLIENT_LOG_PREFIX} [INFO] Send/receive sub-tasks cancelled.")
    if websocket_connection:
        print(f"{CLIENT_LOG_PREFIX} [INFO] Closing WebSocket connection from manager.")
        try: await websocket_connection.close()
        except Exception as e: print(f"{CLIENT_LOG_PREFIX} [ERROR] Error closing websocket connection in manager: {e}")
        websocket_connection = None
    print(f"{CLIENT_LOG_PREFIX} [INFO] WebSocket client manager finished.")

def run_audio_and_websocket_loop():
    """Main function for the background thread: sets up asyncio loop and runs the WebSocket manager."""
    global audio_stream, app_running, p, root, status_label, start_button, stop_button, audio_buffer_queue, CLIENT_LOG_PREFIX
    audio_buffer_queue = asyncio.Queue()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.current_thread().websocket_loop = loop
    manager_task = None
    try:
        try:
            audio_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, stream_callback=audio_callback)
            audio_stream.start_stream() # Start the callback chain
            print(f"{CLIENT_LOG_PREFIX} [STATUS] Microphone stream opened successfully.")
        except IOError as e:
            print(f"{CLIENT_LOG_PREFIX} [ERROR] PyAudio Error (Input): {e}")
            error_str = str(e).lower()
            user_msg = "Error: Could not open microphone. Check audio settings."
            if "invalid input device" in error_str or "no default input device" in error_str:
                user_msg = "Error: No microphone found or invalid input device."
            elif "device unavailable" in error_str or "device or resource busy" in error_str:
                user_msg = "Error: Microphone is busy or unavailable."
            print(f"{CLIENT_LOG_PREFIX} [ERROR] Failed to open microphone: {user_msg}")
            schedule_gui_update(root, status_label.config, text=user_msg)
            schedule_gui_update(root, start_button.config, state=tk.NORMAL)
            schedule_gui_update(root, stop_button.config, state=tk.DISABLED)
            app_running = False # Critical failure
            return # Exit thread
        except Exception as e:
            print(f"{CLIENT_LOG_PREFIX} [ERROR] Fatal: Unexpected error opening input audio stream: {e}")
            schedule_gui_update(root, status_label.config, text=f"Status: Mic Error (unexpected) - {e}")
            schedule_gui_update(root, start_button.config, state=tk.NORMAL)
            schedule_gui_update(root, stop_button.config, state=tk.DISABLED)
            app_running = False
            return

        # Update GUI now that mic is confirmed open
        schedule_gui_update(root, status_label.config, text="Status: Mic open, connecting...")

        manager_task = loop.create_task(websocket_client_manager())
        loop.run_until_complete(manager_task) # Run the manager until it completes (or loop is stopped)
    except Exception as e:
        print(f"{CLIENT_LOG_PREFIX} [ERROR] Unhandled error in run_audio_and_websocket_loop: {e}")
        schedule_gui_update(root, status_label.config, text=f"Status: Critical Error - {e}")
        app_running = False # Ensure main app knows something went wrong
    finally:
        print(f"{CLIENT_LOG_PREFIX} [INFO] run_audio_and_websocket_loop - finally block executing...")
        # Stop and close the input audio stream
        if audio_stream :
            try:
                if audio_stream.is_active(): audio_stream.stop_stream()
                audio_stream.close()
                print(f"{CLIENT_LOG_PREFIX} [INFO] Audio input stream (microphone) closed in finally.")
            except Exception as e: print(f"{CLIENT_LOG_PREFIX} [ERROR] Error closing input audio stream in finally: {e}")
            audio_stream = None # Reset global

        # Ensure manager task is awaited/cancelled if it didn't complete
        if manager_task and not manager_task.done():
             print(f"{CLIENT_LOG_PREFIX} [WARN] Manager task was still pending in finally. Attempting to cancel.")
             manager_task.cancel()
             try: # Give it a chance to process cancellation
                 loop.run_until_complete(asyncio.gather(manager_task, return_exceptions=True))
             except asyncio.CancelledError:
                 print(f"{CLIENT_LOG_PREFIX} [INFO] Manager task explicitly cancelled.")

        # Stop and close the asyncio event loop for this thread
        if loop.is_running():
            print(f"{CLIENT_LOG_PREFIX} [INFO] Stopping asyncio event loop (for background thread) from finally.")
            # Cancel any remaining tasks in this loop
            tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)] # Exclude current task if any
            if tasks:
                print(f"{CLIENT_LOG_PREFIX} [INFO] Cancelling {len(tasks)} outstanding asyncio tasks in background loop...")
                for task in tasks: task.cancel()
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True)) # Wait for cancellations
                print(f"{CLIENT_LOG_PREFIX} [INFO] Outstanding asyncio tasks in background loop cancelled.")
            loop.call_soon_threadsafe(loop.stop) # Request loop stop
            # loop.run_forever() # Not needed if loop.stop() is processed by run_until_complete(manager_task)
        print(f"{CLIENT_LOG_PREFIX} [INFO] Asyncio event loop (for background thread) believed to be stopped.")

        # Update GUI to reflect that operations have stopped.
        # This is important if the loop exits due to an error or normal completion.
        if not app_running or (manager_task and manager_task.done()): # Check if shutdown was intended or task completed
            schedule_gui_update(root, status_label.config, text="Status: Stopped.")
            schedule_gui_update(root, start_button.config, state=tk.NORMAL)
            schedule_gui_update(root, stop_button.config, state=tk.DISABLED)
        print(f"{CLIENT_LOG_PREFIX} [INFO] run_audio_and_websocket_loop - background thread finished.")

# --- GUI Setup Buttons ---
start_button = tk.Button(root, text="Start Streaming", command=start_recording_wrapper, font=("Arial", 14), width=20, height=2)
start_button.pack(pady=5)
stop_button = tk.Button(root, text="Stop Streaming", command=stop_recording_wrapper, font=("Arial", 14), width=20, height=2, state=tk.DISABLED)
stop_button.pack(pady=5)

# --- Main Window Close Handler ---
def on_closing_main_window():
    """Handles the event when the main Tkinter window is closed by the user."""
    global app_running, p, root, CLIENT_LOG_PREFIX
    print(f"{CLIENT_LOG_PREFIX} [INFO] Main window closing sequence initiated (WM_DELETE_WINDOW).")
    if app_running:
        print(f"{CLIENT_LOG_PREFIX} [INFO] app_running is True from on_closing, setting to False to signal shutdown.")
        app_running = False # Signal background thread/tasks to stop

    # Brief pause to allow background thread to start its shutdown sequence.
    # A more robust solution would involve joining the thread (see suggestions for improvement).
    print(f"{CLIENT_LOG_PREFIX} [INFO] Giving background tasks a moment to react to app_running=False (0.5s)...")
    time.sleep(0.5)

    print(f"{CLIENT_LOG_PREFIX} [INFO] on_closing_main_window: Terminating global PyAudio instance.")
    if p:
        try:
            p.terminate()
            print(f"{CLIENT_LOG_PREFIX} [INFO] Global PyAudio instance terminated.")
        except Exception as e:
            print(f"{CLIENT_LOG_PREFIX} [ERROR] Error terminating global PyAudio instance: {e}")

    print(f"{CLIENT_LOG_PREFIX} [INFO] on_closing_main_window: Destroying Tkinter root window.")
    if root: # Check if root still exists
        root.destroy()
        # root = None # Not strictly necessary, Python's GC will handle.
        print(f"{CLIENT_LOG_PREFIX} [INFO] Tkinter root window destroyed.")
    print(f"{CLIENT_LOG_PREFIX} [INFO] Application shutdown sequence from on_closing_main_window finished.")

# --- Main Execution Block ---
if __name__ == "__main__":
    global args, CLIENT_LOG_PREFIX # args needs to be global for other functions to access it

    parser = argparse.ArgumentParser(description="PC Audio Client for streaming audio to an Android WebSocket server.")
    parser.add_argument(
        "--auto-start",
        action="store_true",
        help="Automatically start the recording and streaming process on launch."
    )
    parser.add_argument(
        "--save-received-audio",
        type=str,
        default=None,
        metavar="FILENAME",
        help="Filename to save the initial segment of received audio (e.g., received_audio.wav)."
    )
    parser.add_argument(
        "--save-duration",
        type=int,
        default=5,
        metavar="SECONDS",
        help="Duration of received audio to save in seconds (default: 5)."
    )
    args = parser.parse_args() # Parse arguments and store them in the global 'args'

    # Initial IP configuration check (runs in main thread before mainloop)
    if ANDROID_PHONE_IP == "YOUR_ANDROID_PHONE_IP_ADDRESS":
        # This direct GUI update is safe as it's before mainloop()
        status_label.config(text="Status: Configure Phone IP in script!")
        start_button.config(state=tk.DISABLED)

    # Set the window close button protocol
    root.protocol("WM_DELETE_WINDOW", on_closing_main_window)

    # Auto-start logic based on parsed arguments
    if args.auto_start:
        if ANDROID_PHONE_IP == "YOUR_ANDROID_PHONE_IP_ADDRESS":
            print(f"{CLIENT_LOG_PREFIX} [ERROR] --auto-start specified, but ANDROID_PHONE_IP is not configured. Auto-start aborted.")
            status_label.config(text="Status: Auto-start failed. Configure IP!") # Safe direct update
        else:
            print(f"{CLIENT_LOG_PREFIX} [INFO] --auto-start flag detected. Attempting to auto-start recording and streaming...")
            # Schedule start_recording_wrapper to run shortly after mainloop starts.
            root.after(100, start_recording_wrapper)

    try:
        print(f"{CLIENT_LOG_PREFIX} [INFO] Starting Tkinter mainloop...")
        root.mainloop()
    except KeyboardInterrupt: # Handle Ctrl+C if Tkinter window is not in focus or for other reasons
        print(f"{CLIENT_LOG_PREFIX} [INFO] KeyboardInterrupt caught in main Tkinter loop. Closing application.")
        on_closing_main_window() # Attempt graceful shutdown
    finally:
        print(f"{CLIENT_LOG_PREFIX} [INFO] Application has exited.")
