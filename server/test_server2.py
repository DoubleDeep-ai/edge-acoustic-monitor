import tkinter as tk
import threading
import pandas as pd
import cv2
import socket
import struct
from PIL import Image, ImageTk
import pickle
from tkinter import ttk
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import ImageDraw, ImageFont

HOST = 'localhost'
PORT = 8089

DATA_HOST = 'localhost'
DATA_PORT = 8090

class VideoServer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video Server")
        self.status_label = tk.Label(self.root, text="Server not connected", font=("Helvetica", 14))
        self.status_label.pack(pady=10)
        self.root.geometry("1200x800+200+200")
        
        self.start_button = tk.Button(self.root, text="Start Server", command=self.start_server)
        self.start_button.pack(pady=10)

        # 프레임을 저장하는 리스트
        self.frames = []
        # 그래프 출력
        plt.rcParams.update({'font.size': 4})
        self.fig, self.ax = plt.subplots(figsize=(6, 1.2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas_widget = self.canvas.get_tk_widget()

        self.x_data = np.arange(0, 10, 0.1)
        self.y_data = np.zeros_like(self.x_data)

        # 일정 간격으로 그래프 업데이트 호출
        #self.root.after(100, self.update_plot)

        # Treeview로 테이블 생성
        self.table = tk.Frame(self.root)
        self.tree = ttk.Treeview(self.table)
        self.tree["columns"] = ("Client ID", "Additional Data","Time")
        self.tree.column("#0", width=0, stretch=tk.NO)  # 숨김 열
        self.tree.column("Client ID", anchor=tk.CENTER, width=300)
        self.tree.column("Additional Data", anchor=tk.W, width=400)
        self.tree.column("Time", anchor=tk.CENTER, width=300)

        self.tree.heading("#0", text="", anchor=tk.W)
        self.tree.heading("Client ID", text="Client ID", anchor=tk.CENTER)
        self.tree.heading("Additional Data", text="Additional Data", anchor=tk.W)
        
        self.tree.heading("Time", text="Time", anchor=tk.CENTER)
        self.scrollbar = ttk.Scrollbar(self.table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        # 트리뷰와 스크롤바 배치
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH,padx=100)
        self.scrollbar.pack(side='right', fill='y')
        # 윈도우 크기 조정에 따라 테이블 크기 변경
        self.table.pack(side=tk.BOTTOM,fill=tk.BOTH,pady=10)
        self.canvas_widget.pack(side=tk.BOTTOM,padx=100,pady=20)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        # 배경 색을 변경할 태그 생성
        self.tree.tag_configure("green_row", background="#FF0000")  # 예시 색상 (연두색)
        self.tree.tag_configure("yellow_row", background="#0000FF")  # 예시 색상 (노란색)
        
        
    def update_plot(self):
        # 여기에서 실제로 그래프를 업데이트하는 로직을 추가
        self.ax.clear()
        self.x_data += 0.1
        self.line, = self.ax.plot(self.x_data, self.y_data)

        # 그래프 범위 설정
        self.ax.set_ylim([18, 30])
        
        # 다음 업데이트를 예약
        self.canvas.draw()
        #self.root.after(2000, self.update_plot)
        self.ax.clear()
        

        
        
    def start_server(self):
        self.start_button.config(state="disabled")
        self.status_label.config(text="Waiting for connection...")
        server_thread = threading.Thread(target=self.receive_video, daemon=True)
        server_thread.start()
        server_data_thread = threading.Thread(target=self.receive_temper, daemon=True)
        server_data_thread.start()
            
    def receive_video(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen(10)
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            print(f"Connection from {addr}")

            # 클라이언트 식별에 IP 주소와 포트 번호 모두 사용
            client_id = f"{addr[0]}:{addr[1]}"

            # 클라이언트에 대한 레이블 생성
            client_label = tk.Label(self.root)
            client_label.pack(side="left", padx=10)
            
            # 새로운 클라이언트에 대한 레이블을 리스트에 추가
            self.frames.append({
                'client_id': client_id,
                'label': client_label
            })

            # 새로운 클라이언트에 대해 스레드를 생성하여 영상 수신 및 표시
            client_thread = threading.Thread(target=self.receive_and_display, args=(conn, client_id), daemon=True)
            client_thread.start()
            
    def receive_temper(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((DATA_HOST, DATA_PORT))
        print(f"Server listening on data -> {DATA_HOST}:{DATA_PORT}")
        s.listen(10)
        while True:
            conn, addr = s.accept()
            print(f"Connection from {addr}")

            # 클라이언트 식별에 IP 주소와 포트 번호 모두 사용
            client_id = f"{addr[0]}:{addr[1]}"
            # 새로운 클라이언트에 대해 스레드를 생성하여 영상 수신 및 표시
            client_thread = threading.Thread(target=self.receive_data, args=(conn, client_id), daemon=True)
            client_thread.start()

    def receive_data(self, conn, client_id):
        try:
            while True:
                # 클라이언트로부터 데이터를 받음
                data = conn.recv(1024)
                data = data.decode()
                if not data:
                    break  # 클라이언트가 연결을 종료하면 루프를 종료
                # 받은 데이터를 처리 (여기에서는 간단하게 출력)
                print(f"Received data from client: {data}")
                temperature_str = data.split("Temperature:")[1].strip()
                temperature = float(temperature_str)
                self.y_data = np.append(self.y_data[1:],temperature)
                self.update_plot()
        except Exception as e:
            print(f"Error in server: {e}")
        finally:
            # 클라이언트 소켓 종료
            conn.close()
            
        
    def receive_and_display(self, conn, client_id):
        payload_size = struct.calcsize("L")
        data = b''

        while True:
            while len(data) < payload_size:
                data += conn.recv(4096)
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("L", packed_msg_size)[0]
            while len(data) < msg_size:
                data += conn.recv(4096)
            frame_data = data[:msg_size]
            data = data[msg_size:]
            #frame = pickle.loads(frame_data)
            frame, additional_data = pickle.loads(frame_data)
            # 추가 데이터가 있는 경우에만 테이블에 행 추가
            if additional_data:
                self.add_row_to_table(client_id, additional_data)

            # 이미지를 PhotoImage로 변환
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            text_to_add = f"Client: {client_id}"  # 변경 가능
            resized_img = self.resize_image(img, 300, 200)
            self.add_text_to_image(resized_img, text_to_add)
            img_tk = ImageTk.PhotoImage(resized_img)
            # 텍스트를 이미지에 추가
            
            

            # 클라이언트에 해당하는 레이블을 찾아 업데이트
            for frame_info in self.frames:
                if frame_info['client_id'] == client_id:
                    frame_info['label'].configure(image=img_tk,width=300, height=200)
                    frame_info['label'].image = img_tk
                    self.root.update_idletasks()
                    break
                
    def add_text_to_image(self, image, text, position=(10, 10), font_size=20, font_color=(255, 255, 255)):
        # 이미지에 텍스트 추가
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()  # 기본 폰트 사용 (원하는 폰트로 변경 가능)
        draw.text(position, text, font=font, fill=font_color)
        
    
    def add_row_to_table(self, client_id, additional_data):
        now = time
        tag = "green_row" if additional_data == "1번기계에서 이상값이 발견되었습니다" else "yellow_row"
        # 테이블에 새로운 행 추가
        self.tree.insert("", "end", values=(client_id, additional_data,now.strftime('%Y-%m-%d %H:%M:%S')),tags=tag)
        
        
    def run(self):
        self.root.mainloop()
    
    # 이미지 크기 조절 함수
    def resize_image(self, image, new_width, new_height):
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

if __name__ == '__main__':
    video_server = VideoServer()
    video_server.run()
