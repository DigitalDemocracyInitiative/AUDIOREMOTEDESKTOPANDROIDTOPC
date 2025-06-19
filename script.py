import tkinter as tk
import pyaudio
import asyncio
import websockets
# import json # Not used currently
import threading
import time

# --- Configuration ---
ANDROID_PHONE_IP = "YOUR_ANDROID_PHONE_IP_ADDRESS"
ANDROID_PHONE_PORT = 8765

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# --- Global Variables ---
audio_stream = None # Input audio stream from microphone
websocket_connection = None
recording = False # Controls audio capture via callback
app_running = True  # General flag to signal all loops and threads to terminate

# Global PyAudio instance.
p = pyaudio.PyAudio()

# --- GUI Elements (global for easy access by update functions) ---
# Initialize root window first, as it's needed by schedule_gui_update
root = tk.Tk()
root.title("PC Audio Client")
root.geometry("400x250")

# --- Thread-Safe GUI Update Function ---
def schedule_gui_update(root_tk_instance, callable_to_run, **kwargs_for_callable):
    """
    Schedules a callable to be executed on the main Tkinter thread.
    Ensures thread-safety for GUI updates from background threads.
    """
    if root_tk_instance and root_tk_instance.winfo_exists(): # Check if window still exists
        root_tk_instance.after(0, lambda: callable_to_run(**kwargs_for_callable))
    else:
        if root_tk_instance and root_tk_instance.winfo_exists():
             print("Warning: GUI update scheduled but root window is gone or invalid.")

status_label = tk.Label(root, text="Status: Ready", font=("Arial", 12))
status_label.pack(pady=10)

# --- GUI Control Functions ---
def start_recording_wrapper():
    """Wrapper to manage GUI and start background tasks."""
    global recording, app_running
    if recording:
        return

    recording = True
    app_running = True

    schedule_gui_update(root, status_label.config, text="Status: Initializing...")
    schedule_gui_update(root, start_button.config, state=tk.DISABLED)
    schedule_gui_update(root, stop_button.config, state=tk.NORMAL)

    threading.Thread(target=run_audio_and_websocket_loop, daemon=True).start()

def stop_recording_wrapper():
    """Wrapper to manage GUI and signal background tasks to stop."""
    global recording, app_running

    if not app_running and not recording:
        print("Stop called but already stopping or stopped.")
        return

    schedule_gui_update(root, status_label.config, text="Status: Stopping...")
    schedule_gui_update(root, stop_button.config, state=tk.DISABLED)

    recording = False
    app_running = False


# --- Audio Processing and WebSocket Communication (executed in a background thread) ---
def audio_callback(in_data, frame_count, time_info, status_flags):
    if recording and app_running:
        try:
            loop = getattr(threading.current_thread(), 'websocket_loop', None)
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(audio_buffer_queue.put(in_data), loop)
        except Exception as e:
            print(f"Audio callback error: {e}")
        return (in_data, pyaudio.paContinue)
    else:
        return (None, pyaudio.paComplete)

async def send_audio_to_websocket():
    global websocket_connection, recording, app_running, root, status_label
    print("Send audio task started.")
    while app_running:
        if websocket_connection and recording:
            try:
                data = await asyncio.wait_for(audio_buffer_queue.get(), timeout=0.1)
                if data:
                    await websocket_connection.send(data)
                audio_buffer_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed as e:
                print(f"WebSocket connection closed during send: {e}")
                schedule_gui_update(root, status_label.config, text="Status: Connection lost (send). Retrying...")
                websocket_connection = None
                break
            except Exception as e:
                print(f"Error sending audio via WebSocket: {e}")
                schedule_gui_update(root, status_label.config, text="Status: Error sending audio. Retrying...")
                await asyncio.sleep(0.1)
        elif not app_running:
            break
        else:
            await asyncio.sleep(0.01)
    print("Send audio task finishing.")

