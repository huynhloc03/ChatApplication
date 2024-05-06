import customtkinter as ctk
from tkinter import Text, Tk
import socket
import threading
import random
from tkinter import messagebox
import tkinter as tk
from PIL import Image
from customtkinter import CTkImage
import tkinter.simpledialog as simpledialog

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()  
app.title('Chat Application')



HOST = '127.0.0.1'
PORT = 6000
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False
current_username = None  

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')


center_window(app, 1200, 800)

current_group = "default"  # Default group



def switch_group(group_name):
    global current_group
    current_group = group_name
    group_name_label.configure(text=f"Current Group: {group_name}")
    chat_display.delete('1.0', tk.END)
    createMsg('System', f'Switched to group: {group_name}')

top_menu = ctk.CTkFrame(master=app, height=50, corner_radius=0)
top_menu.pack(side='top', fill='x', padx=10, pady=5)

group_name_label = ctk.CTkLabel(master=top_menu, text="No Group Selected", anchor="w")
group_name_label.pack(side='left', padx=10, pady=5)


def invite_user():
    username_to_invite = simpledialog.askstring("Invite User", "Enter the username to invite:")
    if username_to_invite:
        group_name = simpledialog.askstring("Group Name", "Enter the group name:")
        if group_name:
            try:
                invitation_command = f"invite:{username_to_invite}:{group_name}"
                client.sendall(invitation_command.encode('utf-8'))
                print(f"Invitation sent to {username_to_invite} to join {group_name}")
            except Exception as e:
                messagebox.showerror("Network Error", f"Failed to send invitation: {str(e)}")
                print(f"Failed to send invitation to {username_to_invite} for {group_name}: {str(e)}")
    else:
        messagebox.showinfo("Invitation Cancelled", "No username provided.")


invite_button = ctk.CTkButton(master=top_menu, text="+ Invite User", command=invite_user)
invite_button.pack(side='right', padx=10, pady=5)


def get_random_color():
    return f'#{random.randint(0, 255):02X}{random.randint(0, 255):02X}{random.randint(0, 255):02X}'

user_colors = {}

def assign_color_to_user(username):
    if username not in user_colors:
        user_colors[username] = get_random_color()
    return user_colors[username]

def createMsg(username, msg):
    chat_display.configure(state='normal')
    if "System:" in username:
        user_color = "red"  
    else:
        user_color = assign_color_to_user(username)
    chat_display.tag_config(username, foreground=user_color)
    chat_display.insert(tk.END, f'{username}: ', username)
    chat_display.insert(tk.END, f'{msg}\n')
    chat_display.configure(state='disabled')
    chat_display.yview(tk.END)




# Login
login_window = ctk.CTkToplevel(app)
login_window.title("Login")
center_window(login_window, 400, 200)  
login_window.attributes('-topmost', True) 


username_entry = ctk.CTkEntry(login_window, placeholder_text="Enter your username")
username_entry.pack(pady=20)

def on_login():
    global connected, current_username
    username = username_entry.get().strip()
    
    if username == '':
        messagebox.showinfo("Username Required", "Please enter a username before connecting.")
    else:
        try:
            client.connect((HOST, PORT))
            client.sendall(username.encode('utf-8'))
            connected = True
            current_username = username  
            update_profile(username)
            createMsg('Server', 'Connected to server')
            threading.Thread(target=messageListenerFromServer, daemon=True).start()
            login_window.destroy()
        except Exception as e:
            messagebox.showerror('Unable to connect', f'Error: {str(e)}')
            connected = False

current_group = 'default_group'

def update_profile(username):
    username_label.configure(text=username)  

login_button = ctk.CTkButton(login_window, text="Login", command=on_login)
login_button.pack(pady=20)

def messageListenerFromServer():
    global connected
    while connected:
        try:
            msg = client.recv(1024).decode('utf-8')
            print(f"Received message: {msg}")  

            if msg.startswith("update_group:invite:"):
                handle_invitation_message(msg)
            elif ':' in msg:
                parts = msg.split(':', 1)
                if len(parts) == 2:
                    username, msgContent = parts
                    createMsg(username, msgContent)
                else:
                    createMsg('System', "Malformed message received.")
            else:
                createMsg('System', "Unhandled message format: " + msg)
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
            client.sendall(f"join_group:{group_name}".encode('utf-8'))
            createMsg('System', f"You joined '{group_name}'")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to join '{group_name}': {str(e)}")
    else:
        createMsg('System', "Invitation declined.")



