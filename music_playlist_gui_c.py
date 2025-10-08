"""
music_playlist_gui_c.py
Run in VS Code: Python 3.x
This version uses the C backend compiled as a shared library (DLL / .so).
It does NOT use in-app playback; instead it opens YouTube / Google in the browser.
"""

import os
import ctypes
import json
import hashlib
import webbrowser
import urllib.parse
from tkinter import *
from tkinter import messagebox, simpledialog, filedialog

# ---------- load C library ----------
LIB_WINDOWS = "playlist_backend.dll"
LIB_UNIX = "./libplaylist.so"

if os.name == "nt":
    libpath = os.path.join(os.getcwd(), LIB_UNIX)
else:
    libpath = LIB_UNIX

if not os.path.exists(libpath):
    raise FileNotFoundError(f"C shared library not found at: {libpath}\nCompile playlist_backend.c first.")

lib = ctypes.CDLL(libpath)

# declare arg/return types
lib.initSystem.restype = None
lib.add_song.argtypes = [ctypes.c_char_p]
lib.add_song.restype = None
lib.search_song.argtypes = [ctypes.c_char_p]
lib.search_song.restype = ctypes.c_int
lib.play_song.argtypes = [ctypes.c_char_p]
lib.play_song.restype = None
lib.most_played.restype = ctypes.c_char_p
lib.save_songs.argtypes = [ctypes.c_char_p]
lib.save_songs.restype = None
lib.load_songs.argtypes = [ctypes.c_char_p]
lib.load_songs.restype = None

lib.initSystem()

# ---------- simple user DB ----------
USERS_FILE = "users_db.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

users = load_users()
current_user = None
current_playlist = []  # Python-side playlist (per-user)

# ---------- wrappers to C ----------
def c_add_song(name: str):
    lib.add_song(name.encode("utf-8"))

def c_search_song(name: str) -> bool:
    return lib.search_song(name.encode("utf-8")) == 1

def c_play_song(name: str):
    lib.play_song(name.encode("utf-8"))

def c_most_played() -> str:
    try:
        res = lib.most_played()
        if not res:
            return ""
        return res.decode("utf-8")
    except Exception:
        return ""

def c_save_songs(path: str):
    lib.save_songs(path.encode("utf-8"))

def c_load_songs(path: str):
    lib.load_songs(path.encode("utf-8"))

# ---------- GUI logic ----------
root = Tk()
root.title("Musify Playlist Manager")
root.geometry("640x520")
root.resizable(False, False)

# Top: user label and login/signup
lbl_user = Label(root, text="Not logged in", font=("Arial", 11))
lbl_user.pack(pady=6)

def do_signup():
    global users
    uname = simpledialog.askstring("Sign up", "Username:", parent=root)
    if not uname: return
    pwd = simpledialog.askstring("Sign up", "Password:", show="*", parent=root)
    if not pwd: return
    if uname in users:
        messagebox.showerror("Error", "Username already exists.")
        return
    users[uname] = {"pwd_hash": hash_pass(pwd), "playlist": []}
    save_users(users)
    messagebox.showinfo("Signup", "Signup successful — now login.")

def do_login():
    global current_user, current_playlist, users
    uname = simpledialog.askstring("Login", "Username:", parent=root)
    if not uname: return
    pwd = simpledialog.askstring("Login", "Password:", show="*", parent=root)
    if not pwd: return
    if uname not in users or users[uname]["pwd_hash"] != hash_pass(pwd):
        messagebox.showerror("Error", "Invalid credentials.")
        return
    current_user = uname
    current_playlist = users[uname].get("playlist", [])
    lbl_user.config(text=f"Logged in: {current_user}")
    refresh_playlist()
    messagebox.showinfo("Login", f"Welcome, {current_user}!")

frm_top = Frame(root)
frm_top.pack(pady=6)

btn_login = Button(frm_top, text="Login", width=12, command=do_login)
btn_login.grid(row=0, column=0, padx=6)
btn_signup = Button(frm_top, text="Sign up", width=12, command=do_signup)
btn_signup.grid(row=0, column=1, padx=6)

# Middle: song entry and controls
entry_song = Entry(root, width=60, font=("Arial", 12))
entry_song.pack(pady=10)

frm_controls = Frame(root)
frm_controls.pack(pady=6)

