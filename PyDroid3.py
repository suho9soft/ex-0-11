import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import threading
import requests
from PIL import Image, ImageTk
from io import BytesIO
import time

# 전역 상태 변수
relay_state = False
led_states = [False] * 8
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}
mqtt_connected = False
stop_camera = False

# MQTT 설정
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        client.subscribe("arduino/input")
        client.subscribe("arduino/output")
        for i in range(1, 9):
            client.subscribe(f"arduino/led{i}")
    else:
        print("❌ MQTT 연결 실패:", rc)

def on_message(client, userdata, msg):
    global relay_state
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        if topic == "arduino/input":
            data = json.loads(payload)
            current_values["temp"] = float(data.get("temp", 0.0))
            current_values["humi"] = float(data.get("humi", 0.0))
            current_values["pot"] = int(data.get("pot", 0))
            relay_state = bool(data.get("relay", False))
        elif topic == "arduino/output":
            relay_state = ("on" in payload.lower())
        elif topic.startswith("arduino/led"):
            idx = int(topic[-1]) - 1
            led_states[idx] = (payload == "1")
        update_ui()
    except Exception as e:
        print("❗ 메시지 오류:", e)

def connect_mqtt():
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

def update_ui():
    temp_label.config(text=f"🌡 온도\n{current_values['temp']:.1f} °C")
    humi_label.config(text=f"💧 습도\n{current_values['humi']:.1f} %")
    pot_label.config(text=f"🎛 가변저항\n{current_values['pot']}")
    relay_label.config(
        text=f"⚡ 릴레이\n{'ON' if relay_state else 'OFF'}",
        fg="green" if relay_state else "red"
    )
    for i in range(8):
        led_buttons[i].config(bg="green" if led_states[i] else "light gray")

def update_datetime():
    now = datetime.now()
    weekday = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    date_label.config(text=now.strftime(f"%Y-%m-%d ({weekday})"))
    time_label.config(text=now.strftime("%H:%M:%S"))
    window.after(1000, update_datetime)

def toggle_led(index):
    led_states[index] = not led_states[index]
    client.publish(f"arduino/led{index+1}", "1" if led_states[index] else "0")
    update_ui()

CAMERA_URL = "http://172.30.1.60:81/stream"

def mjpeg_stream():
    global stop_camera
    while not stop_camera:
        try:
            response = requests.get(CAMERA_URL, stream=True, timeout=5)
            byte_data = b''
            for chunk in response.iter_content(chunk_size=1024):
                if stop_camera:
                    break
                byte_data += chunk
                a = byte_data.find(b'\xff\xd8')
                b = byte_data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = byte_data[a:b + 2]
                    byte_data = byte_data[b + 2:]
                    img = Image.open(BytesIO(jpg)).convert('RGB')
                    img = img.resize((360, int(360 * img.height / img.width)))  # 크기 조절
                    imgtk = ImageTk.PhotoImage(img)
                    def update_img():
                        camera_label.config(image=imgtk)
                        camera_label.image = imgtk
                    window.after(0, update_img)
                    time.sleep(0.03)
        except Exception as e:
            print("📷 카메라 에러:", e)
            time.sleep(1)

# GUI 구성
window = tk.Tk()
window.title("ESP32 센서 및 카메라 모니터")
window.geometry("800x520")
window.configure(bg="white")

sidebar = tk.Frame(window, width=200, bg="white")
sidebar.pack(side="left", fill="y", padx=5, pady=5)

date_label = tk.Label(sidebar, text="", font=("맑은 고딕", 11), bg="white")
date_label.pack(pady=(10, 2))
time_label = tk.Label(sidebar, text="", font=("맑은 고딕", 11), bg="white")
time_label.pack(pady=(0, 10))

sensor_frame = tk.Frame(sidebar, bg="white")
sensor_frame.pack(pady=5)

temp_label = tk.Label(sensor_frame, text="🌡 온도", font=("맑은 고딕", 11), bg="white")
humi_label = tk.Label(sensor_frame, text="💧 습도", font=("맑은 고딕", 11), bg="white")
pot_label = tk.Label(sensor_frame, text="🎛 가변저항", font=("맑은 고딕", 11), bg="white")
relay_label = tk.Label(sensor_frame, text="⚡ 릴레이", font=("맑은 고딕", 11), bg="white", fg="red")

temp_label.pack(pady=3)
humi_label.pack(pady=3)
pot_label.pack(pady=3)
relay_label.pack(pady=8)

led_frame = tk.LabelFrame(sidebar, text="LED 제어", font=("맑은 고딕", 10), bg="white")
led_frame.pack(pady=10)

led_buttons = []
for i in range(8):
    btn = tk.Button(led_frame, text=f"{i + 1}", width=3, height=1,
                    bg="light gray", command=lambda i=i: toggle_led(i))
    btn.grid(row=i // 2, column=i % 2, padx=3, pady=3)
    led_buttons.append(btn)

camera_area = tk.Frame(window, bg="white")
camera_area.pack(side="left", fill="both", expand=True)

camera_title = tk.Label(camera_area, text="📷 ESP32 카메라 영상", font=("맑은 고딕", 13, "bold"), bg="white")
camera_title.pack(pady=6)

camera_label = tk.Label(camera_area, bg="black", width=360, height=270)
camera_label.pack(pady=8)

connect_mqtt()
update_datetime()
threading.Thread(target=mjpeg_stream, daemon=True).start()

window.mainloop()
stop_camera = True
