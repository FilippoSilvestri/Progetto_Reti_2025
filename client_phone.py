import socket
import tkinter as tk
from threading import Thread
import struct

# creazione server
#server_ip = "192.168.56.241"
server_ip = "192.168.56.185"
server_port = 12345
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))
print(f"Connected to server: {server_ip}:{server_port}")

def send(text):
    message = text
    client_socket.send(message.encode())
def stop_recording():
    message = "stop_recording"
    client_socket.send(message.encode())
def close():
    try:
        client_socket.close()
    except Exception as e:
       root.destroy()
def update_prediction(message):
    if message =="skiing":
        color = "green"
    else:
        color = "red"
    canvas.itemconfig(rect2, fill=color)
    canvas.itemconfig(rect2_text, text=message)

def receive_message():
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if message:
                root.after(0, update_prediction, message)
        except Exception as e:
            break
           
Thread(target=receive_message, daemon=True).start()


root = tk.Tk()
root.title("Reti project App")
frame = tk.Frame(root)
frame.pack(pady=10)

entry = tk.Entry(frame, width=30)
entry.pack(side=tk.LEFT, padx=5)

name_button = tk.Button(frame, text="Start", command=lambda: send(entry.get()))
name_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(root, text="Stop", command=stop_recording, fg="white", bg="red")
stop_button.pack(pady=10)

canvas = tk.Canvas(root, width=300, height=300)
canvas.pack(pady=10)

rect1 = canvas.create_rectangle(50, 20, 250, 70, fill="blue", outline="black")
rect2 = canvas.create_rectangle(50, 220, 250, 270, fill="grey", outline="black")

rect2_text = canvas.create_text(150, 45, text="prediction", fill="white")

root.protocol("WM_DELETE_WINDOW", close)
root.mainloop()

#client_socket.close()
