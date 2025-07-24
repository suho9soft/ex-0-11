import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import threading
import requests
from PIL import Image, ImageTk
from io import BytesIO
import time

# 상태 변수
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
        print("✅ MQTT 연결됨")
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
            relay_state = data.get("relay", False)
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
    temp_label.config(text=f"🌡 온도: {current_values['temp']:.1f} °C")
    humi_label.config(text=f"💧 습도: {current_values['humi']:.1f} %")
    pot_label.config(text=f"🎛 가변저항: {current_values['pot']}")
    relay_label.config(
        text=f"⚡ 릴레이 상태: {'ON' if relay_state else 'OFF'}",
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


# MJPEG 스트리밍
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
                    img = img.resize((360, int(360 * img.height / img.width)))
                    imgtk = ImageTk.PhotoImage(img)
                    window.after(0, lambda img=imgtk: camera_label.config(image=img) or setattr(camera_label, 'imgtk', img))
                    time.sleep(0.04)
        except Exception as e:
            print("📷 카메라 에러:", e)
            time.sleep(1)


# GUI 구성
window = tk.Tk()
window.title("ESP32 센서 + 카메라 모니터")
window.geometry("420x850")
window.configure(bg="white")

top_frame = tk.Frame(window, bg="white")
top_frame.pack(pady=10)

# 날짜 / 시간
date_label = tk.Label(top_frame, text="", font=("맑은 고딕", 12), bg="white")
date_label.pack()
time_label = tk.Label(top_frame, text="", font=("맑은 고딕", 12), bg="white")
time_label.pack()

# 센서 값
sensor_frame = tk.LabelFrame(top_frame, text="센서 데이터", font=("맑은 고딕", 11), bg="white")
sensor_frame.pack(pady=5)
temp_label = tk.Label(sensor_frame, text="🌡 온도: --", font=("맑은 고딕", 13), bg="white")
humi_label = tk.Label(sensor_frame, text="💧 습도: --", font=("맑은 고딕", 13), bg="white")
pot_label = tk.Label(sensor_frame, text="🎛 가변저항: --", font=("맑은 고딕", 13), bg="white")
temp_label.pack(pady=2)
humi_label.pack(pady=2)
pot_label.pack(pady=2)

# 릴레이 상태
relay_label = tk.Label(top_frame, text="⚡ 릴레이 상태: --", font=("맑은 고딕", 13), fg="red", bg="white")
relay_label.pack(pady=10)

# LED 버튼
led_frame = tk.LabelFrame(top_frame, text="LED 제어", font=("맑은 고딕", 11), bg="white", padx=10, pady=10)
led_frame.pack(pady=5)

led_buttons = []
for i in range(8):
    btn = tk.Button(led_frame, text=f"LED {i + 1}", width=8, height=2,
                    bg="light gray", command=lambda i=i: toggle_led(i))
    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
    led_buttons.append(btn)

# 카메라 화면
camera_title = tk.Label(window, text="📷 ESP32 카메라", font=("맑은 고딕", 13, "bold"), bg="white")
camera_title.pack(pady=8)
camera_label = tk.Label(window, bg="black", width=360, height=240)
camera_label.pack(pady=6)

# 실행
connect_mqtt()
update_datetime()
threading.Thread(target=mjpeg_stream, daemon=True).start()

window.mainloop()
stop_camera = True
