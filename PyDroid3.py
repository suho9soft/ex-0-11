from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.text import LabelBase
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# ✅ 한글폰트 등록 — fonts 폴더 내 실제 파일명과 일치해야 함
LabelBase.register(name="NotoSans", fn_regular="fonts/NotoSansKR-Regular.otf")

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

class IoTDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(10), **kwargs)
        self.font = {"font_name": "NotoSans"}

        # 날짜・시간
        self.date_label = Label(font_size=sp(18), size_hint_y=None, height=dp(30), **self.font)
        self.time_label = Label(font_size=sp(18), size_hint_y=None, height=dp(30), **self.font)
        self.add_widget(self.date_label); self.add_widget(self.time_label)

        # 센서 데이터 출력
        self.temp_label = Label(text="온도: -- °C", font_size=sp(16), size_hint_y=None, height=dp(30), **self.font)
        self.humi_label = Label(text="습도: -- %", font_size=sp(16), size_hint_y=None, height=dp(30), **self.font)
        self.pot_label = Label(text="가변저항: --", font_size=sp(16), size_hint_y=None, height=dp(30), **self.font)
        self.add_widget(self.temp_label); self.add_widget(self.humi_label); self.add_widget(self.pot_label)

        # 릴레이 상태
        self.relay_label = Label(text="릴레이: OFF", font_size=sp(16), size_hint_y=None, height=dp(30),
                                 color=(1,0,0,1), **self.font)
        self.add_widget(self.relay_label)

        # LED 버튼 배열
        self.led_grid = GridLayout(cols=2, spacing=dp(10), padding=dp(10), size_hint_y=None)
        self.led_grid.bind(minimum_height=self.led_grid.setter("height"))
        self.led_buttons = []; self.led_states = [False]*8
        for i in range(8):
            btn = Button(text=f"LED {i+1}", font_size=sp(16),
                         size_hint=(1,None), height=dp(50),
                         background_normal="", background_color=(0.7,0.7,0.7,1),
                         color=(0,0,0,1), **self.font)
            btn.bind(on_press=self.make_led_callback(i))
            self.led_grid.add_widget(btn); self.led_buttons.append(btn)
        self.add_widget(self.led_grid)

        # MQTT 설정
        self.relay=False
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()
        Clock.schedule_interval(self.update_time, 1)

    def update_time(self, dt):
        now = datetime.now()
        wed = ["월","화","수","목","금","토","일"][now.weekday()]
        self.date_label.text = now.strftime(f"%Y-%m-%d ({wed})")
        self.time_label.text = now.strftime("%H:%M:%S")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("arduino/input"); client.subscribe("arduino/output")
            for i in range(1,9):
                client.subscribe(f"arduino/led{i}")

    def on_message(self, client, userdata, msg):
        t, p = msg.topic, msg.payload.decode()
        if t=="arduino/input":
            try:
                d=json.loads(p)
                self.temp_label.text=f"온도: {d.get('temp',0):.1f} °C"
                self.humi_label.text=f"습도: {d.get('humi',0):.1f} %"
                self.pot_label.text=f"가변저항: {d.get('pot',0)}"
                self.relay=bool(d.get("relay",False)); self.update_relay()
            except: pass
        elif t=="arduino/output":
            self.relay = (p.strip().upper()=="ON"); self.update_relay()
        else:
            for i in range(8):
                if t==f"arduino/led{i+1}":
                    st=(p=="1"); self.led_states[i]=st
                    self.led_buttons[i].background_color = (0.2,1,0.2,1) if st else (0.7,0.7,0.7,1)

    def update_relay(self):
        self.relay_label.text=f"릴레이: {'ON' if self.relay else 'OFF'}"
        self.relay_label.color=(0,1,0,1) if self.relay else (1,0,0,1)

    def make_led_callback(self, i):
        def cb(inst):
            st = not self.led_states[i]; self.led_states[i]=st
            self.client.publish(f"arduino/led{i+1}", "1" if st else "0")
            inst.opacity=0.6
            Animation(opacity=1, duration=0.12).start(inst)
        return cb

class IoTApp(App):
    def build(self):
        return IoTDashboard()

if __name__=="__main__":
    IoTApp().run()
