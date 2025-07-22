import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# 전역 상태
relay_state = False
led_states = [False] * 8
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}
mqtt_connected = False

# MQTT 설정
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
client = mqtt.Client()

# MQTT 메시지 수신 처리
def on_message(client, userdata, msg):
    global relay_state, led_states
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == "arduino/input":
        try:
            data = json.loads(payload)
            current_values["temp"] = float(data.get("temp", 0.0))
            current_values["humi"] = float(data.get("humi", 0.0))
            current_values["pot"] = int(data.get("pot", 0))
            relay_state = bool(data.get("relay", False))
        except Exception as e:
            print(f"❌ JSON 파싱 실패: {e}")

    elif topic == "arduino/output":
        relay_state = (payload.lower() == "post 3200 on")

    else:
        for i in range(8):
            if topic == f"arduino/led{i+1}":
                led_states[i] = (payload == "1")

    update_ui()

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

def connect_mqtt():
    client.on_message = on_message
    client.on_connect = on_connect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"🚫 MQTT 연결 오류: {e}")

# UI 갱신
def update_ui():
    temp_label.config(text=f"🌡 온도: {current_values['temp']:.1f} °C")
    humi_label.config(text=f"💧 습도: {current_values['humi']:.1f} %")
    pot_label.config(text=f"🎛 가변저항: {current_values['pot']}")
    relay_label.config(text=f"⚡ 릴레이: {'ON' if relay_state else 'OFF'}",
                       fg="green" if relay_state else "red")
    for i in range(8):
        led_buttons[i].config(bg="green" if led_states[i] else "gray")

# 시간 표시
def update_datetime():
    now = datetime.now()
    weekday_kor = ["월", "화", "수", "목", "금", "토", "일"]
    date_label.config(text=now.strftime(f"%Y-%m-%d ({weekday_kor[now.weekday()]})"))
    time_label.config(text=now.strftime("%H:%M:%S"))
    window.after(1000, update_datetime)

# LED 토글
def toggle_led(index):
    led_states[index] = not led_states[index]
    payload = "1" if led_states[index] else "0"
    client.publish(f"arduino/led{index+1}", payload)
    update_ui()

# GUI 초기화
window = tk.Tk()
window.title("ESP32 실시간 센서 모니터")
window.geometry("520x550")
window.resizable(False, False)

# 날짜/시간
date_label = tk.Label(window, text="", font=("맑은 고딕", 12))
date_label.pack(pady=5)
time_label = tk.Label(window, text="", font=("맑은 고딕", 12))
time_label.pack(pady=5)

# 센서 정보
sensor_frame = tk.Frame(window)
sensor_frame.pack(pady=10)

temp_label = tk.Label(sensor_frame, text="온도: -- °C", font=("맑은 고딕", 14))
temp_label.grid(row=0, column=0, padx=10, pady=5)

humi_label = tk.Label(sensor_frame, text="습도: -- %", font=("맑은 고딕", 14))
humi_label.grid(row=0, column=1, padx=10, pady=5)

pot_label = tk.Label(sensor_frame, text="가변저항: --", font=("맑은 고딕", 14))
pot_label.grid(row=1, column=0, columnspan=2, pady=5)

# 릴레이 상태
relay_label = tk.Label(window, text="릴레이: OFF", font=("맑은 고딕", 14), fg="red")
relay_label.pack(pady=10)

# LED 버튼들
led_frame = tk.LabelFrame(window, text="LED 제어 (GPIO)", font=("맑은 고딕", 12))
led_frame.pack(pady=10)

led_buttons = []
for i in range(8):
    btn = tk.Button(
        led_frame,
        text=f"LED {i+1}",
        width=12, height=3,
        bg="gray",
        command=lambda idx=i: toggle_led(idx)
    )
    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
    led_buttons.append(btn)

# 시작
connect_mqtt()
update_datetime()
window.mainloop()

