import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk
import threading
import os
import socket
from queue import Queue

# ---------- Настройки ----------
PIC_FOLDER = "IMG"
HOST = "0.0.0.0"
PORT = 12345
ICON_FILE = "icon.ico"

# ---------- Палитра ----------
BG_TOP = "#ffe4ec"
BG_BOTTOM = "#f8d7e3"
CARD_BG = "#fffafc"
CARD_BORDER = "#f3c1d1"
TEXT_MAIN = "#6b3a4b"
TEXT_MUTED = "#b07a8d"
ACCENT_OK = "#7bcfa3"
ACCENT_WAIT = "#f7a8c0"
SHADOW = "#f0c9d6"


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


LOCAL_IP = get_local_ip()

# ---------- Окно ----------
root = tk.Tk()
root.title("Приёмник изображений")
root.geometry("960x700")
root.minsize(720, 540)
root.configure(bg=BG_TOP)

if os.path.exists(ICON_FILE):
    try:
        root.iconbitmap(ICON_FILE)
    except Exception as e:
        print(f"Иконка не установлена: {e}")

# ---------- Градиент ----------
bg_canvas = tk.Canvas(root, highlightthickness=0, bd=0, bg=BG_TOP)
bg_canvas.pack(fill="both", expand=True)


def draw_gradient(canvas, top_color, bottom_color):
    canvas.delete("grad")
    w = canvas.winfo_width() or 960
    h = canvas.winfo_height() or 700
    steps = h
    r1, g1, b1 = root.winfo_rgb(top_color)
    r2, g2, b2 = root.winfo_rgb(bottom_color)
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = int(r1 + (r2 - r1) * t) // 256
        g = int(g1 + (g2 - g1) * t) // 256
        b = int(b1 + (b2 - b1) * t) // 256
        color = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(0, i, w, i, fill=color, tags="grad")
    canvas.tag_lower("grad")


bg_canvas.bind("<Configure>", lambda e: draw_gradient(bg_canvas, BG_TOP, BG_BOTTOM))

# ---------- Карточка ----------
card_shadow = tk.Frame(root, bg=SHADOW, bd=0)
card_shadow.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.875, relheight=0.845)

card_border = tk.Frame(root, bg=CARD_BORDER, bd=0)
card_border.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.86, relheight=0.83)

card = tk.Frame(card_border, bg=CARD_BG, bd=0)
card.pack(fill="both", expand=True, padx=2, pady=2)

# ---------- Верхняя панель ----------
top_bar = tk.Frame(card, bg=CARD_BG)
top_bar.pack(fill="x", padx=24, pady=(18, 6))

status_dot = tk.Canvas(top_bar, width=16, height=16, bg=CARD_BG, highlightthickness=0, bd=0)
status_dot.pack(side="left", padx=(0, 10))
dot_id = status_dot.create_oval(3, 3, 13, 13, fill=ACCENT_WAIT, outline="")


def pick_font(candidates, size, weight="normal"):
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return (name, size, weight)
    return ("TkDefaultFont", size, weight)


soft_font = pick_font(["Segoe UI Variable", "Segoe UI", "Verdana", "Helvetica", "Arial"], 11, "bold")

status_text = tk.Label(top_bar, text="Ожидание отправителя…", font=soft_font, bg=CARD_BG, fg=TEXT_MUTED)
status_text.pack(side="left")

# ---------- Плашка IP ----------
info_frame = tk.Frame(card, bg=CARD_BG)
info_frame.pack(pady=(0, 8))  # Изначально видима

info_label = tk.Label(info_frame, text=f"{LOCAL_IP}  :  {PORT}", font=("Consolas", 22, "bold"), bg=CARD_BG,
                      fg=TEXT_MAIN)
info_label.pack()

hint_label = tk.Label(info_frame, text="Введите этот адрес в отправителе",
                      font=pick_font(["Segoe UI", "Verdana"], 10, "italic"), bg=CARD_BG, fg=TEXT_MUTED)
hint_label.pack(pady=(2, 0))