async def receive_audio_from_websocket():
    global websocket_connection, app_running, p, root, status_label
    output_stream_local = None
    print("Receive audio task started.")
    try:
        try:
            output_stream_local = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
            print("Output audio stream opened for received audio.")
        except IOError as e:
            print(f"PyAudio Error (Output): {e}")
            error_str = str(e).lower()
            user_msg = "Error: Could not open speaker. Check audio settings."
            if "invalid output device" in error_str or "no default output device" in error_str:
                user_msg = "Error: No speaker found or invalid output device."
            elif "device unavailable" in error_str or "device or resource busy" in error_str:
                user_msg = "Error: Speaker is busy or unavailable."
            schedule_gui_update(root, status_label.config, text=user_msg)
            return
        except Exception as e:
            print(f"Fatal: Unexpected error opening output audio stream: {e}")
            schedule_gui_update(root, status_label.config, text="Status: Error - Cannot play audio (unexpected).")
            return

        while app_running:
            if websocket_connection:
                try:
                    data = await asyncio.wait_for(websocket_connection.recv(), timeout=0.1)
                    if data and output_stream_local and output_stream_local.is_active():
                        output_stream_local.write(data)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"WebSocket connection closed during receive: {e}")
                    schedule_gui_update(root, status_label.config, text="Status: Connection lost (receive). Retrying...")
                    websocket_connection = None
                    break
                except Exception as e:
                    print(f"Error receiving/playing audio from WebSocket: {e}")
                    schedule_gui_update(root, status_label.config, text="Status: Error receiving audio. Retrying...")
                    await asyncio.sleep(0.1)
            elif not app_running:
                break
            else:
                await asyncio.sleep(0.01)
    finally:
        if output_stream_local:
            try:
                if output_stream_local.is_active(): output_stream_local.stop_stream()
                output_stream_local.close()
                print("Output audio stream (for received audio) closed.")
            except Exception as e: print(f"Error closing output stream for received audio: {e}")
    print("Receive audio task finishing.")

