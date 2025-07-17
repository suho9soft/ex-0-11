import tkinter as tk
from datetime import datetime
import paho.mqtt.client as mqtt
from gpiozero import LED

# 안전한 GPIO 핀 리스트 (BCM 기준)
led_pins = [5, 6, 13, 19, 26, 16, 20, 21]
leds = [LED(pin) for pin in led_pins]

# 상태 변수
relay_state = False
led_states = [False] * 8
current_values = {"temp": 0.0, "humi": 0.0, "pot": 0}

# MQTT 설정
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
            if led_states[i]:
                leds[i].on()
            else:
                leds[i].off()

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
    if led_states[index]:
        leds[index].on()
    else:
        leds[index].off()

    led_buttons[index].config(bg="green" if led_states[index] else "gray")
    payload = "1" if led_states[index] else "0"
    client.publish(f"arduino/led{index+1}", payload)

# Tkinter GUI
window = tk.Tk()
window.title("Tony Pi 센서 모니터")
window.geometry("600x480")
window.resizable(False, False)

label_font = ("맑은 고딕", 12)
data_font = ("맑은 고딕", 13)

date_label = tk.Label(window, text="", font=label_font)
date_label.pack(pady=3)

time_label = tk.Label(window, text="", font=label_font)
time_label.pack(pady=3)

temp_label = tk.Label(window, text="온도: -- °C", font=data_font)
temp_label.pack(pady=3)

humi_label = tk.Label(window, text="습도: -- %", font=data_font)
humi_label.pack(pady=3)

pot_label = tk.Label(window, text="가변저항: --", font=data_font)
pot_label.pack(pady=3)

relay_label = tk.Label(window, text="릴레이: OFF", font=data_font, fg="red")
relay_label.pack(pady=6)

led_frame = tk.Frame(window)
led_frame.pack(pady=8)

led_buttons = []
for i in range(8):
    row = i // 4
    col = i % 4
    btn = tk.Button(
        led_frame,
        text=f"LED {i+1}\nGPIO {led_pins[i]}",
        width=10,
        height=2,
        bg="gray",
        font=("맑은 고딕", 10),
        command=lambda idx=i: toggle_led(idx)
    )
    btn.grid(row=row, column=col, padx=5, pady=5)
    led_buttons.append(btn)

connect_mqtt()
update_datetime()
window.mainloop()
