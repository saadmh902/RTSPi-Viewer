import cv2
import threading
from tkinter import Tk, Label, Canvas, Toplevel, PhotoImage
from PIL import Image, ImageTk
import math
import os
import requests

# RTSP login and streams
rtsp_login = "user:pass"  # Change this to your RTSP login credentials
ip = "10.0.0.1" #change to your ip
streams = [
    f"rtsp://{rtsp_login}@{ip}:554/ch1/1/",
    f"rtsp://{rtsp_login}@{ip}:554/ch2/1/",
    f"rtsp://{rtsp_login}@{ip}:554/ch3/1/",
    f"rtsp://{rtsp_login}@{ip}:554/ch4/1/"
]  # Add more streams as needed

# Tkinter setup
root = Tk()
root.title("RTSP Viewer")
root.configure(bg="black")
root.geometry("800x600")  # Set initial size for the window


ico = Image.open('data/icon.png')
photo = ImageTk.PhotoImage(ico)
root.wm_iconphoto(False, photo)



# Calculate grid dimensions dynamically
num_streams = len(streams)
columns = math.ceil(math.sqrt(num_streams))  # Adjust columns based on the number of streams
rows = math.ceil(num_streams / columns)  # Adjust rows accordingly

# Create canvas for each stream and label
canvas_list = []
labels = []
stream_dimensions = []  # To store the original grid position and size of each stream
for i in range(num_streams):
    canvas = Canvas(root, bg='black')
    canvas.grid(row=i // columns, column=i % columns, padx=5, pady=5, sticky="nsew")  # Arrange in grid
    canvas_list.append(canvas)

    # Add label for stream number
    label = Label(root, text=f"Stream {i+1}", fg="white", bg="black")
    label.grid(row=i // columns, column=i % columns, padx=5, pady=5, sticky="nw")
    labels.append(label)

    # Store original grid dimensions for each stream (row, column, width, height)
    stream_dimensions.append({
        "row": i // columns,
        "col": i % columns,
        "width": canvas.winfo_width(),
        "height": canvas.winfo_height(),
        "hidden": False
    })

# Stream frames storage
frames = [None] * num_streams
fallback_image_path = 'data/cams.webp'  # Path to the fallback image

def is_stream_accessible(stream_url):
    """Check if the RTSP stream is accessible by attempting to connect."""
    try:
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            return False
        cap.release()
        return True
    except cv2.error:
        return False

def update_stream(idx):
    """Capture and update the RTSP stream in the corresponding Tkinter canvas."""
    stream_url = streams[idx]
    
    # Check if the stream is accessible, if not use the fallback image
    if not is_stream_accessible(stream_url):
        display_fallback_image(idx)
    else:
        cap = cv2.VideoCapture(stream_url)
        while True:
            ret, frame = cap.read()
            if ret:
                frames[idx] = frame  # Store the frame
                # Use after() to schedule UI update in the main thread
                root.after(10, update_label, idx)

def display_fallback_image(idx):
    """Display the fallback image if the RTSP stream is not accessible."""
    # Load the fallback image (cams.webp)
    if os.path.exists(fallback_image_path):
        img = Image.open(fallback_image_path)
        img = img.resize((125, 125))  # Resize to 125x125
        img_tk = ImageTk.PhotoImage(img)
        canvas_list[idx].create_image(0, 0, anchor='nw', image=img_tk)
        canvas_list[idx].image = img_tk  # Keep a reference to avoid garbage collection
    else:
        print(f"Fallback image not found at {fallback_image_path}")

def update_label(idx):
    """Update the canvas with the frame for the given stream index."""
    if frames[idx] is not None:
        # Get the canvas size and scale the frame accordingly
        canvas_width = canvas_list[idx].winfo_width()
        canvas_height = canvas_list[idx].winfo_height()

        # Resize the frame to fit the canvas size while maintaining aspect ratio
        frame_resized = resize_frame(frames[idx], canvas_width, canvas_height)

        # Calculate the position to center the image inside the canvas
        x_offset = (canvas_width - frame_resized.shape[1]) // 2
        y_offset = (canvas_height - frame_resized.shape[0]) // 2

        img = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)))
        canvas_list[idx].create_image(x_offset, y_offset, anchor='nw', image=img)
        canvas_list[idx].image = img  # Keep a reference to avoid garbage collection

def resize_frame(frame, width, height):
    """Resize the frame while maintaining its aspect ratio."""
    aspect_ratio = frame.shape[1] / float(frame.shape[0])
    new_width = width
    new_height = int(new_width / aspect_ratio)
    if new_height > height:
        new_height = height
        new_width = int(new_height * aspect_ratio)
    return cv2.resize(frame, (new_width, new_height))

def open_fullscreen_window(idx):
    """Open a new window with the live stream displayed fullscreen."""
    fullscreen_window = Toplevel(root)
    fullscreen_window.title(f"Stream {idx+1} - Fullscreen")
    
    fullscreen_window.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")  # Fullscreen size
    fullscreen_window.configure(bg='black')
    fullscreen_window.attributes("-fullscreen", True)  # Enable fullscreen mode
    
    canvas_fullscreen = Canvas(fullscreen_window, bg='black')
    canvas_fullscreen.pack(fill="both", expand=True)
    
    def update_fullscreen():
        if frames[idx] is not None:
            frame_resized = resize_frame(frames[idx], root.winfo_screenwidth(), root.winfo_screenheight())
            img = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)))
            canvas_fullscreen.create_image(0, 0, anchor='nw', image=img)
            canvas_fullscreen.image = img  # Keep a reference
        fullscreen_window.after(10, update_fullscreen)  # Schedule next frame update
    
    update_fullscreen()
    
    fullscreen_window.bind("<Double-1>", lambda event: fullscreen_window.destroy())  # Close on double-click


def update_fullscreen_stream(idx, canvas_fullscreen):
    """Update the fullscreen window with the stream frame."""
    if frames[idx] is not None:
        # Resize the frame to fit fullscreen size while maintaining aspect ratio
        frame_resized = resize_frame(frames[idx], root.winfo_screenwidth(), root.winfo_screenheight())

        # Calculate the position to center the image inside the canvas
        x_offset = (root.winfo_screenwidth() - frame_resized.shape[1]) // 2
        y_offset = (root.winfo_screenheight() - frame_resized.shape[0]) // 2

        # Create image and place it at the centered position
        img = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)))
        canvas_fullscreen.create_image(x_offset, y_offset, anchor='nw', image=img)
        canvas_fullscreen.image = img  # Keep a reference to avoid garbage collection

def close_fullscreen_and_restore(idx, fullscreen_window):
    """Close the fullscreen window and restore the original window."""
    fullscreen_window.destroy()
    root.deiconify()  # Restore the original window


def close_fullscreen_and_restore(idx, fullscreen_window):
    """Close the fullscreen window and restore the original window."""
    fullscreen_window.destroy()
    root.deiconify()  # Restore the original window

# Start threads for each stream
for i in range(num_streams):
    threading.Thread(target=update_stream, args=(i,), daemon=True).start()

# Double-click event to open fullscreen stream
def on_double_click(event, idx):
    open_fullscreen_window(idx)

# Bind double-click event to each canvas
for i, canvas in enumerate(canvas_list):
    canvas.bind("<Double-1>", lambda event, idx=i: on_double_click(event, idx))

# Make the grid expand with resizing
for i in range(rows):
    root.grid_rowconfigure(i, weight=1)
for i in range(columns):
    root.grid_columnconfigure(i, weight=1)

root.mainloop()
