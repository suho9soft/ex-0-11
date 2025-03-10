import tkinter as tk

from tkinter import font

import paho.mqtt.client as mqtt



# MQTT 브로커 정보

MQTT_BROKER = "broker.emqx.io"

MQTT_PORT = 1883

MQTT_TOPICS = [

    "arduino/led1", "arduino/led2", "arduino/led3", "arduino/led4",

    "arduino/led5", "arduino/led6", "arduino/led7", "arduino/led8",

]



# MQTT 클라이언트 초기화

client = mqtt.Client()



# MQTT 연결 함수

def connect_mqtt():

    try:

        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        print("Connected to MQTT Broker!")

        client.loop_start()

    except Exception as e:

        print(f"Failed to connect to MQTT Broker: {e}")



# 연결 재시도 함수

def on_disconnect(client, userdata, rc):

    print("Disconnected from MQTT Broker")

    connect_mqtt()



client.on_disconnect = on_disconnect



# LED 제어 함수

def toggle_led(index):

    current_state = led_states[index].get()

    new_state = not current_state

    toggle_led_text = "켜짐" if new_state else "꺼짐"

    client.publish(MQTT_TOPICS[index], "1" if new_state else "0")

    buttons[index].configure(

        text=f"버튼 {index+1} ({toggle_led_text})",

        bg="#FF5252" if new_state else "#1976D2"

    )

    led_states[index].set(new_state)



# GUI 생성

def create_gui():

    window = tk.Tk()

    window.title("Zerg Hive Control")

    window.geometry("650x1300")

    window.configure(bg="#1E1E1E")



    canvas = tk.Canvas(window, bg="#1E1E1E", highlightthickness=0)

    scrollbar = tk.Scrollbar(window, orient="vertical", command=canvas.yview)

    scroll_frame = tk.Frame(canvas, bg="#1E1E1E")

    canvas.create_window((325, 0), window=scroll_frame, anchor="n")

    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")

    canvas.pack(side="left", fill="both", expand=True)

    

    def update_scroll_region(event=None):

        canvas.configure(scrollregion=canvas.bbox("all"))

    scroll_frame.bind("<Configure>", update_scroll_region)



    title_font = font.Font(family="Arial", size=24, weight="bold")

    label_font = font.Font(family="Arial", size=16)

    button_font = font.Font(family="Arial", size=14, weight="bold")



    title = tk.Label(

        scroll_frame, text="ZERG HIVE CONTROL", font=title_font,

        bg="#1E1E1E", fg="#4FC3F7"

    )

    title.pack(pady=20)



    labels = [

        "1. Hatchery", "2. Hatchery", "3. Spawning Pool", "4. Hydralisk Den",

        "5. Evolution Chamber", "6. Lair", "7. Hive", "8. Nydus Canal"

    ]

    global buttons, led_states

    buttons = []

    led_states = [tk.BooleanVar(value=False) for _ in labels]



    for i, label in enumerate(labels):

        lbl_frame = tk.Frame(scroll_frame, bg="#1E1E1E")

        lbl_frame.pack(fill="x", padx=30, pady=5)

        lbl_num = tk.Label(

            lbl_frame, text=f"{i+1}.", font=label_font,

            bg="#1E1E1E", fg="#E0E0E0", width=3, anchor="e"

        )

        lbl_num.pack(side="left")

        lbl_text = tk.Label(

            lbl_frame, text=f"{label[3:]}", font=label_font,

            bg="#1E1E1E", fg="#E0E0E0", anchor="w"

        )

        lbl_text.pack(side="left", expand=True)



        btn = tk.Button(

            scroll_frame, text=f"버튼 {i+1} (꺼짐)", font=button_font,

            width=20, height=2, bg="#1976D2", fg="#FFFFFF",

            activebackground="#1565C0", activeforeground="#E3F2FD",

            command=lambda idx=i: toggle_led(idx),

            relief="raised", bd=5

        )

        btn.pack(pady=10, fill="x", expand=True)

        buttons.append(btn)



    window.mainloop()



if __name__ == "__main__":

    connect_mqtt()

    create_gui()

