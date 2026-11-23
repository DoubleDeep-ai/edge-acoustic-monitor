"""Thread-safe Tkinter dashboard for edge monitoring nodes."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime
from io import BytesIO
import queue
import socket
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

from common.protocol import ConnectionClosed, receive_packet


class MonitoringDashboard:
    def __init__(self, root: tk.Tk, host: str, port: int):
        self.root = root
        self.host = host
        self.port = port
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.stop_event = threading.Event()
        self.server_socket: Optional[socket.socket] = None
        self.frame_labels: dict[str, tk.Label] = {}
        self.frame_images: dict[str, ImageTk.PhotoImage] = {}
        self.temperature_history: defaultdict[str, deque[float]] = defaultdict(lambda: deque(maxlen=100))
        self.alert_state: defaultdict[str, bool] = defaultdict(bool)

        self.root.title("Edge Acoustic Monitor")
        self.root.geometry("1180x820")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        header = ttk.Frame(root, padding=12)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Edge Acoustic Monitor", font=("Helvetica", 18, "bold")).pack(side=tk.LEFT)
        self.status = ttk.Label(header, text="Server stopped")
        self.status.pack(side=tk.LEFT, padx=20)
        self.start_button = ttk.Button(header, text="Start server", command=self.start)
        self.start_button.pack(side=tk.RIGHT)

        self.video_area = ttk.LabelFrame(root, text="Live devices", padding=10)
        self.video_area.pack(fill=tk.X, padx=12, pady=6)

        self.figure, self.axis = plt.subplots(figsize=(8, 2.2))
        self.axis.set_title("Temperature history")
        self.axis.set_ylabel("°C")
        self.axis.set_ylim(15, 35)
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        event_frame = ttk.LabelFrame(root, text="Anomaly events", padding=8)
        event_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        self.event_table = ttk.Treeview(event_frame, columns=("device", "message", "time"), show="headings", height=7)
        self.event_table.heading("device", text="Device")
        self.event_table.heading("message", text="Message")
        self.event_table.heading("time", text="Received at")
        self.event_table.column("device", width=180)
        self.event_table.column("message", width=600)
        self.event_table.column("time", width=200)
        scrollbar = ttk.Scrollbar(event_frame, orient=tk.VERTICAL, command=self.event_table.yview)
        self.event_table.configure(yscrollcommand=scrollbar.set)
        self.event_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.root.after(50, self.process_events)

    def start(self) -> None:
        self.start_button.configure(state=tk.DISABLED)
        threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self) -> None:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(10)
            server.settimeout(0.5)
            self.server_socket = server
            self.events.put(("status", f"Listening on {self.host}:{self.port}"))

            while not self.stop_event.is_set():
                try:
                    connection, address = server.accept()
                except socket.timeout:
                    continue
                connection.settimeout(10)
                threading.Thread(target=self.receive_client, args=(connection, address), daemon=True).start()
        except OSError as error:
            self.events.put(("error", f"Server error: {error}"))

    def receive_client(self, connection: socket.socket, address: tuple[str, int]) -> None:
        peer = f"{address[0]}:{address[1]}"
        self.events.put(("status", f"Connected: {peer}"))
        try:
            with connection:
                while not self.stop_event.is_set():
                    packet = receive_packet(connection)
                    if packet is None:
                        break
                    metadata, image = packet
                    self.events.put(("packet", (metadata, image)))
        except (ConnectionClosed, OSError, ValueError) as error:
            self.events.put(("status", f"Disconnected: {peer} ({error})"))
        else:
            self.events.put(("status", f"Disconnected: {peer}"))

    def process_events(self) -> None:
        while True:
            try:
                event_type, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event_type == "packet":
                self.update_packet(*payload)
            elif event_type == "error":
                self.status.configure(text=payload, foreground="#b3261e")
                self.start_button.configure(state=tk.NORMAL)
            else:
                self.status.configure(text=payload)

        self.root.after(50, self.process_events)

    def update_packet(self, metadata: dict[str, Any], image_bytes: bytes) -> None:
        device_id = str(metadata.get("device_id", "unknown-device"))
        anomaly = bool(metadata.get("anomaly", False))
        temperature = float(metadata.get("temperature", 0.0))
        exceedances = int(metadata.get("exceedances", 0))

        if image_bytes:
            try:
                with Image.open(BytesIO(image_bytes)) as frame:
                    display = frame.convert("RGB").resize((360, 203), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(display)
                label = self.frame_labels.get(device_id)
                if label is None:
                    panel = ttk.Frame(self.video_area)
                    panel.pack(side=tk.LEFT, padx=8)
                    ttk.Label(panel, text=device_id, font=("Helvetica", 11, "bold")).pack()
                    label = ttk.Label(panel)
                    label.pack()
                    self.frame_labels[device_id] = label
                label.configure(image=photo)
                self.frame_images[device_id] = photo
            except OSError:
                self.status.configure(text=f"Invalid image from {device_id}", foreground="#b3261e")

        self.temperature_history[device_id].append(temperature)
        self.update_temperature_plot()

        if anomaly and not self.alert_state[device_id]:
            message = f"Large-amplitude audio detected ({exceedances:,} samples over threshold)"
            self.event_table.insert("", 0, values=(device_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.alert_state[device_id] = anomaly

    def update_temperature_plot(self) -> None:
        self.axis.clear()
        self.axis.set_title("Temperature history")
        self.axis.set_ylabel("°C")
        self.axis.set_ylim(15, 35)
        for device_id, values in self.temperature_history.items():
            self.axis.plot(list(values), label=device_id)
        if self.temperature_history:
            self.axis.legend(loc="upper right")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def close(self) -> None:
        self.stop_event.set()
        if self.server_socket is not None:
            self.server_socket.close()
        plt.close(self.figure)
        self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jetson Nano monitoring dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="address to bind")
    parser.add_argument("--port", type=int, default=8089, help="TCP port")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    window = tk.Tk()
    MonitoringDashboard(window, arguments.host, arguments.port)
    window.mainloop()
