import socket
import threading

clients = {}
chat_sessions = {}


def handle_client(client_socket, address):
    try:
        name = client_socket.recv(1024).decode('utf-8').strip()

        if not name:
            client_socket.sendall("Invalid name. Disconnecting.\n".encode('utf-8'))
            client_socket.close()
            return

        if name in clients.keys():
            client_socket.sendall("Name already exists. Disconnecting.\n".encode('utf-8'))
            client_socket.close()
            return

        clients[name] = {"socket": client_socket, "public_key": None, "contact_request": None}
        print(f"[SERVER] {name} connected from {address}.")
        broadcast(f"{name} has joined the chat!\n", exclude=name)
        send_greeting(client_socket)

        data_buffer = ''

        while True:
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                print(f"[SERVER] {name} has disconnected.")
                break

            data_buffer += data
            while '\n' in data_buffer:
                message, data_buffer = data_buffer.split('\n', 1)
                message = message.strip()
                if not message:
                    continue
                elif message.startswith("/contact"):
                    handle_contact_request(client_socket, name, message)
                elif message.startswith("/accept"):
                    handle_accept_request(client_socket, name, message)
                elif message.startswith("/decline"):
                    handle_decline_request(client_socket, name, message)
                elif message.startswith("/key_exchange"):
                    handle_key_exchange(client_socket, name, message)
                elif message.startswith("/leave"):
                    handle_leave(client_socket, name)
                elif message.startswith("/list"):
                    list_users(client_socket, name)
                elif message.startswith("/help"):
                    send_help(client_socket)
                else:
                    handle_encrypted_message(client_socket, name, message)

    except Exception as e:
        print(f"[SERVER ERROR] {e}")
    finally:
        remove_client(client_socket, name)
        client_socket.close()


def handle_contact_request(client_socket, sender_name, message):
    try:
        _, target_name = message.split(" ", 1)
        if target_name in clients:
            target_socket = clients[target_name]["socket"]
            clients[target_name]["contact_request"] = sender_name
            target_socket.sendall(f"{sender_name} wants to chat with you. Type /accept {sender_name} or /decline {sender_name}.\n".encode('utf-8'))
        else:
            client_socket.sendall(f"User {target_name} not found.\n".encode('utf-8'))
    except Exception as e:
        print(f"[CONTACT ERROR] {e}")


def handle_accept_request(client_socket, recipient_name, message):
    try:
        _, sender_name = message.split(" ", 1)
        if clients[recipient_name]["contact_request"] == sender_name:
            chat_sessions[(recipient_name, sender_name)] = True
            chat_sessions[(sender_name, recipient_name)] = True

            recipient_socket = clients[recipient_name]["socket"]
            sender_socket = clients[sender_name]["socket"]
            recipient_socket.sendall(
                f"Secure chat session established with {sender_name}. You can now exchange messages.\n".encode('utf-8'))
            sender_socket.sendall(
                f"Secure chat session established with {recipient_name}. You can now exchange messages.\n".encode('utf-8'))

            clients[recipient_name]["contact_request"] = None
        else:
            client_socket.sendall("No contact request from this user.\n".encode('utf-8'))
    except Exception as e:
        print(f"[ACCEPT ERROR] {e}")


def handle_decline_request(client_socket, recipient_name, message):
    try:
        _, sender_name = message.split(" ", 1)
        if clients[recipient_name]["contact_request"] == sender_name:
            sender_socket = clients[sender_name]["socket"]
            sender_socket.sendall(f"{recipient_name} declined your chat request.\n".encode('utf-8'))
            clients[recipient_name]["contact_request"] = None
        else:
            client_socket.sendall("No contact request from this user.\n".encode('utf-8'))
    except Exception as e:
        print(f"[DECLINE ERROR] {e}")


def handle_key_exchange(client_socket, sender_name, message):
    try:
        _, target_name, public_key = message.split(" ", 2)
        if target_name in clients:
            clients[target_name]["socket"].sendall(f"KEY_EXCHANGE {sender_name} {public_key}\n".encode('utf-8'))
            clients[target_name]["public_key"] = public_key
        else:
            client_socket.sendall(f"User {target_name} not found.\n".encode('utf-8'))
    except Exception as e:
        print(f"[KEY EXCHANGE ERROR] {e}")


def handle_encrypted_message(client_socket, sender_name, message):
    try:
        for (recipient_name, sender_name_pair) in chat_sessions.keys():
            if sender_name_pair == sender_name:
                if (message.startswith("VOICE_CHUNK") or message.startswith("FILE_CHUNK")):
                    pass
                else:
                    print(f'{sender_name} - {recipient_name} : {message.replace("ENCRYPTED:", "")}')
                recipient_socket = clients[recipient_name]["socket"]
                recipient_socket.sendall((message + '\n').encode('utf-8'))
    except Exception as e:
        print(f"[MESSAGE ERROR] {e}")


def handle_leave(client_socket, name):
    client_socket.sendall("You left the chat.\n".encode('utf-8'))
    sessions_to_remove = [session for session in chat_sessions if name in session]
    for session in sessions_to_remove:
        del chat_sessions[session]
        other_client_name = session[0] if session[1] == name else session[1]
        if other_client_name in clients:
            other_client_socket = clients[other_client_name]["socket"]
            other_client_socket.sendall(f"{name} has left the chat session.\n".encode('utf-8'))


def list_users(client_socket, sender_name):
    user_list = [name for name in clients if name != sender_name]
    client_socket.sendall(f"Users online: {', '.join(user_list)}\n".encode('utf-8'))


def send_greeting(client_socket):
    greeting_message = """
Welcome to the chat server!
Available Commands:
/list - List all users online
/contact <username> - Request to chat with a user
/accept <username> - Accept a chat request
/decline <username> - Decline a chat request
/leave - Leave the chat
/help - Display this help message

Voice Message Commands:
/voice record - To record the message
/voice stop - To stop the recording
/voice send - To send the last recorded voice message
/voice play - To play the last received voice message

File Transfer Commands:
/file input - Select a file to send
/file send - Send the selected file
/file download - Download the received file
"""
    client_socket.sendall((greeting_message + "\n").encode('utf-8'))


def send_help(client_socket):
    help_message = """
Available Commands:
/list - List all users online
/contact <username> - Request to chat with a user
/accept <username> - Accept a chat request
/decline <username> - Decline a chat request
/leave - Leave the chat
/help - Display this help message

Voice Message Commands:
/voice record - To record the message
/voice stop - To stop the recording
/voice send - To send the last recorded voice message
/voice play - To play the last received voice message

File Transfer Commands:
/file input - Select a file to send
/file send - Send the selected file
/file download - Download the received file
"""
    client_socket.sendall((help_message + "\n").encode('utf-8'))


def broadcast(message, exclude=None, sender_socket=None):
    for name, client in clients.items():
        if name != exclude and client["socket"] != sender_socket:
            try:
                client["socket"].sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"[BROADCAST ERROR] {e}")


def remove_client(client_socket, name):
    if name in clients:
        del clients[name]
        broadcast(f"{name} has left the chat.\n", exclude=None)
        print(f"[SERVER] {name} disconnected.")


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 12345))
    server_socket.listen(5)
    print("[SERVER] Server started on localhost:12345.")

    while True:
        client_socket, address = server_socket.accept()
        print(f"[SERVER] Connection from {address}.")
        threading.Thread(target=handle_client, args=(client_socket, address)).start()


if __name__ == "__main__":
    start_server()
