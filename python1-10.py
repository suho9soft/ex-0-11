import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import pymysql
import time

# =================== 전역 상태 ===================
relay_state = False  # 릴레이 ON/OFF
led_states = [False] * 8  # 8개 LED 상태
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}
mqtt_connected = False

# =================== MySQL 설정 ===================
DB_CONFIG = {
    "host": "localhost",
    "user": "arduino",
    "password": "123f5678",
    "database": "python1"
}

# =================== DB 저장 함수 ===================
def insert_data_to_mysql(temp, humi, pot, relay_onoff):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        sql = """
            INSERT INTO final_data (rotary, temp, humi, switch_status, data)
            VALUES (%s, %s, %s, %s, %s);
        """
        val = (pot, temp, humi, "ON" if relay_onoff else "OFF", now)
        cursor.execute(sql, val)
        conn.commit()
        print(f"✅ DB 저장 완료: {val}")
    except pymysql.MySQLError as e:
        print(f"❌ MySQL 오류: {e}")
    finally:
        cursor.close()
        conn.close()

# =================== MQTT 설정 ===================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
client = mqtt.Client()

def on_message(client, userdata, msg):
    global relay_state, led_states

    topic = msg.topic
    payload = msg.payload.decode()
    print(f"📩 수신됨: {topic} → {payload}")

    if topic == "arduino/input":
        try:
            data = json.loads(payload)
            current_values["temp"] = float(data.get("temp", 0.0))
            current_values["humi"] = float(data.get("humi", 0.0))
            current_values["pot"] = int(data.get("pot", 0))
            relay_state = bool(data.get("relay", False))

            # DB 저장
            insert_data_to_mysql(
                current_values["temp"],
                current_values["humi"],
                current_values["pot"],
                relay_state
            )

        except Exception as e:
            print(f"❌ JSON 파싱 오류: {e}")

    elif topic == "arduino/output":
        relay_state = (payload.strip().upper() == "ON")

    else:
        for i in range(8):
            if topic == f"arduino/led{i+1}":
                led_states[i] = (payload == "1")

    update_ui()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        global mqtt_connected
        mqtt_connected = True
        print("✅ MQTT 연결 성공")
        client.subscribe("arduino/input")
        client.subscribe("arduino/output")
        for i in range(1, 9):
            client.subscribe(f"arduino/led{i}")
    else:
        print(f"❌ MQTT 연결 실패: {rc}")

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print("⚠️ MQTT 연결 끊김")

def connect_mqtt():
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("📡 MQTT 시작")
    except Exception as e:
        print(f"🚫 MQTT 오류: {e}")

# =================== UI 갱신 함수 ===================
def update_ui():
    temp_label.config(text=f"🌡 온도: {current_values['temp']:.1f} °C")
    humi_label.config(text=f"💧 습도: {current_values['humi']:.1f} %")
    pot_label.config(text=f"🎛 가변저항: {current_values['pot']}")
    relay_label.config(
        text=f"⚡ 릴레이: {'ON' if relay_state else 'OFF'}",
        fg="green" if relay_state else "red"
    )
    for i in range(8):
        led_buttons[i].config(bg="green" if led_states[i] else "gray")

def update_datetime():
    now = datetime.now()
    weekday_kor = ["월", "화", "수", "목", "금", "토", "일"]
    date_label.config(text=now.strftime(f"%Y-%m-%d ({weekday_kor[now.weekday()]})"))
    time_label.config(text=now.strftime("%H:%M:%S"))
    window.after(1000, update_datetime)

# =================== LED 제어 ===================
def toggle_led(index):
    led_states[index] = not led_states[index]
    payload = "1" if led_states[index] else "0"
    client.publish(f"arduino/led{index+1}", payload)
    print(f"🔀 LED{index+1} → {payload}")
    update_ui()

# =================== GUI ===================
window = tk.Tk()
window.title("ESP32 센서 모니터 - Raspberry Pi 5")
window.geometry("520x550")
window.resizable(False, False)

date_label = tk.Label(window, text="", font=("Arial", 12))
date_label.pack(pady=5)
time_label = tk.Label(window, text="", font=("Arial", 12))
time_label.pack(pady=5)

sensor_frame = tk.Frame(window)
sensor_frame.pack(pady=10)

temp_label = tk.Label(sensor_frame, text="온도: -- °C", font=("Arial", 14))
temp_label.grid(row=0, column=0, padx=10, pady=5)

humi_label = tk.Label(sensor_frame, text="습도: -- %", font=("Arial", 14))
humi_label.grid(row=0, column=1, padx=10, pady=5)

pot_label = tk.Label(sensor_frame, text="가변저항: --", font=("Arial", 14))
pot_label.grid(row=1, column=0, columnspan=2, pady=5)

relay_label = tk.Label(window, text="릴레이: OFF", font=("Arial", 14), fg="red")
relay_label.pack(pady=10)

led_frame = tk.LabelFrame(window, text="LED 제어 (GPIO)", font=("Arial", 12))
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

# =================== 실행 ===================
time.sleep(1)
connect_mqtt()
update_datetime()
window.mainloop()
