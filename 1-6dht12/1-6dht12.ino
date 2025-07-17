#include <WiFi.h>
#include "wifi_credentials.h"  // ssid, password 정의
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "DHT.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Fonts/FreeSans9pt7b.h>
#include <time.h>

// OLED 설정
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// 핀 설정
#define DHTPIN 15
#define DHTTYPE DHT11
#define POTPIN 35
#define RELAY_PIN 32

const int ledPins[8] = {2, 4, 5, 18, 19, 25, 26, 27};

DHT dht(DHTPIN, DHTTYPE);

// MQTT 설정
const char* mqtt_server = "broker.emqx.io";
WiFiClient espClient;
PubSubClient client(espClient);
StaticJsonDocument<256> doc_out;

unsigned long mqtt_t = 0;
const unsigned long mqtt_interval = 2000;

bool relayState = false;

// ===== WiFi 연결 =====
void setup_wifi() {
  Serial.print("🔌 WiFi 연결 중...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi 연결 완료: " + WiFi.localIP().toString());
}

// ===== MQTT 콜백 =====
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  payload[length] = '\0';
  String message = String((char*)payload);
  Serial.printf("📥 수신됨 (%s): %s\n", topic, message.c_str());

  if (String(topic) == "arduino/output") {
    if (message.equalsIgnoreCase("post 3200 on")) {
      digitalWrite(RELAY_PIN, HIGH);
      relayState = true;
      Serial.println("⚡ 수동 릴레이 ON");
    } else if (message.equalsIgnoreCase("post 3200 off")) {
      digitalWrite(RELAY_PIN, LOW);
      relayState = false;
      Serial.println("🛑 수동 릴레이 OFF");
    }
  }

  for (int i = 0; i < 8; i++) {
    String ledTopic = "arduino/led" + String(i + 1);
    if (String(topic) == ledTopic) {
      digitalWrite(ledPins[i], message == "1" ? HIGH : LOW);
      Serial.printf("💡 LED %d → %s\n", i + 1, message == "1" ? "ON" : "OFF");
    }
  }
}

// ===== MQTT 재연결 =====
void reconnect() {
  while (!client.connected()) {
    Serial.print("🔄 MQTT 연결 시도...");
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("성공!");
      client.subscribe("arduino/output");
      for (int i = 1; i <= 8; i++) {
        client.subscribe(("arduino/led" + String(i)).c_str());
      }
    } else {
      Serial.printf("실패(%d) → 5초 후 재시도\n", client.state());
      delay(5000);
    }
  }
}

// ===== 날짜 + 요일 (한줄로, 예: 2025-07-16/Wed) =====
String getDateDay() {
  struct tm t;
  if (!getLocalTime(&t)) return "--/---";

  const char* days[] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};

  char buf[16];
  strftime(buf, sizeof(buf), "%Y-%m-%d", &t);

  return String(buf) + "/" + days[t.tm_wday];
}

// ===== 시간 =====
String getTime() {
  struct tm t;
  if (!getLocalTime(&t)) return "--:--:--";

  char buf[9];
  strftime(buf, sizeof(buf), "%H:%M:%S", &t);

  return String(buf);
}

// ===== OLED 출력 =====
void showDisplay(float temp, float humi, int pot) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setFont(&FreeSans9pt7b);

  display.setCursor(0, 14);
  display.println(getDateDay());  // 날짜/요일

  display.setCursor(0, 30);
  display.println(getTime());  // 시간

  display.setCursor(0, 46);
  display.printf("%.1f°C / %.1f%%", temp, humi);  // 온도 / 습도

  display.setCursor(0, 62);
  display.printf("POT: %d  %s", pot, relayState ? "ON" : "OFF");  // 가변저항 + 릴레이 상태

  display.display();
}

// ===== 초기화 =====
void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  for (int i = 0; i < 8; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  setup_wifi();

  client.setServer(mqtt_server, 1883);
  client.setCallback(mqtt_callback);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("❌ OLED 초기화 실패!");
    while (true);
  }

  display.setTextColor(SSD1306_WHITE);
  display.setFont(&FreeSans9pt7b);

  configTime(9 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  while (time(nullptr) < 100000) delay(500);
  Serial.println("⏰ NTP 시간 동기화 완료");
}

// ===== 메인 루프 =====
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  if (millis() - mqtt_t > mqtt_interval) {
    mqtt_t = millis();

    float temp = dht.readTemperature();
    float humi = dht.readHumidity();
    int pot = analogRead(POTPIN);

    if (isnan(temp) || isnan(humi)) {
      Serial.println("❗ 센서 오류");
      return;
    }

    if (pot >= 3200 && !relayState) {
      digitalWrite(RELAY_PIN, HIGH);
      relayState = true;
      Serial.println("🟢 POT >= 3200 → 릴레이 ON");
    } else if (pot < 3200 && relayState) {
      digitalWrite(RELAY_PIN, LOW);
      relayState = false;
      Serial.println("🔴 POT < 3200 → 릴레이 OFF");
    }

    doc_out["temp"] = temp;
    doc_out["humi"] = humi;
    doc_out["pot"] = pot;
    doc_out["relay"] = relayState;

    String js;
    serializeJson(doc_out, js);
    client.publish("arduino/input", js.c_str());

    showDisplay(temp, humi, pot);

    Serial.printf("📤 MQTT 전송: %s\n", js.c_str());
  }
}
