import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
import json

relay_state = False
led_states = [False] * 8
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}
mqtt_connected = False

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("✅ MQTT 연결 성공")
        client.subscribe("arduino/input")
        client.subscribe("arduino/output")
        for i in range(1, 9):
            client.subscribe(f"arduino/led{i}")
    else:
        print(f"❌ MQTT 연결 실패: {rc}")

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
        print(f"🚫 MQTT 연결 오류: {e}")

def update_ui():
    temp_label.config(text=f"🌡 온도: {current_values['temp']:.1f} °C")
    humi_label.config(text=f"💧 습도: {current_values['humi']:.1f} %")
    pot_label.config(text=f"🎛 가변저항: {current_values['pot']}")
    relay_label.config(
        text=f"⚡ 릴레이: {'ON' if relay_state else 'OFF'}",
        fg="green" if relay_state else "red"
    )
    for i in range(8):
        new_color = "green" if led_states[i] else "gray"
        if led_buttons[i].cget("bg") != new_color:
            led_buttons[i].config(bg=new_color)

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

# --- GUI 시작 ---
window = tk.Tk()
window.title("ESP32 센서 모니터")
window.geometry("360x640")
window.resizable(True, True)

canvas = tk.Canvas(window)
scrollbar = tk.Scrollbar(window, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# 날짜/시간
date_label = tk.Label(scrollable_frame, text="", font=("맑은 고딕", 12))
date_label.pack(pady=5)
time_label = tk.Label(scrollable_frame, text="", font=("맑은 고딕", 12))
time_label.pack(pady=5)

# 센서 정보
sensor_frame = tk.Frame(scrollable_frame)
sensor_frame.pack(pady=10)

temp_label = tk.Label(sensor_frame, text="🌡 온도: -- °C", font=("맑은 고딕", 14))
temp_label.grid(row=0, column=0, padx=10, pady=5)

humi_label = tk.Label(sensor_frame, text="💧 습도: -- %", font=("맑은 고딕", 14))
humi_label.grid(row=0, column=1, padx=10, pady=5)

pot_label = tk.Label(sensor_frame, text="🎛 가변저항: --", font=("맑은 고딕", 14))
pot_label.grid(row=1, column=0, columnspan=2, pady=5)

# 릴레이 상태
relay_label = tk.Label(scrollable_frame, text="⚡ 릴레이: OFF", font=("맑은 고딕", 14), fg="red")
relay_label.pack(pady=10)

# LED 제어 버튼
led_frame = tk.LabelFrame(scrollable_frame, text="LED 제어 (GPIO)", font=("맑은 고딕", 12))
led_frame.pack(pady=10)

led_buttons = []
for i in range(8):
    btn = tk.Button(
        led_frame,
        text=f"LED {i+1}",
        width=10, height=2,
        bg="gray",
        font=("맑은 고딕", 10),
        command=lambda idx=i: toggle_led(idx)
    )
    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
    led_buttons.append(btn)

# 실행
connect_mqtt()
update_datetime()
window.mainloop()