def add_new_group(group_name):
    
    if group_name not in section_frames:
        add_group_to_sidebar(group_name)

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
            full_message = f"msg:{current_group}:{msg}"
            print(f"Sending message: {full_message}")
            try:
                client.sendall(full_message.encode('utf-8'))
                # createMsg(current_username, msg)  
                chat_input.delete(0, 'end')
            except Exception as e:
                messagebox.showerror("Send Error", str(e))
        else:
            messagebox.showinfo("Warning", "Message cannot be empty!")
    else:
        messagebox.showwarning("Not Connected", "You are not connected to the server or not part of any group.")



def create_section(container, title, items=[]):
    if title not in section_frames:
        section_frame = ctk.CTkFrame(master=container, fg_color="#333333", corner_radius=10)
        section_frame.pack(pady=10, padx=10, fill='x')
        section_frames[title] = section_frame  
        header_frame = ctk.CTkFrame(master=section_frame)
        header_frame.pack(fill='x', padx=10, pady=(5, 10))
        label = ctk.CTkLabel(master=header_frame, text=title, anchor='w', fg_color=None, font=("Roboto Medium", 12))
        label.pack(side='left')
        add_button = ctk.CTkButton(master=header_frame, text="+", width=10)
        add_button.pack(side='right')



section_frames = {}


def create_section(container, title, items):
    section_frame = ctk.CTkFrame(master=container, fg_color="#333333", corner_radius=10)
    section_frame.pack(pady=10, padx=10, fill='x')
    section_frames[title] = section_frame 

    header_frame = ctk.CTkFrame(master=section_frame)
    header_frame.pack(fill='x', padx=10, pady=(5, 10))
    label = ctk.CTkLabel(master=header_frame, text=title, anchor='w', fg_color=None, font=("Roboto Medium", 12))
    label.pack(side='left')

    add_button = ctk.CTkButton(master=header_frame, text="+", width=10, command=lambda: add_item(title))
    add_button.pack(side='right')

    for item in items:
        btn = ctk.CTkButton(master=section_frame, text=item, corner_radius=10,
                            command=lambda item=item: switch_group(item))
        btn.pack(pady=2, padx=20, fill='x')

def switch_group(group_name):
    print(f"Switching to group: {group_name}")  
    app.after(0, update_ui_for_group, group_name)

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
create_section(leftmost_sidebar, "Favorites", [])  
create_section(leftmost_sidebar, "Direct Messages", [])
create_section(leftmost_sidebar, "Groups", [])




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

username_label = ctk.CTkLabel(master=profile_frame, text="Username", fg_color=None, font=("Roboto Medium", 12))
username_label.pack(side='left', padx=10)

# Info sidebar
info_sidebar = ctk.CTkFrame(master=app, width=200, corner_radius=0)
info_sidebar.pack(side='right', fill='y', padx=10)



def create_info_section(container, title, options):
    section_frame = ctk.CTkFrame(master=container, fg_color="#333333", corner_radius=10)
    section_frame.pack(pady=10, padx=10, fill='x')
    label = ctk.CTkLabel(master=section_frame, text=title, anchor='w', fg_color=None, font=("Roboto Medium", 12))
    label.pack(pady=(5, 10), padx=10, fill='x')
    dropdown = ctk.CTkOptionMenu(section_frame, values=options, button_color="#555555")
    dropdown.pack(padx=20, pady=10, fill='x')



create_info_section(info_sidebar, "Members", ["John Doe", "Jane Smith", "Alice Johnson"])
create_info_section(info_sidebar, "Pinned Messages", ["Message 1", "Message 2", "Message 3"])
create_info_section(info_sidebar, "Files", ["File 1", "File 2", "File 3"])

# Chat Area
chat_area = ctk.CTkFrame(master=app, fg_color="#333333")
chat_area.pack(side='left', fill='both', expand=True)
chat_display = Text(chat_area, height=20, bg='#404040', fg='white', insertbackground='white')
chat_display.pack(pady=20, padx=20, fill='both', expand=True)
chat_display.tag_config('User', foreground='white')
chat_input = ctk.CTkEntry(master=chat_area, width=400)
chat_input.pack(pady=20, padx=20, fill='x')
chat_input.bind('<Return>', lambda event: sendMessage())

def on_app_close():
    if connected:
        client.close()
    app.destroy()


if __name__ == "__main__":
    # Initialize and display the main window
    app.protocol("WM_DELETE_WINDOW", on_app_close)
    # app.after(1000, test_invitation_handling)  
    app.mainloop()