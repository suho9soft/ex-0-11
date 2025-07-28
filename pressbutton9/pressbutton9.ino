#include <Wire.h>
#include <U8g2lib.h>

#define NUM_BUTTONS 4
#define NUM_LEDS 4

int button_pins[NUM_BUTTONS] = {15, 14, 13, 12};  // 버튼 핀
int led_pins[NUM_LEDS] = {18, 19, 20, 21};        // LED 핀

bool led_states[NUM_LEDS] = {false, false, false, false};
unsigned long button_press_time[NUM_BUTTONS] = {0};
bool ignore_button[NUM_BUTTONS] = {false, false, false, false};  // 리셋 후 무시 플래그

// OLED 디스플레이 초기화
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE, 1, 0);

// 숫자에 대응하는 한글 라벨: 가, 나, 다, 라
const char* labels[NUM_BUTTONS] = {"가", "나", "다", "라"};

void setup() {
  for (int i = 0; i < NUM_BUTTONS; i++) {
    pinMode(button_pins[i], INPUT_PULLUP);
    pinMode(led_pins[i], OUTPUT);
    digitalWrite(led_pins[i], LOW);
  }

  display.begin();
  display.enableUTF8Print();  // UTF-8 사용
  display.setFont(u8g2_font_unifont_t_korean2);  // 한글 폰트
}

void toggle_led(int index) {
  led_states[index] = !led_states[index];
  digitalWrite(led_pins[index], led_states[index] ? HIGH : LOW);
}

void reset_leds() {
  for (int i = 0; i < NUM_LEDS; i++) {
    led_states[i] = false;
    digitalWrite(led_pins[i], LOW);
  }
}

void loop() {
  display.clearBuffer();

  for (int i = 0; i < NUM_BUTTONS; i++) {
    int y = 12 + i * 16;
    int state = digitalRead(button_pins[i]);

    if (state == LOW) {
      if (!ignore_button[i]) {
        if (button_press_time[i] == 0) {
          button_press_time[i] = millis();
        } else if (millis() - button_press_time[i] > 2000) {
          reset_leds();
          display.setCursor(0, y);
          display.print(i + 1);
          display.print(labels[i]);
          display.print(": ALL OFF (전체 멈춰)");
          button_press_time[i] = 0;
          ignore_button[i] = true;  // 이 버튼은 뗄 때까지 무시
          continue;
        }
      }
    } else {
      // 버튼이 떨어졌을 때 무시 해제
      if (ignore_button[i]) {
        ignore_button[i] = false;
      } else if (button_press_time[i] > 0 && millis() - button_press_time[i] <= 2000) {
        toggle_led(i);
      }
      button_press_time[i] = 0;
    }

    // OLED 상태 출력 (RUN/OFF + 한글)
    display.setCursor(0, y);
    display.print(i + 1);
    display.print(labels[i]);
    display.print(" > ");
    if (led_states[i]) {
      display.print("RUN (하자)");
    } else {
      display.print("OFF (멈춰)");
    }
  }

  display.sendBuffer();
  delay(100);
}