async def websocket_client_manager():
    global websocket_connection, app_running, ANDROID_PHONE_IP, ANDROID_PHONE_PORT, root, status_label

    send_task = None
    receive_task = None

    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 30.0     # seconds
    current_retry_delay = INITIAL_RETRY_DELAY

    print("WebSocket client manager started.")
    while app_running:
        if not websocket_connection:
            # Update GUI before attempting to connect
            if current_retry_delay == INITIAL_RETRY_DELAY: # First attempt after successful connection or initial start
                 schedule_gui_update(root, status_label.config, text=f"Status: Connecting to {ANDROID_PHONE_IP}...")
            # else: # The status is already set by the exception block that led to this retry
                # schedule_gui_update(root, status_label.config, text=f"Status: Retrying connection in {int(current_retry_delay)}s...")

            print(f"Attempting to connect to ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT}")
            try:
                # Set a timeout for the connection attempt itself
                ws_connect_coro = websockets.connect(f"ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT}", open_timeout=5)
                websocket_connection = await asyncio.wait_for(ws_connect_coro, timeout=6.0) # Slightly > open_timeout

                print("WebSocket connection established.")
                schedule_gui_update(root, status_label.config, text="Status: Connected. Streaming...")
                current_retry_delay = INITIAL_RETRY_DELAY # Reset delay on successful connection

                if send_task and not send_task.done(): send_task.cancel()
                if receive_task and not receive_task.done(): receive_task.cancel()
                if send_task: await asyncio.gather(send_task, return_exceptions=True)
                if receive_task: await asyncio.gather(receive_task, return_exceptions=True)

                send_task = asyncio.create_task(send_audio_to_websocket())
                receive_task = asyncio.create_task(receive_audio_from_websocket())

            except asyncio.TimeoutError: # Timeout for asyncio.wait_for (covers entire connection attempt)
                msg = f"Status: Connection timed out. Retrying in {int(current_retry_delay)}s..."
                print(f"Connection to ws://{ANDROID_PHONE_IP}:{ANDROID_PHONE_PORT} timed out.")
                schedule_gui_update(root, status_label.config, text=msg)
                websocket_connection = None
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * 2, MAX_RETRY_DELAY)
            except (websockets.exceptions.ConnectionRefusedError, OSError) as e: # OSError for network issues
                msg = f"Status: Connection failed ({type(e).__name__}). Retrying in {int(current_retry_delay)}s..."
                print(f"Connection failed: {e}.")
                schedule_gui_update(root, status_label.config, text=msg)
                websocket_connection = None
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * 2, MAX_RETRY_DELAY)
            except Exception as e:
                msg = f"Status: Connection error. Retrying in {int(current_retry_delay)}s..."
                print(f"Unexpected WebSocket connection error: {e}.")
                schedule_gui_update(root, status_label.config, text=msg)
                websocket_connection = None
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * 2, MAX_RETRY_DELAY)
        else: # Websocket connection exists, check its health
            try:
                await asyncio.wait_for(websocket_connection.ping(), timeout=3.0)
                # If ping is successful, connection is good. Reset retry delay in case it had increased.
                current_retry_delay = INITIAL_RETRY_DELAY
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                print(f"WebSocket ping failed or connection closed ({type(e).__name__}).")
                # Update status to show retrying with the current delay before it's potentially increased
                schedule_gui_update(root, status_label.config, text=f"Status: Connection lost. Retrying in {int(current_retry_delay)}s...")
                websocket_connection = None
                if send_task and not send_task.done(): send_task.cancel()
                if receive_task and not receive_task.done(): receive_task.cancel()
                # No sleep here, the loop will go to the connection block, sleep with current_retry_delay, then double it.
            except Exception as e:
                print(f"Error during WebSocket ping: {e}. Assuming connection lost.")
                schedule_gui_update(root, status_label.config, text=f"Status: Connection error (ping). Retrying in {int(current_retry_delay)}s...")
                websocket_connection = None
                if send_task and not send_task.done(): send_task.cancel()
                if receive_task and not receive_task.done(): receive_task.cancel()
            await asyncio.sleep(1) # Interval for pinging active connection

    print("WebSocket client manager initiating shutdown...")
    tasks_to_cancel = []
    if send_task and not send_task.done(): tasks_to_cancel.append(send_task)
    if receive_task and not receive_task.done(): tasks_to_cancel.append(receive_task)
    for task in tasks_to_cancel: task.cancel()
    if tasks_to_cancel:
        print(f"Waiting for {len(tasks_to_cancel)} sub-tasks (send/receive) to cancel...")
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        print("Send/receive sub-tasks cancelled.")
    if websocket_connection:
        print("Closing WebSocket connection from manager.")
        try: await websocket_connection.close()
        except Exception as e: print(f"Error closing websocket connection in manager: {e}")
        websocket_connection = None
    print("WebSocket client manager finished.")

