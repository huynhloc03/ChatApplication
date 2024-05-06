import socket
import threading

HOST = '127.0.0.1'
PORT = 6000
LISTENER_CAPACITY = 10

groups = {'default_group': {}}  # Initialize with a default group
user_sockets = {}

def message_listener(client, username):
    try:
        while True:
            msg = client.recv(1024).decode('utf-8')
            if not msg:
                break  # If the message is empty, exit the loop

            if msg.startswith("invite:"):
                _, invitee, group = msg.split(':')
                group = group.strip()
                handle_invitation(username, invitee.strip(), group)

            elif msg.startswith("msg:"):
                _, group, message_content = msg.split(':', 2)
                group = group.strip()
                message_content = message_content.strip()
                sentMessage = f"{username}: {message_content}"
                send_message_group(sentMessage, group)

            else:
                print(f"Received unhandled message format from {username}: {msg}")
    except Exception as e:
        print(f"Error with {username}: {e}")
    finally:
        client.close()
        leave_group(username, "default_group")  # Remove from default group on disconnect
        print(f"{username} has disconnected.")

def handle_invitation(sender, recipient_username, group_name):
    recipient_socket = get_client_socket(recipient_username)
    if recipient_socket:
        invite_message = f"update_group:invite:{sender}:{recipient_username}:{group_name}"
        send_message_client(recipient_socket, invite_message)
    else:
        print(f"No active connection found for {recipient_username}")

def get_client_socket(username):
    return user_sockets.get(username, None)

def send_message_client(client, message):
    client.sendall(message.encode('utf-8'))

def send_message_group(message, group_name):
    if group_name in groups:
        for username, client in groups[group_name].items():
            try:
                client.sendall(message.encode('utf-8'))
                print(f"Message sent to {username}")
            except Exception as e:
                print(f"Failed to send message to {username}: {e}")
    else:
        print(f"Group '{group_name}' not found")

def join_group(username, client, group_name):
    if group_name not in groups:
        groups[group_name] = {}
    groups[group_name][username] = client
    print(f"{username} joined {group_name}, total members: {len(groups[group_name])}")
    send_system_message(f"{username} has joined the chat", group_name)
    update_clients_group_list(group_name)

def leave_group(username, group_name):
    if group_name in groups and username in groups[group_name]:
        del groups[group_name][username]
        if not groups[group_name]:  # Remove group if empty
            del groups[group_name]
        send_system_message(f"{username} has left the chat", group_name)

def send_system_message(message, group_name):
    if group_name in groups:
        formatted_message = f"System: {message}"
        for client in groups[group_name].values():
            send_message_client(client, formatted_message)

def update_clients_group_list(group_name):
    message = f"update_group:{group_name}"
    for client in groups[group_name].values():
        send_message_client(client, message)

def client_handler(client):
    username = client.recv(1024).decode('utf-8').strip()
    user_sockets[username] = client  # Track the user's socket
    join_group(username, client, "default_group")  # Automatically add to default group
    try:
        message_listener(client, username)
    except Exception as e:
        print(f"Exception handling client {username}: {e}")
    finally:
        if username in user_sockets:
            del user_sockets[username]  # Clean up when the user disconnects
        client.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(LISTENER_CAPACITY)
    print(f"Server started on {HOST}:{PORT}")
    while True:
        client, addr = server.accept()
        print(f'Connected with {addr[0]}:{str(addr[1])}')
        threading.Thread(target=client_handler, args=(client,)).start()

if __name__ == '__main__':
    main()
