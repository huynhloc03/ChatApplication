import customtkinter as ctk
from tkinter import Text, Tk, filedialog, Menu
import socket
import threading
import random
import time
import re
from tkinter import Button
from tkinter import messagebox
import tkinter as tk
from PIL import Image
from customtkinter import CTkImage
import tkinter.simpledialog as simpledialog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import base64

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title('Chat Application')

HOST = '127.0.0.1'
PORT = 6000
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False
current_username = None
section_frames = {}
current_group = "default_group"
star_state = False
favorite_groups = set()
favorite_states = {}
user_colors = {}
group_members = {}
display_messages = True

public_key_pem= b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvjSF219LvqqdNPlxOxQB
foIybwu3rmmmC+h+DTa7ftDXvhyH4XvOrl5bf13gr14HBO8yKeJWNsOa6MyO/BuX
Y9yesbKA/a1BUwFBGdMpAVOxrxDr7G3VfZqweBqQlk5mEQeRcxYqmoKjffvGen9n
SEhRnyTE/O0eelhvVLA0bqVBOVD6RwnqLPGJC3qqIhHHjbGpKxW/+Z6AhAuWn/fF
bxA5/Syoe5vn/brBl05K/+Tf+VrrsOOKnsC8AYUCYymm8P3SIymQG/mTZbxWe+OE
9M6dQhJ2FhUGBObhazJMwNHyxRhBMRJ1WJSb/NPYt5YZvhq4GOQeK0hD9ENJ1mne
TwIDAQAB
-----END PUBLIC KEY-----
"""
public_key = serialization.load_pem_public_key(
    public_key_pem,
    backend=default_backend()
)

def encrypt_with_rsa(message, public_key):
    encrypted = public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode('utf-8')
    
def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')


center_window(app, 1200, 800)


def switch_group(group_name):
    global current_group, display_messages
    if current_group != group_name:
        display_messages = False
        current_group = group_name
        print(f"Switched to group: {group_name}")
        group_name_label.configure(text=f"Current Group: {group_name}" if group_name != "default_group" else "No Group Selected")
        print("Clearing chat display...")
        chat_display.delete('1.0', tk.END)
        display_messages = True
        createMsg('System', f'Switched to group: {group_name}')
        if group_name in group_members:
            update_member_list(group_members[group_name])
        else:
            member_listbox.delete(0, 'end')

        try:
            encrypted_message=encrypt_with_rsa(f"switch_group:{group_name}", public_key)
            client.sendall(encrypted_message.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Network Error", f"Failed to switch group: {str(e)}")

        star_label.pack_forget() if group_name == "default_group" else star_label.pack(side='left', padx=(10, 5))
        if group_name in favorite_states and favorite_states[group_name]:
            star_label.configure(text="★")
        else:
            star_label.configure(text="☆")

def request_group_messages(group_name):
    try:
        encrypted_message=encrypt_with_rsa(f"request_messages:{group_name}", public_key)
        client.sendall(encrypted_message.encode('utf-8'))
        print(f"Requested latest messages for group {group_name}")
    except Exception as e:
        print(f"Failed to request messages for {group_name}: {str(e)}")

def handle_server_message(msg):
    global group_members
    print("Received message:", msg)

    if msg.startswith("update_members:"):
        try:
            parts = msg.split(":", 2)
            if len(parts) < 3:
                print("Malformed message, skipping:", msg)
                return
            _, group_name, members_data = parts
            members = set(member.strip() for member in members_data.split(','))
            group_members[group_name] = members
            if current_group == group_name:
                update_member_list(members)
        except Exception as e:
            print("Error processing update_members message:", e)
    elif msg.startswith("msg:"):
        _, group, content = msg.split(':', 2)
        if group == current_group:
            createMsg(content)
    elif msg.startswith("clear_display"):
        clear_message_display()

def clear_message_display():
    chat_display.delete('1.0', tk.END)

def add_to_favorites(group_name):
    global favorite_groups
    if group_name not in favorite_groups:
        favorite_groups.add(group_name)
        favorites_section = section_frames.get("Favorites")
        btn = ctk.CTkButton(master=favorites_section, text=group_name, corner_radius=10,
                            command=lambda: switch_group(group_name))
        btn.pack(pady=2, padx=20, fill='x')

def remove_from_favorites(group_name):
    global favorite_groups
    if group_name in favorite_groups:
        favorite_groups.remove(group_name)
        favorites_section = section_frames.get("Favorites")
        for widget in favorites_section.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == group_name:
                widget.destroy()
                break

def go_home():
    switch_group("default_group")
    group_name_label.configure(text="No Group Selected")

def toggle_star():
    global current_group
    if current_group in favorite_states:
        favorite_states[current_group] = not favorite_states[current_group]
    else:
        favorite_states[current_group] = True

    if favorite_states[current_group]:
        star_label.configure(text="★")
        add_to_favorites(current_group)
    else:
        star_label.configure(text="☆")
        remove_from_favorites(current_group)



top_menu = ctk.CTkFrame(master=app, height=50, corner_radius=0)
top_menu.pack(side='top', fill='x', padx=10, pady=5)



group_name_label = ctk.CTkLabel(master=top_menu, text="No Group Selected", anchor="w")
group_name_label.pack(side='left', padx=10, pady=5)

star_label = ctk.CTkLabel(master=top_menu, text="☆", font=("Arial", 14))
star_label.bind("<Button-1>", lambda event: toggle_star())

 

def invite_user():
    username_to_invite = simpledialog.askstring("Invite User", "Enter the username to invite:")
    if username_to_invite:
        group_name = simpledialog.askstring("Group Name", "Enter the group name:")
        if group_name:
            try:
                invitation_command = f"invite:{username_to_invite}:{group_name}"
                encrypted_message=encrypt_with_rsa(invitation_command, public_key)
                client.sendall(encrypted_message.encode('utf-8'))
                print(f"Invitation sent to {username_to_invite} to join {group_name}")
            except Exception as e:
                messagebox.showerror("Network Error", f"Failed to send invitation: {str(e)}")
                print(f"Failed to send invitation to {username_to_invite} for {group_name}: {str(e)}")
    else:
        messagebox.showinfo("Invitation Cancelled", "No username provided.")


invite_button = ctk.CTkButton(master=top_menu, text="+ Invite User", command=invite_user)
invite_button.pack(side='right', padx=30, pady=5)


def get_random_color():
    return f'#{random.randint(0, 255):02X}{random.randint(0, 255):02X}{random.randint(0, 255):02X}'

def assign_color_to_user(username):
    if username not in user_colors:
        user_colors[username] = get_random_color()
    return user_colors[username]

def createMsg(username, msg):
    global display_messages
    if not display_messages:
        print(f"Ignoring message from {username} during group switch")
        return
    chat_display.configure(state='normal')
    timestamp = time.strftime("[%I:%M %p]")
    if "System:" in username:
        user_color = "red"
    else:
        user_color = assign_color_to_user(username)
    chat_display.tag_config(username, foreground=user_color)

    # Check for hyperlinks in the message
    hyperlinks = re.findall(r'(https?://\S+)', msg)
    if hyperlinks:
        for hyperlink in hyperlinks:
            hyperlink_index = msg.find(hyperlink)
            chat_display.insert(tk.END, f'{timestamp} {username}: {msg[:hyperlink_index]}', username)
            # Insert the hyperlink as a clickable button
            button = ctk.CTkButton(master=chat_display, text=hyperlink, command=lambda link=hyperlink: open_link(link))
            chat_display.window_create(tk.END, window=button)
            # Add a space after the hyperlink and continue with the rest of the message
            chat_display.insert(tk.END, ' ' + msg[hyperlink_index + len(hyperlink):] + '\n')
    else:
        chat_display.insert(tk.END, f'{timestamp} {username}: {msg}\n', username)

    chat_display.configure(state='disabled')
    chat_display.yview(tk.END)

def open_link(link):
    import webbrowser
    webbrowser.open(link)
    
# Login
login_window = ctk.CTkToplevel(app)
login_window.title("Login")
center_window(login_window, 400, 200)
login_window.attributes('-topmost', True)


username_entry = ctk.CTkEntry(login_window, placeholder_text="Enter your username")
username_entry.pack(pady=10)

# Add entry widgets for host and port
host_entry = ctk.CTkEntry(login_window, placeholder_text="Enter the host")
host_entry.pack(pady=10)

port_entry = ctk.CTkEntry(login_window, placeholder_text="Enter the port")
port_entry.pack(pady=10)

def on_login():
    global connected, current_username, HOST, PORT
    username = username_entry.get().strip()
    host = host_entry.get().strip()  # Get the host from the entry widget
    port = port_entry.get().strip()  # Get the port from the entry widget
    
    if username == '':
        messagebox.showinfo("Username Required", "Please enter a username before connecting.")
    elif host == '' or port == '':
        messagebox.showinfo("Host and Port Required", "Please enter a host and port before connecting.")
    else:
        try:
            PORT = int(port)  # Convert port to integer
            client.connect((host, PORT))  # Connect to the specified host and port
            encrypted_message=encrypt_with_rsa(username, public_key)
            client.sendall(encrypted_message.encode('utf-8'))
            connected = True
            current_username = username
            update_profile(username)
            createMsg('Server', 'Connected to server')
            threading.Thread(target=messageListenerFromServer, daemon=True).start()
            login_window.destroy()
        except Exception as e:
            messagebox.showerror('Unable to connect', f'Error: {str(e)}')
            connected = False
def update_profile(username):
    username_label.configure(text=username)

login_button = ctk.CTkButton(login_window, text="Login", command=on_login)
login_button.pack(pady=10)

def messageListenerFromServer():
    global connected
    while connected:
        try:
            msg = client.recv(1024).decode('utf-8')
            print(f"Received message: {msg}")
            
            if msg.startswith("update_group:invite:"):
                handle_invitation_message(msg)
                continue
            elif msg.startswith("update_members:"):
                members_string = msg.split(':', 1)[1]
                print(f"Debug - Members string: {members_string}")
                members = members_string.split(',')
                print(f"Debug - Members to update: {members_string.split(',') }")
                update_member_list(members)
                continue

            parts = msg.split(':', 2)
            if len(parts) == 3:
                command, group, content = parts
                print(f"Command, Group, Content: {command}, {group}, {content}")
                if command == "msg" and group == current_group:
                    username, message = content.split(':', 1)
                    createMsg(username, message)
                elif command == "system" and group == current_group:
                    createMsg("System", content)
                elif command == "update" and group == current_group:
                    print("Group update received for current group.")
            elif len(parts) == 2:
                command, content = parts
                if command == "System":
                    createMsg("System", content)
            else:
                print("Unhandled message format or wrong number of parts in message.")
        except Exception as e:
            createMsg('System', f"Error: {str(e)}")
            connected = False
            client.close()



            
def handle_invitation_message(msg):
    print(f"Handling invitation message at {current_username}: {msg}")
    parts = msg.split(':')
    if len(parts) == 5 and parts[0] == "update_group" and parts[1] == "invite":
        sender = parts[2]
        receiver = parts[3]
        group_name = parts[4]
        print(f"Received invite details: Sender: {sender}, Receiver: {receiver}, Group: {group_name}")
        if receiver == current_username:
            handle_received_invitation(sender, group_name)
        else:
            print(f"Invitation not for me: intended for {receiver}, I am {current_username}")

def handle_received_invitation(sender, group_name):
    print(f"Invitation received by {current_username} from {sender} to join {group_name}")
    response = messagebox.askyesno("Group Invitation", f"{sender} has invited you to join '{group_name}'. Do you want to accept?")
    if response:
        print(f"{current_username} accepted the invitation to join {group_name}")
        add_new_group(group_name)
        try:
            encrypted_message=encrypt_with_rsa(f"join_group:{group_name}", public_key)
            client.sendall(encrypted_message.encode('utf-8'))
            createMsg('System', f"You joined '{group_name}'")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to join '{group_name}': {str(e)}")
    else:
        createMsg('System', "Invitation declined.")



def add_new_group(group_name):
    if group_name not in section_frames:
        add_group_to_sidebar(group_name)
        try:
            encrypted_message=encrypt_with_rsa(f"create_group:{group_name}", public_key)
            client.sendall(encrypted_message.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to create group on server: {str(e)}")


def add_group_to_sidebar(group_name):
    groups_section = section_frames.get("Groups")
    if groups_section:
        btn = ctk.CTkButton(master=groups_section, text=group_name, corner_radius=10,
                            command=lambda: switch_group(group_name))
        btn.pack(pady=2, padx=20, fill='x')



def sendMessage(event=None):
    if connected and current_group:
        msg = chat_input.get()
        if msg:
            if len(msg) > CHARACTER_LIMIT:
                messagebox.showerror("Message Too Long", f"Message exceeds maximum length of {CHARACTER_LIMIT} characters.")
            else:
                encrypted_message = encrypt_with_rsa(f"msg:{current_group}:{msg}", public_key)
                print(f"Sending message: {msg}")
            try:
                client.sendall(encrypted_message.encode('utf-8'))
                chat_input.delete(0, 'end')
                update_character_count()
            except Exception as e:
                messagebox.showerror("Send Error", str(e))
        else:
            messagebox.showinfo("Warning", "Message cannot be empty!")
    else:
        messagebox.showwarning("Not Connected", "You are not connected to the server or not part of any group.")


def create_section(container, title, items):
    section_frame = ctk.CTkFrame(master=container, fg_color="#333333", corner_radius=10)
    section_frame.pack(pady=10, padx=10, fill='x')
    section_frames[title] = section_frame

    header_frame = ctk.CTkFrame(master=section_frame)
    header_frame.pack(fill='x', padx=10, pady=(5, 10))
    label = ctk.CTkLabel(master=header_frame, text=title, anchor='w', fg_color=None, font=("Roboto Medium", 12))
    label.pack(side='left')
    if title != "Favorites":
        add_button = ctk.CTkButton(master=header_frame, text="+", width=10, command=lambda: add_item(title))
        add_button.pack(side='right')

    for item in items:
        btn = ctk.CTkButton(master=section_frame, text=item, corner_radius=10,
                            command=lambda item=item: switch_group(item))
        btn.pack(pady=2, padx=20, fill='x')



def update_ui_for_group(group_name):
    chat_display.configure(state='normal')
    chat_display.delete('1.0', tk.END)
    chat_display.insert(tk.END, f"Switched to group: {group_name}\n")
    chat_display.configure(state='disabled')
    group_name_label.configure(text=f"Current Group: {group_name}")



def add_item_to_ui(section_title, item):
    section_frame = section_frames[section_title]
    btn = ctk.CTkButton(master=section_frame, text=item, corner_radius=10,
                        command=lambda item=item: switch_group(item))
    btn.pack(pady=2, padx=20, fill='x')


def add_item(section_title):
    new_item = simpledialog.askstring("Add New Group", "Enter a name for the new group:")
    if new_item:
        app.after(0, add_item_to_ui, section_title, new_item)






leftmost_sidebar = ctk.CTkFrame(master=app, width=200, corner_radius=0)
leftmost_sidebar.pack(side='left', fill='y', padx=10)
home_button = ctk.CTkButton(master=leftmost_sidebar, text="Home", command=go_home)
home_button.pack(pady=(10, 0), padx=10, fill='x')


create_section(leftmost_sidebar, "Favorites",[])
create_section(leftmost_sidebar, "Groups", [])

def change_profile_picture():
    global image_path, ctk_image, avatar
    new_image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
    if new_image_path:
        image = Image.open(new_image_path)
        image = image.resize((75, 75), Image.Resampling.LANCZOS)
        ctk_image = CTkImage(image)
        avatar.configure(image=ctk_image)
        avatar.image = ctk_image
        image_path = new_image_path
        
# Profile
profile_frame = ctk.CTkFrame(master=leftmost_sidebar, fg_color="#333333", corner_radius=10)
profile_frame.pack(side='bottom', fill='x', padx=10, pady=10)

avatar_frame = ctk.CTkFrame(master=profile_frame, fg_color="#333333", corner_radius=10)
avatar_frame.pack(side='left', padx=10, pady=10)

image_path = "D:\\ChatroomUpdated\\CustomTkinter-master\\profile.jpg"
image = Image.open(image_path)
image = image.resize((75, 75), Image.Resampling.LANCZOS)
ctk_image = CTkImage(image)
avatar = ctk.CTkLabel(master=avatar_frame, image=ctk_image, text="")
avatar.image = ctk_image
avatar.pack(side='left')
avatar.bind("<Button-1>", lambda event: change_profile_picture())
username_label = ctk.CTkLabel(master=profile_frame, text="Username", fg_color=None, font=("Roboto Medium", 12))
username_label.pack(side='left', padx=10)

# Info sidebar
info_sidebar = ctk.CTkFrame(master=app, width=200, corner_radius=0)
info_sidebar.pack(side='right', fill='y', padx=10)

def update_member_list(members):
    unique_members = set()
    member_listbox.delete(0, 'end')

    if isinstance(members, str):
        members = members.split(',')
    
    for member in members:
        cleaned_member = member.strip()
        if ':' in cleaned_member:
            _, cleaned_member = cleaned_member.split(':')
        unique_members.add(cleaned_member)

    for member in unique_members:
        member_listbox.insert('end', member)
        print("Adding unique member:", member)
 

def create_info_section(container, title):
    section_frame = ctk.CTkFrame(master=container, fg_color="#333333", corner_radius=10)
    section_frame.pack(pady=10, padx=10, fill='x')

    label = ctk.CTkLabel(master=section_frame, text=title, anchor='w', fg_color=None, font=("Roboto Medium", 12))
    label.pack(pady=(5, 10), padx=10, fill='x')

    if title == "Members":
        global member_listbox
        member_listbox = tk.Listbox(section_frame, bg="#333333", fg="white", height=10)
        member_listbox.pack(padx=20, pady=10, fill='x', expand=True)
    else:
        dropdown = ctk.CTkOptionMenu(section_frame, values=["Option 1", "Option 2"], button_color="#555555")
        dropdown.pack(padx=20, pady=10, fill='x')

create_info_section(info_sidebar, "Members")


# Chat Area
chat_area = ctk.CTkFrame(master=app, fg_color="#333333")
chat_area.pack(side='left', fill='both', expand=True)
chat_display = Text(chat_area, height=20, bg='#404040', fg='white', insertbackground='white')
chat_display.pack(pady=15, padx=20, fill='both', expand=True)
chat_display.tag_config('User', foreground='white')
character_count_label = ctk.CTkLabel(master=chat_area, text="0/300", fg_color='transparent')
character_count_label.pack(padx=(20, 5), pady=(3, 0), anchor='e')

def addEmoji(emoji_symbol):
    chat_input.insert(tk.END, emoji_symbol)

emoji_menu = Menu(app, tearoff=0)
emoji_menu.add_command(label="😀", command=lambda: addEmoji("😀"))
emoji_menu.add_command(label="😂", command=lambda: addEmoji("😂"))
emoji_menu.add_command(label="😍", command=lambda: addEmoji("😍"))
emoji_menu.add_command(label="😎", command=lambda: addEmoji("😎"))
emoji_menu.add_command(label="🤔", command=lambda: addEmoji("🤔"))
emoji_menu.add_command(label="🙌", command=lambda: addEmoji("🙌"))
emoji_menu.add_command(label="🎉", command=lambda: addEmoji("🎉"))
emoji_menu.add_command(label="👍", command=lambda: addEmoji("👍"))
emoji_menu.add_command(label="👎", command=lambda: addEmoji("👎"))
emoji_menu.add_command(label="❤️", command=lambda: addEmoji("❤️"))

emoji_button = tk.Button(master=chat_area, text="😀")
emoji_button.pack(side="right", padx=5, pady=5)

# Adjust the width of the chat input widget
chat_input = ctk.CTkEntry(master=chat_area, width=50)  # Set a smaller width
chat_input.pack(pady=15, padx=(20, 5), fill='x')  # Adjust the padx to give space for the emoji button
chat_input.bind('<Return>', lambda event: sendMessage())

# Attach the menu to the emoji button
emoji_button.bind("<Button-1>", lambda e: emoji_menu.post(e.x_root, e.y_root))

CHARACTER_LIMIT = 300

def update_character_count(event=None):
    # Use the after method to add a slight delay before updating the character count
    chat_input.after(10, update_character_count_helper)

def update_character_count_helper():
    message_length = len(chat_input.get())
    character_count_label.configure(text=f"{message_length}/{CHARACTER_LIMIT}")
    if message_length > CHARACTER_LIMIT:
        character_count_label.configure(fg_color='red')
    else:
        character_count_label.configure(fg_color='transparent')
        
# Bind the callback function to the text input box
chat_input.bind('<Key>', update_character_count)


def on_app_close():
    if connected:
        client.close()
    app.destroy()
    
def toggle_dark_mode():
    current_mode = ctk.get_appearance_mode()
    if current_mode == "Dark":
        ctk.set_appearance_mode("Light")
        app.configure(bg="white")  # Change the background color to white for light mode
        chat_display.configure(bg="white", fg="black")  # Adjust chat display colors for light mode
        # You can add more widgets to adjust their appearance for light mode
        dark_mode_button.configure(text="Dark Mode")  # Change the button text to "Dark Mode"
    else:
        ctk.set_appearance_mode("Dark")
        app.configure(bg="#333333")  # Change the background color to dark for dark mode
        chat_display.configure(bg="#404040", fg="white")  # Adjust chat display colors for dark mode
        # You can add more widgets to adjust their appearance for dark mode
        dark_mode_button.configure(text="Light Mode")  # Change the button text to "Light Mode"

# Create the "Toggle Dark Mode" button
initial_mode = ctk.get_appearance_mode()
if initial_mode == "Dark":
    dark_mode_button_text = "Light Mode"  # Set the initial text to "Light Mode" if the initial mode is dark
else:
    dark_mode_button_text = "Dark Mode"  # Set the initial text to "Dark Mode" if the initial mode is light
dark_mode_button = ctk.CTkButton(master=info_sidebar, text=dark_mode_button_text, command=toggle_dark_mode)
dark_mode_button.pack(pady=10)

def save_chat_log():
    chat_log = chat_display.get("1.0", "end-1c")
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
    if file_path:
        with open(file_path, "w") as file:
            file.write(chat_log)
        messagebox.showinfo("Save Successful", "Chat log saved successfully.")
        
save_button = ctk.CTkButton(master=info_sidebar, text="Save Chat Log", command=save_chat_log)
save_button.pack(pady=10)

if __name__ == "__main__":
    app.protocol("WM_DELETE_WINDOW", on_app_close)
    app.mainloop()
