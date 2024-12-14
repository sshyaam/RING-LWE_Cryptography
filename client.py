import socket
import threading
import base64
import pyaudio
import wave
import os
import struct
import numpy as np
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import ringlwe
from ringlwe import *
import chacha20
from chacha20 import *

# Initialize global variables
shared_key = None
nonce = b"0123456789ab"
ring = RingLWE()
name = ""

recording = False
voice_file = "recorded_message.wav"

selected_file_data = None  # Variable to store the selected file data
incoming_file_data = None  # Variable to store incoming file data

def record_voice():
    global recording
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    print("[VOICE] Recording...")
    frames = []
    recording = True

    while recording:
        data = stream.read(1024)
        frames.append(data)

    print("[VOICE] Recording stopped.")
    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(voice_file, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b"".join(frames))

def play_voice(audio_data):
    try:
        temp_file = "temp_received_voice.wav"
        with open(temp_file, "wb") as wf:
            wf.write(audio_data)

        wf = wave.open(temp_file, "rb")
        audio = pyaudio.PyAudio()
        stream = audio.open(format=audio.get_format_from_width(wf.getsampwidth()), channels=wf.getnchannels(), rate=wf.getframerate(), output=True)

        print("[VOICE] Playing message...")
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)

        stream.stop_stream()
        stream.close()
        audio.terminate()
        wf.close()
        os.remove(temp_file)
        print("[VOICE] Playback finished.")
    except Exception as e:
        print(f"[VOICE ERROR] Playback failed: {e}")

last_received_voice = None

def receive_messages(client_socket):
    global shared_key, last_received_voice, incoming_file_data
    voice_buffer = []
    file_buffer = []
    data_buffer = b''  # Use bytes buffer
    voice_chacha = None  # For decrypting voice data
    file_chacha = None   # For decrypting file data

    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break  # Connection closed

            data_buffer += data
            while b'\n' in data_buffer:
                message, data_buffer = data_buffer.split(b'\n', 1)
                message = message.strip()
                if not message:
                    continue

                if message.startswith(b"KEY_EXCHANGE"):
                    parts = message.decode('utf-8').split(" ", 2)
                    _, sender, public_key = parts
                    public_key_bytes = base64.b64decode(public_key + "===")
                    shared_key = ring.derive_shared_secret(ring.private_key, public_key_bytes)
                    print(f"[SECURE CHAT] Shared key established with {sender}: {shared_key.hex()}")

                    if not message.endswith(b"REPLY"):
                        reply_public_key = base64.b64encode(ring.public_key).decode('utf-8')
                        client_socket.sendall(f"KEY_EXCHANGE {sender} {reply_public_key} REPLY\n".encode('utf-8'))

                elif message.startswith(b"ENCRYPTED:"):
                    if shared_key:
                        encrypted_part = message[len("ENCRYPTED:"):].decode('utf-8')
                        missing_padding = len(encrypted_part) % 4
                        if missing_padding:
                            encrypted_part += '=' * (4 - missing_padding)
                        chacha = ChaCha20(shared_key, nonce)
                        decrypted_message = chacha.decrypt(base64.b64decode(encrypted_part)).decode('utf-8')
                        print(decrypted_message)
                    else:
                        print("[WARNING] Received encrypted message but no shared key established.")

                elif message.startswith(b"VOICE_CHUNK:"):
                    if shared_key:
                        if voice_chacha is None:
                            # Initialize the cipher once per voice message
                            voice_chacha = ChaCha20(shared_key, nonce)
                        b64_data = message[len("VOICE_CHUNK:"):].decode('utf-8')
                        missing_padding = len(b64_data) % 4
                        if missing_padding:
                            b64_data += '=' * (4 - missing_padding)
                        encrypted_chunk = base64.b64decode(b64_data)
                        decrypted_chunk = voice_chacha.decrypt(encrypted_chunk)
                        voice_buffer.append(decrypted_chunk)
                        print(f"[DEBUG] Received voice chunk of size: {len(decrypted_chunk)}")
                    else:
                        print("[WARNING] Received voice chunk but no shared key established.")

                elif message == b"VOICE_END":
                    if voice_buffer:
                        last_received_voice = b"".join(voice_buffer)
                        voice_buffer = []
                        voice_chacha = None  # Reset cipher after message is complete
                        print(f"[VOICE] Reassembled voice message of size: {len(last_received_voice)} bytes.")
                    else:
                        print("[VOICE ERROR] No chunks to reassemble.")

                elif message.startswith(b"FILE_CHUNK:"):
                    if shared_key:
                        if file_chacha is None:
                            # Initialize the cipher once per file transfer
                            file_chacha = ChaCha20(shared_key, nonce)
                        b64_data = message[len("FILE_CHUNK:"):].decode('utf-8')
                        missing_padding = len(b64_data) % 4
                        if missing_padding:
                            b64_data += '=' * (4 - missing_padding)
                        encrypted_chunk = base64.b64decode(b64_data)
                        decrypted_chunk = file_chacha.decrypt(encrypted_chunk)
                        file_buffer.append(decrypted_chunk)
                        print(f"[DEBUG] Received file chunk of size: {len(decrypted_chunk)} bytes")
                    else:
                        print("[WARNING] Received file chunk but no shared key established.")

                elif message == b"FILE_END":
                    if file_buffer:
                        incoming_file_data = b"".join(file_buffer)
                        file_buffer = []
                        file_chacha = None  # Reset cipher after file transfer is complete
                        print(f"[FILE] Reassembled file of size: {len(incoming_file_data)} bytes.")
                    else:
                        print("[FILE ERROR] No file chunks to reassemble.")

                else:
                    print(message.decode('utf-8'))

        except Exception as e:
            print(f"[CLIENT ERROR] {e}")
            break

