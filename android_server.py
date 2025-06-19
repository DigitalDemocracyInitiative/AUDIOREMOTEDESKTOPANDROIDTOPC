# android_server.py
#
# Purpose:
# This script implements a WebSocket server intended to run on an Android device
# (e.g., within Termux or a similar environment). Its main functions are:
# 1. Receive raw audio data chunks from a connected PC client via WebSocket.
# 2. Play back the received audio on the Android device.
# 3. Simulate a response from a conceptual "Gemini Live" service by generating
#    a simple audio signal (e.g., a sine wave).
# 4. Send this simulated audio response back to the PC client via WebSocket.
#
# Intended Environment:
# Android (e.g., using Termux with Python installed).
# Requires access to audio playback capabilities.
#
# Required Python Packages (install via pip):
# - websockets: For WebSocket server implementation.
# - pyaudio: For audio playback. (May require extra steps to install on Android/Termux,
#            e.g., installing portaudio via 'pkg install portaudio')
# - numpy: For generating the sine wave audio signal.

import asyncio
import websockets
import pyaudio
import numpy as np
import math
import time

# --- Global Audio Constants ---
# These constants define the audio stream parameters. They should ideally match
# the parameters used by the PC client sending the audio.

FORMAT = pyaudio.paInt16  # Audio format for playback and generated sine wave. paInt16 means 16-bit integers.
CHANNELS = 1             # Mono audio. Set to 2 for stereo if needed.
RATE = 44100             # Sample rate in Hz. Common for CD-quality audio.
CHUNK = 1024             # Number of frames per buffer for audio playback. Affects latency.

# Constants for the simulated Gemini Live response (sine wave)
SINE_FREQUENCY = 440.0   # Frequency of the sine wave in Hz (A4 musical note).
SINE_DURATION = 0.5      # Duration of the generated sine wave in seconds.

