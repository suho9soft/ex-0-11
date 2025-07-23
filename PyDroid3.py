from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.core.text import LabelBase
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# ✅ 한글 폰트 등록 (글자 깨짐 방지)
LabelBase.register(name="NotoSans", fn_regular="NotoSansCJK-Regular.ttf")

Window.size = (dp(360), dp(760))

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883


class IoTDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(10), **kwargs)

        font_kwargs = {"font_name": "NotoSans"}

        # 날짜 & 시간
        self.date_label = Label(text="", font_size=sp(18), size_hint_y=None, height=dp(30), **font_kwargs)
        self.time_label = Label(text="", font_size=sp(18), size_hint_y=None, height=dp(30), **font_kwargs)
        self.add_widget(self.date_label)
        self.add_widget(self.time_label)

        # 센서 데이터
        self.temp_label = Label(text="온도: -- °C", font_size=sp(16), size_hint_y=None, height=dp(30), **font_kwargs)
        self.humi_label = Label(text="습도: -- %", font_size=sp(16), size_hint_y=None, height=dp(30), **font_kwargs)
        self.pot_label = Label(text="가변저항: --", font_size=sp(16), size_hint_y=None, height=dp(30), **font_kwargs)
        self.add_widget(self.temp_label)
        self.add_widget(self.humi_label)
        self.add_widget(self.pot_label)

        # 릴레이 상태
        self.relay_label = Label(text="릴레이: OFF", font_size=sp(16), size_hint_y=None, height=dp(30),
                                 color=(1, 0, 0, 1), **font_kwargs)
        self.add_widget(self.relay_label)

        # LED 버튼들
        self.led_grid = GridLayout(cols=2, spacing=dp(10), padding=dp(10), size_hint_y=None)
        self.led_grid.bind(minimum_height=self.led_grid.setter('height'))

        self.led_buttons = []
        self.led_states = [False] * 8

        for i in range(8):
            btn = Button(
                text=f"LED {i + 1}",
                font_size=sp(16),
                size_hint=(1, None),
                height=dp(50),
                background_normal='',
                background_color=(0.7, 0.7, 0.7, 1),
                color=(0, 0, 0, 1),
                **font_kwargs
            )
            btn.bind(on_press=self.make_led_callback(i))
            self.led_buttons.append(btn)
            self.led_grid.add_widget(btn)

        self.add_widget(self.led_grid)

        # MQTT
        self.relay = False
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

        Clock.schedule_interval(self.update_time, 1)

    def update_time(self, dt):
        now = datetime.now()
        weekday = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
        self.date_label.text = now.strftime(f"%Y-%m-%d ({weekday})")
        self.time_label.text = now.strftime("%H:%M:%S")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("arduino/input")
            client.subscribe("arduino/output")
            for i in range(1, 9):
                client.subscribe(f"arduino/led{i}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if topic == "arduino/input":
            try:
                data = json.loads(payload)
                self.temp_label.text = f"온도: {data.get('temp', 0.0):.1f} °C"
                self.humi_label.text = f"습도: {data.get('humi', 0.0):.1f} %"
                self.pot_label.text = f"가변저항: {data.get('pot', 0)}"
                self.relay = bool(data.get("relay", False))
                self.update_relay()
            except Exception as e:
                print(f"[오류] JSON 파싱 실패: {e}")

        elif topic == "arduino/output":
            self.relay = (payload.strip().upper() == "ON")
            self.update_relay()

        else:
            for i in range(8):
                if topic == f"arduino/led{i + 1}":
                    state = (payload == "1")
                    self.led_states[i] = state
                    self.update_led_button(i, state)

    def update_relay(self):
        self.relay_label.text = f"릴레이: {'ON' if self.relay else 'OFF'}"
        self.relay_label.color = (0, 1, 0, 1) if self.relay else (1, 0, 0, 1)

    def update_led_button(self, index, state):
        color = (0.2, 1, 0.2, 1) if state else (0.7, 0.7, 0.7, 1)
        self.led_buttons[index].background_color = color

    def make_led_callback(self, idx):
        def callback(instance):
            new_state = not self.led_states[idx]
            self.led_states[idx] = new_state
            self.client.publish(f"arduino/led{idx + 1}", "1" if new_state else "0")
            self.update_led_button(idx, new_state)

            instance.opacity = 0.6
            Animation(opacity=1, duration=0.15).start(instance)
        return callback


class IoTApp(App):
    def build(self):
        return IoTDashboard()


if __name__ == "__main__":
    IoTApp().run()