def start_client():
    global shared_key, name, recording, selected_file_data, incoming_file_data
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Enter the IP: ")
        lh = input().strip()
        client_socket.connect((lh, 12345))

        name = input("Enter your name: ").strip()
        client_socket.sendall((name + '\n').encode('utf-8'))

        threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()

        while True:
            message = input().strip()

            if message.startswith("/contact"):
                client_socket.sendall((message + '\n').encode('utf-8'))
                print("Contact Request Sent... Waiting for user to accept")

            elif message.startswith("/accept"):
                public_key = base64.b64encode(ring.public_key).decode('utf-8')
                client_socket.sendall((message + '\n').encode('utf-8'))
                _, target_name = message.split(" ", 1)
                client_socket.sendall(f"/key_exchange {target_name} {public_key}\n".encode('utf-8'))

            elif message.startswith("/decline"):
                client_socket.sendall((message + '\n').encode('utf-8'))

            elif shared_key and not message.startswith("/"):
                message_with_sender = f"{name}: {message}"
                chacha = ChaCha20(shared_key, nonce)
                encrypted_message = chacha.encrypt(message_with_sender.encode('utf-8'))
                encoded_message = base64.b64encode(encrypted_message).decode('utf-8')
                client_socket.sendall(f"ENCRYPTED:{encoded_message}\n".encode('utf-8'))

            elif message == "/voice record":
                threading.Thread(target=record_voice).start()

            elif message == "/voice stop":
                recording = False

            elif message == "/voice send":
                if os.path.exists(voice_file):
                    with open(voice_file, "rb") as vf:
                        voice_data = vf.read()

                    # Initialize cipher once for the entire voice message
                    chacha = ChaCha20(shared_key, nonce)

                    chunk_size = 1024
                    start = 0

                    print(f"[DEBUG] Voice Data Before Encryption: {len(voice_data)} bytes")

                    while start < len(voice_data):
                        chunk = voice_data[start:start + chunk_size]
                        encrypted_chunk = chacha.encrypt(chunk)
                        encoded_chunk = base64.b64encode(encrypted_chunk).decode('utf-8')
                        client_socket.sendall(f"VOICE_CHUNK:{encoded_chunk}\n".encode('utf-8'))
                        start += chunk_size

                    client_socket.sendall("VOICE_END\n".encode('utf-8'))
                    print("[VOICE] Voice message sent in chunks.")
                else:
                    print("[VOICE ERROR] No recorded message found.")

            elif message == "/voice play":
                if last_received_voice:
                    print(f"[DEBUG] Playing voice message of size: {len(last_received_voice)} bytes.")
                    play_voice(last_received_voice)
                else:
                    print("[VOICE ERROR] No voice message received yet.")

            elif message == "/file input":
                root = Tk()
                root.withdraw()
                filename = askopenfilename()
                root.update()
                root.destroy()
                if filename:
                    with open(filename, "rb") as f:
                        selected_file_data = f.read()
                    print(f"[FILE] Selected file {filename} with size {len(selected_file_data)} bytes.")
                else:
                    print("[FILE] No file selected.")

            elif message == "/file send":
                if selected_file_data and shared_key:
                    # Initialize cipher once for the entire file transfer
                    chacha = ChaCha20(shared_key, nonce)

                    chunk_size = 1024
                    start = 0
                    print(f"[DEBUG] File Data Before Encryption: {len(selected_file_data)} bytes.")
                    while start < len(selected_file_data):
                        chunk = selected_file_data[start:start + chunk_size]
                        encrypted_chunk = chacha.encrypt(chunk)
                        encoded_chunk = base64.b64encode(encrypted_chunk).decode('utf-8')
                        client_socket.sendall(f"FILE_CHUNK:{encoded_chunk}\n".encode('utf-8'))
                        start += chunk_size
                    client_socket.sendall("FILE_END\n".encode('utf-8'))
                    print("[FILE] File sent in chunks.")
                else:
                    if not selected_file_data:
                        print("[FILE ERROR] No file selected. Use /file input to select a file.")
                    if not shared_key:
                        print("[FILE ERROR] No shared key established. Cannot send file.")

            elif message == "/file download":
                if incoming_file_data:
                    filename = "received_file.docx"
                    with open(filename, "wb") as f:
                        f.write(incoming_file_data)
                    print(f"[FILE] File saved as {filename} in current directory.")
                    incoming_file_data = None  # Clear after saving
                else:
                    print("[FILE ERROR] No file received yet.")

            elif message == "/help":
                client_socket.sendall((message + '\n').encode('utf-8'))

            elif message.startswith("/list") or message.startswith("/leave"):
                client_socket.sendall((message + '\n').encode('utf-8'))
                if message.startswith("/leave"):
                    shared_key = None

            else:
                print("[ERROR] Invalid command. Type /help for a list of commands.")

    except Exception as e:
        print(f"[CLIENT STARTUP ERROR] {e}")

if __name__ == "__main__":
    start_client()
