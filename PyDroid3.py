from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from datetime import datetime
import paho.mqtt.client as mqtt
import json

class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relay = False
        self.led_states = [False] * 8
        self.client = mqtt.Client()
        self.setup_mqtt()
        Clock.schedule_interval(self.update_time, 1)

    def setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect("broker.emqx.io", 1883, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT 연결 성공")
            client.subscribe("arduino/input")
            client.subscribe("arduino/output")
            for i in range(8):
                client.subscribe(f"arduino/led{i+1}")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        topic = msg.topic

        if topic == "arduino/input":
            try:
                data = json.loads(payload)
                self.ids.temp.text = f"온도: {data.get('temp', 0.0):.1f} °C"
                self.ids.humi.text = f"습도: {data.get('humi', 0.0):.1f} %"
                self.ids.pot.text = f"조도: {data.get('pot', 0)}"
                self.relay = data.get("relay", False)
                self.ids.relay.text = f"릴레이: {'ON' if self.relay else 'OFF'}"
                self.ids.relay.color = (0,1,0,1) if self.relay else (1,0,0,1)
            except Exception as e:
                print("JSON 파싱 오류:", e)
        elif topic == "arduino/output":
            self.relay = (payload.strip().upper() == "ON")
            self.ids.relay.text = f"릴레이: {'ON' if self.relay else 'OFF'}"
        else:
            for i in range(8):
                if topic == f"arduino/led{i+1}":
                    self.led_states[i] = payload == "1"
                    self.update_led_button(i)

    def update_led_button(self, idx):
        btn = self.ids.get(f"led{idx+1}")
        if btn:
            btn.background_color = (0,1,0,1) if self.led_states[idx] else (0.5,0.5,0.5,1)

    def toggle_led(self, idx):
        self.led_states[idx] = not self.led_states[idx]
        payload = "1" if self.led_states[idx] else "0"
        self.client.publish(f"arduino/led{idx+1}", payload)
        self.update_led_button(idx)

    def update_time(self, dt):
        now = datetime.now()
        self.ids.date.text = now.strftime("%m/%d (%a)")
        self.ids.time.text = now.strftime("%H:%M:%S")

class IoTApp(App):
    def build(self):
        return MainLayout()
