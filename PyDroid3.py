import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import cv2
from PIL import Image, ImageTk
import threading

# ==== 상태 변수 ====
relay_state = False
led_states = [False] * 8
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}
mqtt_connected = False

# ==== MQTT 설정 ====
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
client = mqtt.Client()

# ==== MQTT 콜백 ====
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("✅ MQTT에 성공적으로 연결되었습니다.")
        client.subscribe("arduino/input")
        client.subscribe("arduino/output")
        for i in range(1, 9):
            client.subscribe(f"arduino/led{i}")
    else:
        print(f"❌ MQTT 연결 실패 - 반환 코드: {rc}")

def on_message(client, userdata, msg):
    global relay_state
    topic = msg.topic
    payload = msg.payload.decode()

    try:
        if topic == "arduino/input":
            data = json.loads(payload)
            current_values["temp"] = float(data.get("temp", 0.0))
            current_values["humi"] = float(data.get("humi", 0.0))
            current_values["pot"] = int(data.get("pot", 0))
            relay_state = bool(data.get("relay", False))

        elif topic == "arduino/output":
            relay_state = (payload.lower() == "post 3200 on")

        elif topic.startswith("arduino/led"):
            index = int(topic.replace("arduino/led", "")) - 1
            if 0 <= index < 8:
                led_states[index] = (payload == "1")

        update_ui()

    except Exception as e:
        print(f"❌ 메시지 처리 오류: {e}")

def connect_mqtt():
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"🚫 MQTT 연결 중 오류 발생: {e}")

# ==== UI 업데이트 ====
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
    weekday_kor = ["월", "화", "수", "목", "금", "토", "일"]
    date_label.config(text=now.strftime(f"%Y-%m-%d ({weekday_kor[now.weekday()]})"))
    time_label.config(text=now.strftime("%H:%M:%S"))
    window.after(1000, update_datetime)

def toggle_led(index):
    led_states[index] = not led_states[index]
    payload = "1" if led_states[index] else "0"
    client.publish(f"arduino/led{index+1}", payload)
    update_ui()

# ==== 카메라 스트림 ====
CAMERA_URL = "http://172.30.1.60:81/stream"
cap = cv2.VideoCapture(CAMERA_URL)

def update_camera():
    try:
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = img.resize((320, 240))
            imgtk = ImageTk.PhotoImage(image=img)
            camera_label.imgtk = imgtk
            camera_label.config(image=imgtk)
    except Exception as e:
        print(f"카메라 오류: {e}")
    window.after(100, update_camera)

# ==== GUI 구성 ====
window = tk.Tk()
window.title("ESP32 센서 모니터 + 카메라")
window.geometry("380x700")
window.resizable(False, False)

# 스크롤 가능한 프레임
canvas = tk.Canvas(window)
scrollbar = tk.Scrollbar(window, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# ==== 카메라 프레임 ====
tk.Label(scrollable_frame, text="📷 ESP32 카메라", font=("맑은 고딕", 13, "bold")).pack(pady=5)
camera_label = tk.Label(scrollable_frame)
camera_label.pack(pady=10)

# ==== LED 버튼 ====
led_buttons = []
led_layout = [3, 3, 2]
btn_index = 0
led_frame = tk.Frame(scrollable_frame)
led_frame.pack(pady=10)

for row, count in enumerate(led_layout):
    for col in range(count):
        if btn_index >= 8:
            break
        btn = tk.Button(
            led_frame,
            text=f"LED {btn_index + 1}",
            width=10,
            height=2,
            bg="light gray",
            activebackground="green",
            font=("맑은 고딕", 10, "bold"),
            command=lambda idx=btn_index: toggle_led(idx)
        )
        btn.grid(row=row, column=col, padx=8, pady=6)
        led_buttons.append(btn)
        btn_index += 1

# ==== 날짜 및 시간 ====
date_label = tk.Label(scrollable_frame, text="날짜", font=("맑은 고딕", 12))
date_label.pack(pady=4)

time_label = tk.Label(scrollable_frame, text="시간", font=("맑은 고딕", 12))
time_label.pack(pady=4)

# ==== 센서 데이터 ====
temp_label = tk.Label(scrollable_frame, text="🌡 온도: -- °C", font=("맑은 고딕", 14))
temp_label.pack(pady=4)

humi_label = tk.Label(scrollable_frame, text="💧 습도: -- %", font=("맑은 고딕", 14))
humi_label.pack(pady=4)

pot_label = tk.Label(scrollable_frame, text="🎛 가변저항: --", font=("맑은 고딕", 14))
pot_label.pack(pady=4)

# ==== 릴레이 상태 ====
relay_label = tk.Label(scrollable_frame, text="⚡ 릴레이 상태: OFF", font=("맑은 고딕", 14), fg="red")
relay_label.pack(pady=10)

# ==== 실행 ====
connect_mqtt()
update_datetime()
update_camera()

window.mainloop()
