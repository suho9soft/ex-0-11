from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# MQTT 브로커 정보
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

# 화면 크기 설정 (세로 15cm, 가로 7cm 기준)
Window.size = (360, 640)

class IoTDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        self.relay = False
        self.led_states = [False] * 8

        # 상단 날짜/시간
        self.date_label = Label(text="날짜", font_size=18, size_hint_y=None, height=30)
        self.time_label = Label(text="시간", font_size=18, size_hint_y=None, height=30)
        self.add_widget(self.date_label)
        self.add_widget(self.time_label)

        # 센서 데이터
        self.temp_label = Label(text="온도: -- °C", font_size=16)
        self.humi_label = Label(text="습도: -- %", font_size=16)
        self.pot_label = Label(text="조도: --", font_size=16)
        self.add_widget(self.temp_label)
        self.add_widget(self.humi_label)
        self.add_widget(self.pot_label)

        # 릴레이 상태
        self.relay_label = Label(text="릴레이: OFF", font_size=16, color=(1, 0, 0, 1))
        self.add_widget(self.relay_label)

        # LED 제어 버튼
        self.led_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=320)
        self.led_buttons = []

        for i in range(8):
            btn = Button(
                text=f"LED {i+1}",
                font_size=16,
                background_color=(0.5, 0.5, 0.5, 1),
                on_press=self.make_toggle_callback(i)
            )
            self.led_grid.add_widget(btn)
            self.led_buttons.append(btn)

        self.add_widget(self.led_grid)

        # 시간 갱신
        Clock.schedule_interval(self.update_time, 1)

        # MQTT 연결
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def update_time(self, dt):
        now = datetime.now()
        weekday = ['월', '화', '수', '목', '금', '토', '일'][now.weekday()]
        self.date_label.text = now.strftime(f"%Y-%m-%d ({weekday})")
        self.time_label.text = now.strftime("%H:%M:%S")

    def on_connect(self, client, userdata, flags, rc):
        print("✅ MQTT 연결됨" if rc == 0 else f"❌ 연결 실패: {rc}")
        client.subscribe("arduino/input")
        client.subscribe("arduino/output")
        for i in range(8):
            client.subscribe(f"arduino/led{i+1}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if topic == "arduino/input":
            try:
                data = json.loads(payload)
                temp = data.get("temp", 0.0)
                humi = data.get("humi", 0.0)
                pot = data.get("pot", 0)
                self.relay = bool(data.get("relay", False))

                self.temp_label.text = f"온도: {temp:.1f} °C"
                self.humi_label.text = f"습도: {humi:.1f} %"
                self.pot_label.text = f"조도: {pot}"
                self.relay_label.text = f"릴레이: {'ON' if self.relay else 'OFF'}"
                self.relay_label.color = (0, 1, 0, 1) if self.relay else (1, 0, 0, 1)
            except Exception as e:
                print("❌ JSON 오류:", e)

        elif topic == "arduino/output":
            self.relay = payload.strip().upper() == "ON"
            self.relay_label.text = f"릴레이: {'ON' if self.relay else 'OFF'}"
            self.relay_label.color = (0, 1, 0, 1) if self.relay else (1, 0, 0, 1)

        else:
            for i in range(8):
                if topic == f"arduino/led{i+1}":
                    self.led_states[i] = (payload == "1")
                    self.update_led_button(i)

    def make_toggle_callback(self, index):
        def toggle(instance):
            self.led_states[index] = not self.led_states[index]
            payload = "1" if self.led_states[index] else "0"
            self.client.publish(f"arduino/led{index+1}", payload)
            self.update_led_button(index)
        return toggle

    def update_led_button(self, index):
        btn = self.led_buttons[index]
        btn.background_color = (0, 1, 0, 1) if self.led_states[index] else (0.5, 0.5, 0.5, 1)

class IoTApp(App):
    def build(self):
        return IoTDashboard()

if __name__ == "__main__":
    IoTApp().run()
