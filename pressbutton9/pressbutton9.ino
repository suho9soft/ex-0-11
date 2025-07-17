#include <Wire.h>
#include <U8g2lib.h>

#define NUM_BUTTONS 4
#define NUM_LEDS 4

int button_pins[NUM_BUTTONS] = {15, 14, 13, 12};      // 버튼 핀 배열
int led_pins[NUM_LEDS] = {18, 19, 20, 21};            // LED 핀 배열

bool led_states[NUM_LEDS] = {false, false, false, false};     // LED 상태 배열
unsigned long button_press_time[NUM_BUTTONS] = {0};           // 버튼 누른 시간 기록

// U8g2 객체 생성 (I2C, Pico W 기준: SDA=GP0, SCL=GP1)
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE, 1, 0);  // SCL=1, SDA=0

void setup() {
  // 버튼, LED 핀 설정
  for (int i = 0; i < NUM_BUTTONS; i++) {
    pinMode(button_pins[i], INPUT_PULLUP);
    pinMode(led_pins[i], OUTPUT);
    digitalWrite(led_pins[i], LOW);
  }

  // OLED 초기화
  display.begin();
  display.enableUTF8Print();  // 한글 출력 허용
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
  display.clearBuffer();  // 화면 초기화
  display.setFont(u8g2_font_unifont_t_korean2);  // 한글+ASCII 폰트

  // 상단 출력
  display.setCursor(0, 12);
  display.print("한국-독립 결의대");

  int y_base = 30;

  for (int i = 0; i < NUM_BUTTONS; i++) {
    int y = y_base + i * 10;
    int state = digitalRead(button_pins[i]);

    // 버튼 누름 처리
    if (state == LOW) {
      if (button_press_time[i] == 0) {
        button_press_time[i] = millis();  // 처음 눌린 시간 기록
      } else if (millis() - button_press_time[i] > 2000) {
        reset_leds();  // 2초 이상 누르면 전체 끄기
        display.setCursor(0, y);
        display.print("#");
        display.print(i + 1);
        display.print(": 전체끄기");
        button_press_time[i] = 0;
      }
    } else {
      if (button_press_time[i] > 0 && millis() - button_press_time[i] <= 2000) {
        toggle_led(i);  // 짧게 눌렀으면 해당 LED 토글
        button_press_time[i] = 0;
      }
    }

    // OLED 상태 출력
    display.setCursor(0, y);
    display.print("#");
    display.print(i + 1);
    display.print(": ");

    if (led_states[i]) {
      display.print("[OFF] 꺼짐");  // LED ON 상태: 꺼짐 표시
    } else {
      display.print("[ON ] 켜짐");  // LED OFF 상태: 켜짐 표시
    }
  }

  display.sendBuffer();  // OLED에 전송
  delay(100);
}
