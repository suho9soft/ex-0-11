from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# MQTT 설정
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

# Note20 Ultra 픽셀 기준
Window.size = (dp(360), dp(760))  # 실제 해상도보다는 논리Dp로 조정

class IoTDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(12), **kwargs)
        self.relay = False
        self.led_states = [False] * 8

        # 날짜/시간
        self.date_label = Label(font_size=sp(18), size_hint_y=None, height=dp(32))
        self.time_label = Label(font_size=sp(18), size_hint_y=None, height=dp(32))
        self.add_widget(self.date_label)
        self.add_widget(self.time_label)

        # 센서 텍스트
        for tid in ['temp', 'humi', 'pot']:
            label = Label(text="–", font_size=sp(16))
            setattr(self, f"{tid}_label", label)
            self.add_widget(label)

        # 릴레이 상태
        self.relay_label = Label(text="릴레이: OFF", font_size=sp(16), color=(1, 0, 0, 1))
        self.add_widget(self.relay_label)

        # LED 버튼 Grid (2열 × 4행)
        self.led_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(360))
        self.led_buttons = []
        for i in range(8):
            btn = Button(text=f"LED {i+1}",
                         font_size=sp(16),
                         background_color=(0.5, 0.5, 0.5, 1),
                         on_press=self.toggle_led(i))
            self.led_buttons.append(btn)
            self.led_grid.add_widget(btn)
        self.add_widget(self.led_grid)

        # 시간 업데이트
        Clock.schedule_interval(self.update_datetime, 1)

        # MQTT 초기화
        self.client = mqtt.Client()
        self.client.on_connect = self.on_mqtt_connect
        self.client.on_message = self.on_mqtt_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def update_datetime(self, dt):
        now = datetime.now()
        wk = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
        self.date_label.text = now.strftime(f"%Y-%m-%d ({wk})")
        self.time_label.text = now.strftime("%H:%M:%S")

    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("arduino/input")
            client.subscribe("arduino/output")
            for i in range(1, 9):
                client.subscribe(f"arduino/led{i}")
        else:
            print("MQTT 연결 실패:", rc)

    def on_mqtt_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        if topic == "arduino/input":
            try:
                data = json.loads(payload)
                self.temp_label.text = f"온도: {data.get('temp', 0.0):.1f} °C"
                self.humi_label.text = f"습도: {data.get('humi', 0.0):.1f} %"
                self.pot_label.text = f"조도: {data.get('pot', 0)}"
                self.relay = bool(data.get("relay", False))
                self.update_relay()
            except Exception as e:
                print("JSON 오류:", e)
        elif topic == "arduino/output":
            self.relay = (payload.strip().upper() == "ON")
            self.update_relay()
        else:
            for i in range(8):
                if topic == f"arduino/led{i+1}":
                    state = (payload == "1")
                    self.led_states[i] = state
                    self.led_buttons[i].background_color = (0,1,0,1) if state else (0.5,0.5,0.5,1)

    def update_relay(self):
        self.relay_label.text = f"릴레이: {'ON' if self.relay else 'OFF'}"
        self.relay_label.color = (0,1,0,1) if self.relay else (1,0,0,1)

    def toggle_led(self, idx):
        def callback(instance):
            new_state = not self.led_states[idx]
            self.led_states[idx] = new_state
            self.client.publish(f"arduino/led{idx+1}", "1" if new_state else "0")
            self.led_buttons[idx].background_color = (0,1,0,1) if new_state else (0.5,0.5,0.5,1)
        return callback

class IoTApp(App):
    def build(self):
        return IoTDashboard()

if __name__ == "__main__":
    IoTApp().run()
