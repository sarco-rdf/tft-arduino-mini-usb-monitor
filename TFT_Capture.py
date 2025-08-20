import serial
from PIL import ImageGrab, Image
import time
import tkinter as tk
from tkinter import messagebox
import threading
import subprocess
import sys
import pkg_resources
import os

def check_and_install_requirements():
    req_file = "requirements.txt"

    if not os.path.exists(req_file):
        print(f"❌ Archivo {req_file} no encontrado. Continuando sin instalar dependencias...")
        return

    with open(req_file, 'r') as f:
        required = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = [pkg for pkg in required if pkg.lower() not in installed]

    if missing:
        print(f"📦 Instalando dependencias faltantes: {missing}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
    else:
        print("✅ Todas las dependencias ya están instaladas.")

check_and_install_requirements()

# =================== CONFIGURACIÓN INICIAL ===================

TFT_WIDTH = 128
TFT_HEIGHT = 160

# Cambia este puerto si es necesario
SERIAL_PORT = "COM3"
BAUD_RATE = 250000

# =================== VARIABLES DE CONTROL ===================

capture_region = [0, 0, 800, 600]  # Por defecto
transmitting = False
mode = None  # 'area' o 'full'
ser = None

lock = threading.Lock()

# =================== FUNCIONES PRINCIPALES ===================

def rgb888_to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def seleccionar_region_visual():
    def on_mouse_down(event):
        nonlocal start_x, start_y
        start_x = root.winfo_pointerx()
        start_y = root.winfo_pointery()
        canvas.delete("rect")

    def on_mouse_drag(event):
        cur_x = root.winfo_pointerx()
        cur_y = root.winfo_pointery()
        canvas.delete("rect")
        canvas.create_rectangle(start_x, start_y, cur_x, cur_y, outline='red', width=2, tag="rect")

    def on_mouse_up(event):
        end_x = root.winfo_pointerx()
        end_y = root.winfo_pointery()

        with lock:
            capture_region[0] = min(start_x, end_x)
            capture_region[1] = min(start_y, end_y)
            capture_region[2] = max(start_x, end_x)
            capture_region[3] = max(start_y, end_y)

        root.destroy()

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)
    root.configure(background='black')
    root.title("Selecciona el área de captura")

    canvas = tk.Canvas(root, cursor="cross", bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    start_x = start_y = 0

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)

    root.mainloop()

def transmitir():
    global transmitting, ser, mode

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
        time.sleep(2)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir el puerto serial: {e}")
        return

    while transmitting:
        with lock:
            if mode == "area":
                region = tuple(capture_region)
                screen = ImageGrab.grab(bbox=region)
            elif mode == "full":
                screen = ImageGrab.grab()
            else:
                break

        img = screen.rotate(90, expand=True).resize((TFT_WIDTH, TFT_HEIGHT), Image.LANCZOS).convert("RGB")

        buf_list = []
        for y in range(TFT_HEIGHT):
            for x in range(TFT_WIDTH):
                r, g, b = img.getpixel((x, y))
                color = rgb888_to_rgb565(r, g, b)
                buf_list.append(color >> 8)
                buf_list.append(color & 0xFF)
        buf = bytearray(buf_list)

        try:
            ser.write(b'START\n')
            ser.write(buf)
            ser.write(b'END\n')
        except Exception as e:
            print(f"Error en envío serial: {e}")
            break

        time.sleep(0.03)  # Aproximadamente 30 FPS

    if ser:
        ser.close()
        ser = None

def iniciar_transmision(tipo):
    global transmitting, mode

    if transmitting:
        messagebox.showwarning("Advertencia", "Ya hay una transmisión en curso.")
        return

    if tipo not in ("area", "full"):
        return

    mode = tipo
    transmitting = True
    thread = threading.Thread(target=transmitir, daemon=True)
    thread.start()

def detener_transmision():
    global transmitting, mode
    transmitting = False
    mode = None

# =================== INTERFAZ GRÁFICA ===================

def build_gui():
    root = tk.Tk()
    root.title("Control de Transmisión TFT")
    root.configure(bg="#1e1e1e")
    root.geometry("450x260")

    # Estilo general
    label_font = ("Segoe UI", 14, "bold")
    button_font = ("Segoe UI", 10, "bold")
    fg_color = "#ffffff"
    bg_color = "#1e1e1e"
    button_bg = "#3a3a3a"
    button_fg = "#ffffff"
    highlight_color = "#007acc"  # Azul tipo VSCode

    # Título
    title = tk.Label(root, text="🎮 Control de Transmisión TFT", font=label_font, fg=fg_color, bg=bg_color)
    title.pack(pady=10)

    # Contenedor de botones
    frame = tk.Frame(root, bg=bg_color)
    frame.pack(pady=10)

    style = dict(
        width=22,
        height=2,
        font=button_font,
        bg=button_bg,
        fg=button_fg,
        activebackground=highlight_color,
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2"
    )

    # Botones de control
    btn_set_area = tk.Button(frame, text="🖱️ Set Area", command=seleccionar_region_visual, **style)
    btn_set_area.grid(row=0, column=0, padx=5, pady=5)

    btn_start_area = tk.Button(frame, text="▶️ Start Transmision", command=lambda: iniciar_transmision("area"), **style)
    btn_start_area.grid(row=0, column=1, padx=5, pady=5)

    btn_start_full = tk.Button(frame, text="🖥️ Start Full Monitor", command=lambda: iniciar_transmision("full"), **style)
    btn_start_full.grid(row=1, column=0, padx=5, pady=5)

    # Corregido para evitar argumento duplicado 'bg'
    btn_stop_style = style.copy()
    btn_stop_style.update({
        "bg": "#aa2e2e",
        "activebackground": "#d64848"
    })
    btn_stop = tk.Button(frame, text="🛑 Stop Transmisión", command=detener_transmision, **btn_stop_style)
    btn_stop.grid(row=1, column=1, padx=5, pady=5)

    # Botón de salir
    btn_salir = tk.Button(root, text="❌ Salir", command=root.destroy, **style)
    btn_salir.pack(pady=10)

    root.mainloop()

# =================== EJECUCIÓN ===================

if __name__ == "__main__":
    build_gui()