# --- WebSocket Connection Handler ---
async def handler(websocket, path):
    """
    Handles incoming WebSocket connections from clients.
    For each client, it:
    1. Opens an audio stream for playback.
    2. Receives audio messages (chunks of raw audio data).
    3. Plays the received audio chunks.
    4. Simulates a response (generates a sine wave).
    5. Sends the simulated audio response back to the client.
    Manages PyAudio resources per connection.
    'path' is the request path from the client, not used in this version of the server.
    """
    client_address = websocket.remote_address
    print(f"Client connected from {client_address}")

    # Initialize PyAudio instance for this connection handler.
    # Each handler gets its own PyAudio instance to manage its stream.
    p = pyaudio.PyAudio()
    stream = None  # Initialize stream variable

    try:
        # Attempt to open an audio stream for playback.
        try:
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            output=True,  # This stream is for audio output (playback).
                            frames_per_buffer=CHUNK)
            print(f"Audio output stream opened for client {client_address}")
        except Exception as e:
            # Log the error and terminate the handler if stream opening fails.
            print(f"Failed to open audio output stream for {client_address}: {e}")
            # Not sending error to client here, but could be added if client expects it.
            return # Exit this handler instance.

        # Main loop for receiving and processing messages from the client.
        async for message in websocket:
            try:
                # Play received audio data.
                # Assumes 'message' is a chunk of raw audio data from the client.
                if stream and stream.is_active():
                    stream.write(message)
                    # For debugging: print(f"Played back {len(message)} bytes from {client_address}.")
                else:
                    # This might occur if the stream was closed or became inactive unexpectedly.
                    print(f"Audio stream not active for {client_address}. Cannot play message.")
                    break  # Exit the message loop.

                # --- Simulate Gemini Live processing and response ---
                # This section generates a sine wave as a placeholder for a real response.
                print(f"Simulating Gemini Live processing for client {client_address}...")

                # Calculate the number of samples for the sine wave.
                num_samples = int(SINE_DURATION * RATE)
                # Create a time vector for the sine wave.
                t = np.linspace(0, SINE_DURATION, num_samples, endpoint=False)
                # Generate the sine wave. Amplitude 0.5 to avoid potential clipping.
                sine_wave = 0.5 * np.sin(2 * np.pi * SINE_FREQUENCY * t)

                # Convert the floating-point sine wave to 16-bit integer format.
                # PyAudio paInt16 expects values in the range [-32768, 32767].
                audio_data_int = (sine_wave * 32767).astype(np.int16)
                # Convert the NumPy array of 16-bit integers to a byte string for sending.
                audio_bytes = audio_data_int.tobytes()

                # Send the simulated audio response back to the client.
                await websocket.send(audio_bytes)
                print(f"Sent {len(audio_bytes)} bytes of simulated audio response to {client_address}.")

            except Exception as e:
                # Handles errors during message processing (playback, sine generation, send).
                print(f"Error processing message or sending response for {client_address}: {e}")
                if isinstance(e, websockets.exceptions.ConnectionClosed):
                    # If the error is due to connection closure, re-raise it
                    # to be handled by the outer specific ConnectionClosed exceptions.
                    raise
                # For other errors within the message processing loop, break the loop.
                break

    # Handle WebSocket connection closure events.
    except websockets.exceptions.ConnectionClosedOK:
        # This occurs when the client closes the connection cleanly.
        print(f"Client {client_address} disconnected normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        # This occurs if the connection closes due to an error.
        print(f"Client {client_address} connection error: {e}")
    except Exception as e:
        # Catch-all for any other unexpected errors within the handler's main try block.
        print(f"Unexpected error in handler for {client_address}: {e}")
    finally:
        # This block ensures that resources are cleaned up regardless of how the handler exits.
        print(f"Cleaning up resources for client {client_address}...")
        if stream:
            try:
                if stream.is_active():
                    stream.stop_stream()  # Stop the stream if it's active.
                stream.close()            # Close the stream.
                print(f"Audio stream closed for {client_address}.")
            except Exception as e:
                print(f"Error closing audio stream for {client_address}: {e}")

        p.terminate()  # Terminate the PyAudio instance associated with this handler.
        print(f"PyAudio instance terminated for {client_address}.")
        print(f"Connection handler for {client_address} finished.")

# --- Main Server Logic ---
async def main():
    """
    Main asynchronous function to start and manage the WebSocket server.
    It includes a loop to attempt restarting the server if it encounters certain errors.
    """
    # Loop indefinitely to allow the server to attempt restarts.
    while True:
        try:
            print("Attempting to start WebSocket server...")
            # Start the WebSocket server.
            # websockets.serve() creates a server instance.
            # - 'handler' is the function called for each new client connection.
            # - "0.0.0.0" means listen on all available network interfaces.
            # - 8765 is the port number.
            server = await websockets.serve(handler, "0.0.0.0", 8765)
            print("Server started successfully, listening on ws://0.0.0.0:8765")
            print("Waiting for client connections... Press Ctrl+C to stop the server.")

            # Keep the server running until it's closed.
            # server.wait_closed() will complete when the server is stopped.
            await server.wait_closed()

        except OSError as e:
            # Handles OS-level errors, e.g., "address already in use" if port 8765 is taken.
            print(f"Server main loop OS error: {e}. Will attempt to restart in 5 seconds...")
        except Exception as e:
            # Handles other unexpected errors that might occur in the server's main loop.
            print(f"Server main loop unexpected error: {e}. Will attempt to restart in 5 seconds...")

        # This part is reached if server.wait_closed() completes (e.g., server explicitly stopped by code,
        # which is not implemented here to happen automatically) or if an exception was caught.
        print("Server has stopped or encountered an error. Waiting 5 seconds before attempting to restart...")
        await asyncio.sleep(5) # Wait for 5 seconds before restarting the loop.

# Standard Python entry point.
if __name__ == "__main__":
    print("Initializing server application...")
    try:
        # Run the main asynchronous function.
        # asyncio.run() is the main way to start an asyncio application.
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handles manual shutdown (e.g., Ctrl+C from the terminal).
        print("Server shutting down manually due to KeyboardInterrupt.")
    except Exception as e:
        # Catches critical errors during the initial startup via asyncio.run(main()),
        # or if an error somehow escapes main()'s own try-except loop (which is unlikely).
        print(f"Critical error preventing server startup or during main execution: {e}")
    finally:
        # This block executes after the program is exiting.
        print("Server program finished.")