# ---------- Область картинки ----------
image_holder = tk.Frame(card, bg=CARD_BG)
image_holder.pack(fill="both", expand=True, padx=24, pady=(4, 22))

label = tk.Label(image_holder, bg=CARD_BG)
label.pack(fill="both", expand=True)

placeholder = tk.Label(image_holder, text="🌸\nздесь появится изображение", font=pick_font(["Segoe UI", "Verdana"], 13),
                       bg=CARD_BG, fg=TEXT_MUTED, justify="center")
placeholder.place(relx=0.5, rely=0.5, anchor="center")

current_photo = None

# ---------- Пульсация ----------
pulse_state = {"phase": 0, "running": True, "color": ACCENT_WAIT}


def pulse_dot():
    if not pulse_state["running"]: return
    phase = pulse_state["phase"]
    size = 8 + int(2 * abs((phase % 20) - 10) / 10 * 2)
    status_dot.coords(dot_id, 8 - size / 2, 8 - size / 2, 8 + size / 2, 8 + size / 2)
    status_dot.itemconfig(dot_id, fill=pulse_state["color"])
    pulse_state["phase"] += 1
    root.after(90, pulse_dot)


def set_status(state, text):
    pulse_state["color"] = ACCENT_OK if state == "ok" else ACCENT_WAIT
    status_text.config(text=text, fg=ACCENT_OK if state == "ok" else TEXT_MUTED)


# ---------- Появление интерфейса ----------
def show_info():
    if not info_frame.winfo_ismapped():
        info_frame.pack(pady=(0, 8), before=image_holder)
    set_status("wait", "Ожидание отправителя…")
    print("Статус: Ожидание")


def hide_info(sender_ip=None):
    # Скрываем плашку
    info_frame.pack_forget()
    if sender_ip:
        set_status("ok", f"Подключено: {sender_ip} ♡")
    else:
        set_status("ok", "Подключено ♡")
    print(f"Статус: Подключено {sender_ip}")


# ---------- Загрузка картинок ----------
def load_image(name, width, height):
    if not name.lower().endswith(".png"): name = name + ".png"
    path = os.path.join(PIC_FOLDER, name)
    if not os.path.exists(path):
        print(f"Картинки нет: {path}")
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((width, height), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Не загрузилось: {e}")
        return None


def update_image_safe(img_name):
    placeholder.place_forget()
    w = label.winfo_width()
    h = label.winfo_height()
    if w < 10: w = 700
    if h < 10: h = 450
    photo = load_image(img_name, w, h)
    global current_photo
    if photo:
        current_photo = photo
        label.config(image=current_photo)
        print(f"сейчас: {img_name} ({w}x{h})")
    else:
        label.config(image="")
        placeholder.place(relx=0.5, rely=0.5, anchor="center")


# ---------- Очередь ----------
gui_queue = Queue()

def process_gui_queue():
    while not gui_queue.empty():
        func = gui_queue.get()
        try:
            func()
        except Exception as e:
            print(f"ошибка в очереди: {e}")
    root.after(80, process_gui_queue)

# ---------- Сеть ----------
def handle_client(conn, addr):
    sender_ip = addr[0]
    print(f"подключился: {addr}")

    # Статус "Подключено"
    gui_queue.put(lambda ip=sender_ip: hide_info(ip))

    buffer = b""
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = line.decode("utf-8", errors="ignore").strip()
                if msg:
                    print(f"получено: {msg}")
                    gui_queue.put(lambda name=msg: update_image_safe(name))

        remainder = buffer.decode("utf-8", errors="ignore").strip()
        if remainder:
            print(f"получено (без \\n): {remainder}")
            gui_queue.put(lambda name=remainder: update_image_safe(remainder))
    except Exception as e:
        print(f"ошибка обработки клиента: {e}")
    finally:
        conn.close()
        print(f"отключился: {addr}")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
        server.listen(1)
        print(f"Сервер запущен на {LOCAL_IP}:{PORT}")
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА СЕРВЕРА: {e}")


# ---------- Запуск ----------
threading.Thread(target=start_server, daemon=True).start()
root.after(80, process_gui_queue)
pulse_dot()
root.mainloop()