def run_audio_and_websocket_loop():
    global audio_stream, app_running, p, root, status_label, start_button, stop_button
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.current_thread().websocket_loop = loop
    manager_task = None
    try:
        try:
            audio_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, stream_callback=audio_callback)
            audio_stream.start_stream()
            print("Audio input stream started (microphone active).")
        except IOError as e:
            print(f"PyAudio Error (Input): {e}")
            error_str = str(e).lower()
            user_msg = "Error: Could not open microphone. Check audio settings."
            if "invalid input device" in error_str or "no default input device" in error_str:
                user_msg = "Error: No microphone found or invalid input device."
            elif "device unavailable" in error_str or "device or resource busy" in error_str:
                user_msg = "Error: Microphone is busy or unavailable."
            schedule_gui_update(root, status_label.config, text=user_msg)
            schedule_gui_update(root, start_button.config, state=tk.NORMAL)
            schedule_gui_update(root, stop_button.config, state=tk.DISABLED)
            app_running = False
            return
        except Exception as e:
            print(f"Fatal: Unexpected error opening input audio stream: {e}")
            schedule_gui_update(root, status_label.config, text=f"Status: Mic Error (unexpected) - {e}")
            schedule_gui_update(root, start_button.config, state=tk.NORMAL)
            schedule_gui_update(root, stop_button.config, state=tk.DISABLED)
            app_running = False
            return

        schedule_gui_update(root, status_label.config, text="Status: Mic open, connecting...")
        manager_task = loop.create_task(websocket_client_manager())
        loop.run_until_complete(manager_task)
    except Exception as e:
        print(f"Unhandled error in run_audio_and_websocket_loop: {e}")
        schedule_gui_update(root, status_label.config, text=f"Status: Critical Error - {e}")
        app_running = False
    finally:
        print("run_audio_and_websocket_loop - finally block executing...")
        if audio_stream :
            try:
                if audio_stream.is_active(): audio_stream.stop_stream()
                audio_stream.close()
                print("Audio input stream (microphone) closed in finally.")
            except Exception as e: print(f"Error closing input audio stream in finally: {e}")
            audio_stream = None

        if manager_task and not manager_task.done():
             print("Manager task was still pending in finally. Attempting to cancel.")
             manager_task.cancel()
             loop.run_until_complete(asyncio.gather(manager_task, return_exceptions=True))
        if loop.is_running():
            print("Stopping asyncio event loop (for background thread) from finally.")
            tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
            if tasks:
                print(f"Cancelling {len(tasks)} outstanding asyncio tasks in background loop...")
                for task in tasks: task.cancel()
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                print("Outstanding asyncio tasks in background loop cancelled.")
            loop.call_soon_threadsafe(loop.stop)
        print("Asyncio event loop (for background thread) believed to be stopped.")

        if not app_running or (manager_task and manager_task.done()):
            schedule_gui_update(root, status_label.config, text="Status: Stopped.")
            schedule_gui_update(root, start_button.config, state=tk.NORMAL)
            schedule_gui_update(root, stop_button.config, state=tk.DISABLED)
        print("run_audio_and_websocket_loop - background thread finished.")

start_button = tk.Button(root, text="Start Streaming", command=start_recording_wrapper, font=("Arial", 14), width=20, height=2)
start_button.pack(pady=5)
stop_button = tk.Button(root, text="Stop Streaming", command=stop_recording_wrapper, font=("Arial", 14), width=20, height=2, state=tk.DISABLED)
stop_button.pack(pady=5)

def on_closing_main_window():
    global app_running, p, root
    print("Main window WM_DELETE_WINDOW (on_closing) called.")
    if app_running:
        print("app_running is True from on_closing, setting to False to signal shutdown.")
        app_running = False
    print("Giving background tasks a moment to stop (0.5s)...")
    time.sleep(0.5)
    print("on_closing_main_window: Terminating global PyAudio instance.")
    if p:
        try:
            p.terminate()
            print("Global PyAudio instance terminated.")
        except Exception as e:
            print(f"Error terminating global PyAudio instance: {e}")
    print("on_closing_main_window: Destroying Tkinter root window.")
    if root:
        root.destroy()
        print("Tkinter root window destroyed.")
    print("Application shutdown sequence from on_closing_main_window finished.")

if ANDROID_PHONE_IP == "YOUR_ANDROID_PHONE_IP_ADDRESS":
    status_label.config(text="Status: Configure Phone IP in script!")
    start_button.config(state=tk.DISABLED)
root.protocol("WM_DELETE_WINDOW", on_closing_main_window)
try:
    print("Starting Tkinter mainloop...")
    root.mainloop()
except KeyboardInterrupt:
    print("KeyboardInterrupt caught in main Tkinter loop. Closing application.")
    on_closing_main_window()
finally:
    print("Application has exited.")