def add_song_ui():
    s = entry_song.get().strip()
    if not s:
        messagebox.showerror("Error", "Enter a song name")
        return
    c_add_song(s)
    if current_user:
        current_playlist.append(s)
        users[current_user]["playlist"] = current_playlist
        save_users(users)
    refresh_playlist()
    messagebox.showinfo("Added", f"Added '{s}' to library.")

def search_song_ui():
    s = entry_song.get().strip()
    if not s:
        messagebox.showerror("Error", "Enter a song name")
        return
    found = c_search_song(s)
    if found:
        messagebox.showinfo("Found", f"'{s}' exists in library.")
    else:
        messagebox.showinfo("Not found", f"'{s}' not found in library.")

def play_song_ui():
    s = entry_song.get().strip()
    if not s:
        messagebox.showerror("Error", "Enter a song name")
        return
    c_play_song(s)             # increments play count in C heap
    lbl_most.config(text=f"Most Played: {c_most_played() or '-'}")
    # open search results on YouTube for playback
    q = urllib.parse.quote(s + " song")
    webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
    messagebox.showinfo("Playing", f"Opened YouTube search for '{s}'.")

def google_search_ui():
    s = entry_song.get().strip()
    if not s:
        messagebox.showerror("Error", "Enter a song name")
        return
    q = urllib.parse.quote(s + " song")
    webbrowser.open(f"https://www.google.com/search?q={q}")

btn_add = Button(frm_controls, text="Add Song", width=12, command=add_song_ui)
btn_add.grid(row=0, column=0, padx=6)
btn_search = Button(frm_controls, text="Search", width=12, command=search_song_ui)
btn_search.grid(row=0, column=1, padx=6)
btn_play = Button(frm_controls, text="Play (YouTube)", width=14, command=play_song_ui)
btn_play.grid(row=0, column=2, padx=6)
btn_google = Button(frm_controls, text="Google", width=12, command=google_search_ui)
btn_google.grid(row=0, column=3, padx=6)

# Bottom: playlist box & controls
lbl_playlist = Label(root, text="Playlist (current user)")
lbl_playlist.pack(pady=6)
listbox = Listbox(root, width=80, height=14)
listbox.pack(pady=6)

def refresh_playlist():
    listbox.delete(0, END)
    for i, s in enumerate(current_playlist):
        listbox.insert(END, f"{i+1}. {s}")

def load_selected_to_entry():
    sel = listbox.curselection()
    if not sel: return
    entry_song.delete(0, END)
    entry_song.insert(0, current_playlist[sel[0]])

def remove_selected():
    global current_playlist, users
    if not current_user:
        messagebox.showerror("Error", "Login first.")
        return
    sel = listbox.curselection()
    if not sel:
        messagebox.showerror("Error", "Select a song to remove.")
        return
    idx = sel[0]
    s = current_playlist.pop(idx)
    users[current_user]["playlist"] = current_playlist
    save_users(users)
    refresh_playlist()
    messagebox.showinfo("Removed", f"Removed '{s}' from playlist.")

def save_library_file():
    path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text","*.txt")])
    if not path: return
    c_save_songs(path)
    messagebox.showinfo("Saved", f"Library saved to {path}")

def load_library_file():
    path = filedialog.askopenfilename(filetypes=[("Text","*.txt")])
    if not path: return
    c_load_songs(path)
    messagebox.showinfo("Loaded", f"Library loaded from {path}")

frm_playlist_controls = Frame(root)
frm_playlist_controls.pack(pady=6)
btn_load_entry = Button(frm_playlist_controls, text="Load to Entry", command=load_selected_to_entry)
btn_load_entry.grid(row=0, column=0, padx=6)
btn_remove = Button(frm_playlist_controls, text="Remove", command=remove_selected)
btn_remove.grid(row=0, column=1, padx=6)
btn_save_lib = Button(frm_playlist_controls, text="Save Library", command=save_library_file)
btn_save_lib.grid(row=0, column=2, padx=6)
btn_load_lib = Button(frm_playlist_controls, text="Load Library", command=load_library_file)
btn_load_lib.grid(row=0, column=3, padx=6)

lbl_most = Label(root, text=f"Most Played: {c_most_played() or '-'}", font=("Arial", 11, "bold"))
lbl_most.pack(pady=6)

# If there is an 'initial_songs.txt' file, load it into C backend
if os.path.exists("initial_songs.txt"):
    try:
        c_load_songs("initial_songs.txt")
    except Exception:
        pass

root.mainloop()
