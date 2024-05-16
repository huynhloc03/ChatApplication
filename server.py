import socket
import threading
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import base64

HOST = '127.0.0.1'
PORT = 6000
LISTENER_CAPACITY = 10

groups = {
    'default_group': {},
    }

user_sockets = {}
user_current_group = {}

private_key_pem = b"""-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC+NIXbX0u+qp00
+XE7FAF+gjJvC7euaaYL6H4NNrt+0Ne+HIfhe86uXlt/XeCvXgcE7zIp4lY2w5ro
zI78G5dj3J6xsoD9rUFTAUEZ0ykBU7GvEOvsbdV9mrB4GpCWTmYRB5FzFiqagqN9
+8Z6f2dISFGfJMT87R56WG9UsDRupUE5UPpHCeos8YkLeqoiEceNsakrFb/5noCE
C5af98VvEDn9LKh7m+f9usGXTkr/5N/5Wuuw44qewLwBhQJjKabw/dIjKZAb+ZNl
vFZ744T0zp1CEnYWFQYE5uFrMkzA0fLFGEExEnVYlJv809i3lhm+GrgY5B4rSEP0
Q0nWad5PAgMBAAECggEBAKPFe6AIrKJuK1BKmzlgH207U4uTzkNJymQkeiyMfOJT
lf+md0UqIiq3Khc/0M+OqYKRJmMz9EHRKJfcUh028KJWevnMFg7W2BFNWi2PSJZQ
5wQzEMCRTaqJv/qZ/Pa+aFmvZ4hthJ9nbrhySlJ9UoPFaSobMdYJoR18+dc0pODC
wFWpudIsXgfKRIf2Q9jHMRPQzfBmHks9h8k/EqVWI/0c2SnNTLX3dDlKfyEb37o/
hZvwRC9od087pb//ZUwqk5CWwkb5BlsinZYKMEI4c8gP+lAi1+Gsl/hfAE/kt2fy
d++O9gareE05Zxv/00H3fWwP3lso5fmSCS/HGC/kNuECgYEA+9GULdPgNwI5aRyy
eObPYvrMa4uBSlHO3m3l8mjGD34+2pCPi/SiUvXnrqgknAoc3WEMs7fpfZ93E6M/
Rr2wfWbIBtuYYHat+oNy7XVAXN4WBKncFIR2Fnj3ctTomFWMqgUhW8mnT2ZbTknR
3MomFyg7KhIQmrpeiq5LgnZojh8CgYEAwV0KLIhUhUcXGmR1sHCMBOsB3kVG86/u
uQ1bCLlIxzlqGmn5zpYCO5Pb+2nSJP6mPDjkCYcO01LnQweVv+BlbKZwvVuTuHrp
7/6Cq7oPQH5k7dRABFZ7rs710jCysha1JT7n1OozFYnWGBCaq1NJenXEEdlDZEpG
KgKxOFaZSdECgYBaKWLdubPY3kICAZVhNnrgnJ2ej/d9zaa8+ypOzfbES1Zj2Uic
Or336DXI0kkxWWmWVg4/NsUyBmuTK2sXgAl2DNvnoK6BM1z9ih0XKlkeJyJJDyxO
aFMDntIyWkrhaBgSM/4KqDvwcNyWPlYWsIZM2km8uXUagUoia1972bt7zwKBgBeo
3bzTNZxVNYN6NVhQfSGA6+qZiXP52/jypGft2/TclpoCy5k2i7Fkhy89JIR4UDjg
MS7lQrAi3b8651ziBScFOphA41NYXtWJy81dZ85ZaNoc9XRSbLHYCwYcBVF7K9ER
4GYR/gwtoG+zYGmEOGJulH4mmnNkDy/Gwo6FMh5xAoGBANS2zWhn6Z99+liUxbzc
Bs/TpQL41Hr1byO4vHkIjvclp958ImUrmyIKWE6D3ZIDyE4wWA05qciusJGIDD2y
8KH92fg10woDXC5sBDfmlyOolGyL++s+s2DfI/Hk7LFmwfyniBdvWkGVxiW1I9Gi
vCDZzsE++jA08VHXBg+jY9Vh
-----END PRIVATE KEY-----"""
private_key = serialization.load_pem_private_key(
    private_key_pem,
    password=None,
    backend=default_backend()
)

def decrypt_with_rsa(encrypted_message, private_key):
    return private_key.decrypt(
        encrypted_message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=SHA256()),
            algorithm=SHA256(),
            label=None
        )
    )
    
