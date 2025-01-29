import tkinter as tk
from tkinter import font
import paho.mqtt.client as mqtt
import threading


MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPICS = [
    "arduino/led1",
    "arduino/led2",
    "arduino/led3",
    "arduino/led4",
    "arduino/led5",
    "arduino/led6",
    "arduino/led7",
    "arduino/led8",
]


client = mqtt.Client()

def connect_mqtt():
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("Connected to MQTT Broker!")
        client.loop_start()  
    except Exception as e:
        print(f"Failed to connect to MQTT Broker: {e}")


def toggle_led(topic, state):
    payload = "1" if state else "0"
    client.publish(topic, payload)
    print(f"Published to {topic}: {payload}")


def create_gui():
    window = tk.Tk()
    window.title("Zerg Hive Control")
    window.geometry("500x700")
    window.configure(bg="white")  


    zerg_font = font.Font(family="Courier New", size=12, weight="bold")
    zerg_title_font = font.Font(family="Courier New", size=18, weight="bold")

    
    title = tk.Label(
        window,
        text="?? ZERG HIVE CONTROL ??",
        font=zerg_title_font,
        bg="white",
        fg="black"
    )
    title.pack(pady=20)

    
    labels = [
        "Hatchery 1", "Hatchery 2", "Spawning Pool", "Hydralisk Den",
        "Evolution Chamber", "Lair", "Hive", "Nydus Canal"
    ]
    buttons = []

    
    for i, label in enumerate(labels):
        led_state = tk.BooleanVar(value=False)

        
        def toggle(index=i):
            current_state = led_state.get()
            toggle_led(MQTT_TOPICS[index], not current_state)
            led_state.set(not current_state)
            buttons[index].configure(
                bg="light gray" if led_state.get() else "white", 
                fg="black"
            )

        
        lbl = tk.Label(
            window,
            text=f"{label} (LED {i+1})",
            font=zerg_font,
            bg="white",
            fg="black"
        )
        lbl.pack(pady=5)

        
        btn = tk.Button(
            window,
            text=f"Toggle LED {i+1}",
            font=zerg_font,
            width=20,
            height=2,
            bg="white",
            fg="black",
            activebackground="light gray",
            activeforeground="black",
            command=lambda idx=i: toggle(idx),  
            relief="raised",
            bd=6,
        )
        btn.pack(pady=5)
        buttons.append(btn)

    
    window.mainloop()


if __name__ == "__main__":
    connect_mqtt()
    
    gui_thread = threading.Thread(target=create_gui)
    gui_thread.start()
