#include <Wire.h>
#include <U8g2lib.h>

#define NUM_BUTTONS 4
#define NUM_LEDS 4

int button_pins[NUM_BUTTONS] = {15, 14, 13, 12};
int led_pins[NUM_LEDS] = {18, 19, 20, 21};

bool led_states[NUM_LEDS] = {false, false, false, false};
unsigned long button_press_time[NUM_BUTTONS] = {0};

U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE, 1, 0);

void setup() {
  for (int i = 0; i < NUM_BUTTONS; i++) {
    pinMode(button_pins[i], INPUT_PULLUP);
    pinMode(led_pins[i], OUTPUT);
    digitalWrite(led_pins[i], LOW);
  }

  display.begin();
  display.enableUTF8Print();
  display.setFont(u8g2_font_unifont_t_korean2);
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
    int y = 12 + i * 16;  // 16픽셀 줄 간격

    int state = digitalRead(button_pins[i]);

    if (state == LOW) {
      if (button_press_time[i] == 0) {
        button_press_time[i] = millis();
      } else if (millis() - button_press_time[i] > 2000) {
        reset_leds();
        display.setCursor(0, y);
        display.print("#");
        display.print(i + 1);
        display.print(": 전체끄기");
        button_press_time[i] = 0;
        continue;
      }
    } else {
      if (button_press_time[i] > 0 && millis() - button_press_time[i] <= 2000) {
        toggle_led(i);
        button_press_time[i] = 0;
      }
    }

    display.setCursor(0, y);
    display.print("#");
    display.print(i + 1);
    display.print(": ");

    if (led_states[i]) {
      display.print("ON (켜짐)");
    } else {
      display.print("OFF (꺼짐)");
    }
  }

  display.sendBuffer();
  delay(100);
}