def message_listener(client, username):
    try:
        while True:
            msg = client.recv(1024)
            if not msg:
                break
            try:
                decrypted_msg = decrypt_with_rsa(base64.b64decode(msg), private_key)
                processed_msg = decrypted_msg.decode('utf-8')
            except Exception as e:
                print(f"Decryption failed for {username} with error {e}")
                continue
            if processed_msg.startswith("invite:"):
                _, invitee, group = processed_msg.split(':')
                group = group.strip()
                handle_invitation(username, invitee.strip(), group)

            elif processed_msg.startswith("msg:"):
                _, group, message_content = processed_msg.split(':', 2)
                group = group.strip()
                message_content = message_content.strip()
                sentMessage = f"{username}: {message_content}"
                send_message_group(sentMessage, group)

            elif processed_msg.startswith("switch_group:"):
                _, group_name = processed_msg.split(':')
                group_name = group_name.strip()
                user_current_group[username] = group_name
                join_group(username, client, group_name)

            elif processed_msg.startswith("create_group:"):
                _, group_name = processed_msg.split(':', 1)
                create_group(group_name.strip(), username, client)

            elif processed_msg.startswith("update_members:"):
                _, members_string = processed_msg.split(':', 1)
                members = members_string.split(',')
                print(f"Received and parsed members: {members}")
                update_member_list(members)

            else:
                print(f"Received unhandled message format from {username}: {processed_msg}")

    except Exception as e:
        print(f"Error with {username}: {e}")
    finally:
        if username in user_current_group:
            leave_group(username, user_current_group[username])
        client.close()
        print(f"{username} has disconnected.")


def create_group(group_name, username, client):
    if group_name not in groups:
        groups[group_name] = {}
        print(f"New group '{group_name}' created by {username}.")
        join_group(username, client, group_name)  
    else:
        print(f"Group '{group_name}' already exists.")

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
            if user_current_group.get(username) == group_name:
                try:
                    formatted_msg = f"msg:{group_name}:{message}"
                    client.sendall(formatted_msg.encode('utf-8'))
                    print(f"Message '{message}' sent to {username} in group {group_name}")
                except Exception as e:
                    print(f"Failed to send message to {username}: {e}")
    else:
        print(f"Group '{group_name}' not found")



def send_system_message(message, group_name='default_group'):
    formatted_message = f"system:{group_name}:{message}"
    for client in groups[group_name].values():
        send_message_client(client, formatted_message)

def update_member_list(group_name):
    members = list(groups[group_name].keys())  
    message = f"update_members:{','.join(members)}"
    for username, client in groups[group_name].items():
        send_message_client(client, message)

def join_group(username, client, group_name):
    if group_name not in groups:
        groups[group_name] = {}
    groups[group_name][username] = client
    user_current_group[username] = group_name
    send_system_message(f"{username} has joined the chat", group_name)
    update_member_list(group_name)  
    broadcast_user_list()  


def leave_group(username, group_name):
    if group_name in groups and username in groups[group_name]:
        del groups[group_name][username]
        send_system_message(f"{username} has left the chat", group_name)
        update_member_list(group_name)  
        if not groups[group_name]:  
            del groups[group_name]
        print(f"{username} has left {group_name}.")


def broadcast_user_list():
    users = list(user_sockets.keys())
    print(f"Current users list: {users}")  
    update_msg = "update_members:" + ",".join(users)
    print(f"Broadcasting user list update: {update_msg}")
    for username, socket in user_sockets.items():
        try:
            socket.sendall(update_msg.encode('utf-8'))
            print(f"Broadcasted user list to {username}: {update_msg}")  
        except Exception as e:
            print(f"Failed to send user list update to {username}: {str(e)}")




def send_system_message(message, group_name):
    if group_name in groups:
        formatted_message = f"System: {message}"
        for client in groups[group_name].values():
            send_message_client(client, formatted_message)

def update_clients_group_list(group_name):
    message = f"update:group_list:{group_name}"
    for client in groups[group_name].values():
        send_message_client(client, message)


def client_handler(client):
    try:
        Decrypted_username = decrypt_with_rsa(base64.b64decode(client.recv(1024)), private_key)
        username = Decrypted_username.decode('utf-8').strip()
        if not username:
            raise ValueError("Username not provided")
        if username in user_sockets:
            raise ValueError("Username already connected")
        
        user_sockets[username] = client
        join_group(username, client, "default_group")
        message_listener(client, username)
    except Exception as e:
        print(f"Exception handling client {username if 'username' in locals() else 'unknown'}: {e}")
    finally:
        if 'username' in locals() and username in user_sockets:
            del user_sockets[username]
        if 'username' in locals() and username in user_current_group:
            del user_current_group[username]
        client.close()
        print(f"{username if 'username' in locals() else 'unknown'} has disconnected.")

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
