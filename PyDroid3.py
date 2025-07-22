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

# Note20 Ultra 용 논리 해상도 설정 (1dp ≈ 4px)
Window.size = (dp(360), dp(760))

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

class IoTDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.relay = False
        self.led_states = [False]*8

        self.date_label = Label(text="", font_size=sp(18), size_hint_y=None, height=dp(30))
        self.time_label = Label(text="", font_size=sp(18), size_hint_y=None, height=dp(30))
        self.add_widget(self.date_label)
        self.add_widget(self.time_label)

        self.temp_label = Label(text="온도: -- °C", font_size=sp(16), size_hint_y=None, height=dp(28))
        self.humi_label = Label(text="습도: -- %", font_size=sp(16), size_hint_y=None, height=dp(28))
        self.pot_label = Label(text="조도: --", font_size=sp(16), size_hint_y=None, height=dp(28))
        self.add_widget(self.temp_label)
        self.add_widget(self.humi_label)
        self.add_widget(self.pot_label)

        self.relay_label = Label(text="릴레이: OFF", font_size=sp(16),
                                 size_hint_y=None, height=dp(28),
                                 color=(1,0,0,1))
        self.add_widget(self.relay_label)

        self.led_grid = GridLayout(
            cols=2, spacing=dp(8),
            size_hint_y=None,
            height=dp(400)
        )
        self.led_buttons = []
        for i in range(8):
            btn = Button(
                text=f"LED {i+1}",
                font_size=sp(16),
                size_hint_y=None,
                height=dp(50),
                background_color=(0.5,0.5,0.5,1),
                on_press=self.toggle_led(i)
            )
            self.led_buttons.append(btn)
            self.led_grid.add_widget(btn)
        self.add_widget(self.led_grid)

        Clock.schedule_interval(self.update_time, 1)
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def update_time(self, dt):
        now = datetime.now()
        wk = ["월","화","수","목","금","토","일"][now.weekday()]
        self.date_label.text = now.strftime(f"%Y-%m-%d ({wk})")
        self.time_label.text = now.strftime("%H:%M:%S")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("arduino/input")
            client.subscribe("arduino/output")
            for i in range(1,9):
                client.subscribe(f"arduino/led{i}")

    def on_message(self, client, userdata, msg):
        t = msg.topic; p = msg.payload.decode()
        if t=="arduino/input":
            try:
                data = json.loads(p)
                self.temp_label.text = f"온도: {data.get('temp',0.0):.1f} °C"
                self.humi_label.text = f"습도: {data.get('humi',0.0):.1f} %"
                self.pot_label.text = f"조도: {data.get('pot',0)}"
                self.relay = bool(data.get("relay",False))
                self.update_relay()
            except: pass
        elif t=="arduino/output":
            self.relay = (p.strip().upper()=="ON")
            self.update_relay()
        else:
            for i in range(8):
                if t==f"arduino/led{i+1}":
                    state = (p=="1")
                    self.led_states[i] = state
                    self.led_buttons[i].background_color = (0,1,0,1) if state else (0.5,0.5,0.5,1)

    def update_relay(self):
        self.relay_label.text = f"릴레이: {'ON' if self.relay else 'OFF'}"
        self.relay_label.color = (0,1,0,1) if self.relay else (1,0,0,1)

    def toggle_led(self, idx):
        def cb(instance):
            new = not self.led_states[idx]
            self.led_states[idx] = new
            self.client.publish(f"arduino/led{idx+1}", "1" if new else "0")
            self.led_buttons[idx].background_color = (0,1,0,1) if new else (0.5,0.5,0.5,1)
        return cb

class IoTApp(App):
    def build(self):
        return IoTDashboard()

if __name__=="__main__":
    IoTApp().run()
