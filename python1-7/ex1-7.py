import tkinter as tk
import random
import time
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# 전역 변수
relay_state = False
led_states = [False] * 8
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}

# 핀 번호 (ESP32 기준)
led_pins = [2, 4, 5, 18, 19, 25, 26, 27]

# MQTT 브로커 설정
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
client = mqtt.Client()

def on_message(client, userdata, msg):
    global relay_state, led_states
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == "arduino/output":
        relay_state = (payload.lower() == "post 3200 on")

    for i in range(8):
        if topic == f"arduino/led{i+1}":
            led_states[i] = (payload == "1")

    update_ui()

def connect_mqtt():
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe("arduino/output")
    for i in range(1, 9):
        client.subscribe(f"arduino/led{i}")
    client.loop_start()

def update_ui():
    temp_label.config(text=f"온도: {current_values['temp']:.1f} °C")
    humi_label.config(text=f"습도: {current_values['humi']:.1f} %")
    pot_label.config(text=f"가변저항: {current_values['pot']}")
    relay_label.config(text=f"릴레이: {'ON' if relay_state else 'OFF'}", fg="green" if relay_state else "red")
    for i in range(8):
        led_buttons[i].config(bg="green" if led_states[i] else "gray")

def update_datetime():
    now = datetime.now()
    weekday_kor = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    weekday = weekday_kor[now.weekday()]
    date_label.config(text=f"날짜: {now.strftime('%Y-%m-%d')} ({weekday})")
    time_label.config(text=f"시간: {now.strftime('%H:%M:%S')}")
    window.after(1000, update_datetime)

def toggle_led(index):
    led_states[index] = not led_states[index]
    led_buttons[index].config(bg="green" if led_states[index] else "gray")
    payload = "1" if led_states[index] else "0"
    client.publish(f"arduino/led{index+1}", payload)

# Tkinter GUI 설정
window = tk.Tk()
window.title("ESP32 센서 모니터")
window.geometry("500x520")
window.resizable(False, False)

date_label = tk.Label(window, text="", font=("맑은 고딕", 12))
date_label.pack(pady=5)

time_label = tk.Label(window, text="", font=("맑은 고딕", 12))
time_label.pack(pady=5)

temp_label = tk.Label(window, text="온도: -- °C", font=("맑은 고딕", 14))
temp_label.pack(pady=5)

humi_label = tk.Label(window, text="습도: -- %", font=("맑은 고딕", 14))
humi_label.pack(pady=5)

pot_label = tk.Label(window, text="가변저항: --", font=("맑은 고딕", 14))
pot_label.pack(pady=5)

relay_label = tk.Label(window, text="릴레이: OFF", font=("맑은 고딕", 14), fg="red")
relay_label.pack(pady=5)

led_frame = tk.Frame(window)
led_frame.pack(pady=10)

led_buttons = []
for i in range(8):
    row = i // 4
    col = i % 4
    btn = tk.Button(led_frame, text=f"LED {i+1}\n(GPIO {led_pins[i]})", width=12, height=3, bg="gray",
                    command=lambda idx=i: toggle_led(idx))
    btn.grid(row=row, column=col, padx=5, pady=5)
    led_buttons.append(btn)

# MQTT 연결 및 UI 시작
connect_mqtt()
update_datetime()
window.mainloop()
