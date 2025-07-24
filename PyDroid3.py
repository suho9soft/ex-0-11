import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import threading
import requests
from PIL import Image, ImageTk
from io import BytesIO

# --- 상태 변수 ---
relay_state = False
led_states = [False] * 8
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}
mqtt_connected = False
latest_img_width = 320
latest_img_height = 240

# --- MQTT 설정 ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
client = mqtt.Client()

# --- MQTT 콜백 함수 ---
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

# --- UI 업데이트 함수 ---
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

# --- MJPEG 스트림 읽기 ---
CAMERA_URL = "http://172.30.1.60:81/stream"
stop_camera = False

def mjpeg_stream():
    global stop_camera, latest_img_width, latest_img_height
    try:
        stream = requests.get(CAMERA_URL, stream=True, timeout=5)
        bytes_data = b""
        for chunk in stream.iter_content(chunk_size=1024):
            if stop_camera:
                break
            bytes_data += chunk
            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')
            if a != -1 and b != -1 and b > a:
                jpg = bytes_data[a:b+2]
                bytes_data = bytes_data[b+2:]
                try:
                    img = Image.open(BytesIO(jpg))
                    # 원본 크기 저장
                    latest_img_width, latest_img_height = img.size
                    # 사이즈 조절 (최대 320px 너비 기준, 비율 유지)
                    max_width = 320
                    ratio = max_width / latest_img_width
                    new_w = int(latest_img_width * ratio)
                    new_h = int(latest_img_height * ratio)
                    img = img.resize((new_w, new_h))
                    imgtk = ImageTk.PhotoImage(image=img)

                    # 메인 스레드에서 GUI 업데이트
                    def update_img():
                        camera_label.imgtk = imgtk
                        camera_label.config(image=imgtk)
                        adjust_layout()

                    window.after(0, update_img)

                except Exception as e:
                    print(f"이미지 변환 오류: {e}")
    except Exception as e:
        print(f"스트림 연결 오류: {e}")

# --- 레이아웃 조정 함수 ---
def adjust_layout():
    # 비율 판단 (가로/세로)
    if latest_img_width == 0 or latest_img_height == 0:
        return  # 이미지 없으면 건너뜀

    ratio = latest_img_width / latest_img_height
    if ratio > 1:  
        # 가로 모드: 영상 왼쪽, 센서UI 오른쪽 (좌우 배치)
        if not layout_frame.winfo_ismapped():
            layout_frame.pack_forget()
            layout_frame.pack(fill="both", expand=True)
        camera_label.pack_forget()
        control_frame.pack_forget()

        main_container.pack_forget()
        main_container.pack(fill="both", expand=True)

        camera_label.pack(side="left", padx=10, pady=10)
        control_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    else:
        # 세로 모드: 영상 위, 센서UI 아래 (상하 배치)
        if not layout_frame.winfo_ismapped():
            layout_frame.pack_forget()
            layout_frame.pack(fill="both", expand=True)
        camera_label.pack_forget()
        control_frame.pack_forget()

        main_container.pack_forget()
        main_container.pack(fill="both", expand=True)

        camera_label.pack(side="top", padx=10, pady=10)
        control_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

# --- GUI 세팅 ---
window = tk.Tk()
window.title("ESP32 센서 모니터 + 카메라 (가로/세로 모드 자동)")
window.geometry("600x700")
window.resizable(True, True)

# 메인 컨테이너 프레임
main_container = tk.Frame(window)
main_container.pack(fill="both", expand=True)

# 내부 레이아웃 조정을 위한 프레임 (이걸로 가로/세로 레이아웃 조정)
layout_frame = tk.Frame(main_container)
layout_frame.pack(fill="both", expand=True)

# 카메라 라벨 (영상 표시)
camera_label = tk.Label(layout_frame)

# 센서 + 버튼 UI 프레임 (control_frame)
control_frame = tk.Frame(layout_frame)

# LED 버튼 8개
led_buttons = []
led_layout = [3, 3, 2]
btn_index = 0
led_frame = tk.Frame(control_frame)
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

# 날짜 및 시간
date_label = tk.Label(control_frame, text="날짜", font=("맑은 고딕", 12))
date_label.pack(pady=4)
time_label = tk.Label(control_frame, text="시간", font=("맑은 고딕", 12))
time_label.pack(pady=4)

# 센서 데이터
temp_label = tk.Label(control_frame, text="🌡 온도: -- °C", font=("맑은 고딕", 14))
temp_label.pack(pady=4)
humi_label = tk.Label(control_frame, text="💧 습도: -- %", font=("맑은 고딕", 14))
humi_label.pack(pady=4)
pot_label = tk.Label(control_frame, text="🎛 가
