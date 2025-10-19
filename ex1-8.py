import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import threading
import json
import pymysql
from datetime import datetime

# --- MQTT & DB 설정 ---
BROKER = "broker.emqx.io"
PORT = 1883
SUB_TOPIC_SENSOR = "arduino/input"
PUB_TOPIC_OUTPUT = "arduino/output"

DB_CONFIG = {
    "host": "localhost",
    "user": "arduino",
    "password": "123f5678",
    "database": "python1"
}

led_pins = [2, 4, 5, 18, 19, 25, 26, 27]
led_states = [False] * 8
relay_state = False
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}

# --- DB 저장 함수 ---
def insert_data(rotary, temp, humi):
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        sql = "INSERT INTO final_data (rotary, temp, humi, data) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (rotary, temp, humi, now))
        conn.commit()
        print("✅ DB 저장 완료")
    except Exception as e:
        print(f"❌ DB 저장 오류: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- MQTT 콜백 ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT 연결 성공")
        client.subscribe(SUB_TOPIC_SENSOR)
        client.subscribe(PUB_TOPIC_OUTPUT)
        for i in range(8):
            client.subscribe(f"arduino/led{i+1}")
    else:
        print(f"❌ MQTT 연결 실패: {rc}")

def on_message(client, userdata, msg):
    global relay_state, led_states

    topic = msg.topic
    payload = msg.payload.decode()

    if topic == SUB_TOPIC_SENSOR:
        try:
            data = json.loads(payload)
            rotary = int(data.get("rotary", 0))
            temp = float(data.get("temp", 0)) / 10
            humi = float(data.get("humi", 0)) / 10

            current_values["temp"] = temp
            current_values["humi"] = humi
            current_values["pot"] = rotary

            root.after(0, update_sensor_ui, payload, rotary, temp, humi)
            threading.Thread(target=insert_data, args=(rotary, temp, humi), daemon=True).start()
        except Exception as e:
            print(f"❌ 센서 메시지 처리 오류: {e}")

    elif topic == PUB_TOPIC_OUTPUT:
        relay_state = (payload.lower() == "post 3200 on")
        root.after(0, update_status_ui)

    elif topic.startswith("arduino/led"):
        try:
            led_num = int(topic.replace("arduino/led", "")) - 1
            led_states[led_num] = (payload == "1")
            root.after(0, update_status_ui)
        except Exception as e:
            print(f"❌ LED 메시지 처리 오류: {e}")

# --- UI 업데이트 함수 ---
def update_sensor_ui(msg, rotary, temp, humi):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, f"수신: {msg}\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)

    pot_value_label.config(text=f"{rotary}")
    temp_value_label.config(text=f"{temp:.1f} ℃")
    humi_value_label.config(text=f"{humi:.1f} %")
    update_datetime_ui()

def update_status_ui():
    relay_value_label.config(text="ON" if relay_state else "OFF",
                              fg="green" if relay_state else "red")
    for i in range(8):
        led_buttons[i].config(bg="green" if led_states[i] else "gray")

def update_datetime_ui():
    now = datetime.now()
    weekday_kor = ["월", "화", "수", "목", "금", "토", "일"]
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')
    date_value_label.config(text=f"{date_str} ({weekday_kor[now.weekday()]})")
    time_value_label.config(text=time_str)

def update_datetime():
    update_datetime_ui()
    root.after(1000, update_datetime)

def toggle_led(index):
    led_states[index] = not led_states[index]
    led_buttons[index].config(bg="green" if led_states[index] else "gray")
    payload = "1" if led_states[index] else "0"
    threading.Thread(target=lambda: client.publish(f"arduino/led{index+1}", payload), daemon=True).start()

def publish_message():
    msg = {"name": "arduino", "age": 20, "gender": "male"}
    client.publish(PUB_TOPIC_OUTPUT, json.dumps(msg))
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, "메시지 전송 완료!\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)

def on_close():
    try:
        client.loop_stop()
        client.disconnect()
    except:
        pass
    root.destroy()

# --- GUI 생성 ---
root = tk.Tk()
root.title("Arduino MQTT 모니터링")
root.geometry("700x700")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_close)

# 날짜/시간 표시
datetime_frame = ttk.Frame(root)
datetime_frame.pack(pady=8, fill=tk.X)

ttk.Label(datetime_frame, text="날짜:", font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, padx=5)
date_value_label = ttk.Label(datetime_frame, text="--", font=("Arial", 12))
date_value_label.grid(row=0, column=1, sticky=tk.W)

ttk.Label(datetime_frame, text="시간:", font=("Arial", 12)).grid(row=0, column=2, sticky=tk.W, padx=5)
time_value_label = ttk.Label(datetime_frame, text="--", font=("Arial", 12))
time_value_label.grid(row=0, column=3, sticky=tk.W)

# 센서 값 표시
sensor_frame = ttk.Frame(root)
sensor_frame.pack(pady=8, fill=tk.X)

ttk.Label(sensor_frame, text="온도:", font=("Arial", 14)).grid(row=0, column=0, sticky=tk.W, padx=10)
temp_value_label = ttk.Label(sensor_frame, text="-- ℃", font=("Arial", 14))
temp_value_label.grid(row=0, column=1, sticky=tk.W, padx=5)

ttk.Label(sensor_frame, text="습도:", font=("Arial", 14)).grid(row=0, column=2, sticky=tk.W, padx=10)
humi_value_label = ttk.Label(sensor_frame, text="-- %", font=("Arial", 14))
humi_value_label.grid(row=0, column=3, sticky=tk.W, padx=5)

ttk.Label(sensor_frame, text="가변저항:", font=("Arial", 14)).grid(row=0, column=4, sticky=tk.W, padx=10)
pot_value_label = ttk.Label(sensor_frame, text="--", font=("Arial", 14))
pot_value_label.grid(row=0, column=5, sticky=tk.W, padx=5)

ttk.Label(sensor_frame, text="릴레이:", font=("Arial", 14)).grid(row=0, column=6, sticky=tk.W, padx=10)
relay_value_label = ttk.Label(sensor_frame, text="OFF", font=("Arial", 14), foreground="red")
relay_value_label.grid(row=0, column=7, sticky=tk.W, padx=5)

# 로그 출력
log_label = ttk.Label(root, text="MQTT 메시지 로그", font=("Arial", 12))
log_label.pack(pady=(15, 0))

log_text = tk.Text(root, height=15, width=85, state=tk.DISABLED, font=("Arial", 11))
log_text.pack(padx=10, pady=5)

# 메시지 전송 버튼
send_btn = ttk.Button(root, text="메시지 전송", command=publish_message)
send_btn.pack(pady=10)

# LED 버튼 표시
led_frame = ttk.Frame(root)
led_frame.pack(pady=10)

led_buttons = []
for i in range(8):
    btn = tk.Button(led_frame, text=f"LED {i+1}\n(GPIO {led_pins[i]})", width=12, height=3,
                    bg="gray", command=lambda idx=i: toggle_led(idx))
    btn.grid(row=i//4, column=i%4, padx=8, pady=8)
    led_buttons.append(btn)

# --- MQTT 시작 ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

update_datetime()
root.mainloop()
