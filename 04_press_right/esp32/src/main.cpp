// ============================================================
// CrashTech VLSI-2026 — Press Right (Challenge 4)
// ============================================================
// The FPGA runs a 10ms counter (0000-9999) on its 7-segment displays.
// Press KEY[0] to start, press again to stop.
// FPGA sends "NNNN\n" (4-digit ASCII + LF) over UART to this ESP32.
// Win condition: stopped value within 1000 ± 10 (= 10.00 seconds).
//
// Wiring:
//   FPGA GPIO[1]  (JP1 pin 2)  →  ESP32 GPIO17  (UART2 RX)
//   FPGA JP1 GND  (JP1 pin 12) →  ESP32 GND
//   OLED SDA → GPIO21,  OLED SCL → GPIO22
//   Buzzer   → GPIO19
// ============================================================

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "../../../../projects/common/esp32/pin_config.h"

// ---- OLED ----
Adafruit_SSD1306 oled(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
bool oledOk = false;

// ---- UART2 from FPGA ----
HardwareSerial FpgaSerial(2);

// ---- Incoming line buffer ----
String rxLine = "";

// ---- Helpers ----

#define BUZZER_CH 0   // LEDC channel for buzzer

void playVictory() {
    // Ascending fanfare: C5 → E5 → G5 → C6
    const int notes[]    = {523, 659, 784, 1047};
    const int durations[] = {120, 120, 120, 400};
    for (int i = 0; i < 4; i++) {
        ledcWriteTone(BUZZER_CH, notes[i]);
        delay(durations[i]);
        ledcWriteTone(BUZZER_CH, 0);
        delay(30);
    }
}

void playMiss() {
    // Descending low tones
    ledcWriteTone(BUZZER_CH, 300);
    delay(200);
    ledcWriteTone(BUZZER_CH, 180);
    delay(350);
    ledcWriteTone(BUZZER_CH, 0);
}

void showWaiting() {
    if (!oledOk) return;
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);

    oled.setTextSize(2);
    oled.setCursor(14, 4);
    oled.print("PRESS");
    oled.setCursor(14, 24);
    oled.print("RIGHT");

    oled.setTextSize(1);
    oled.setCursor(4, 50);
    oled.print("Press KEY[0] on FPGA");
    oled.display();
}

void showResult(int val, bool win, int distance) {
    if (!oledOk) return;

    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);

    // Large WIN / MISS heading
    oled.setTextSize(3);
    if (win) {
        oled.setCursor(20, 2);
        oled.print("WIN!");
    } else {
        oled.setCursor(14, 2);
        oled.print("MISS");
    }

    // Stopped value
    char buf[20];
    oled.setTextSize(1);
    snprintf(buf, sizeof(buf), "Stopped: %4d", val);
    oled.setCursor(0, 40);
    oled.print(buf);

    // Distance from target
    snprintf(buf, sizeof(buf), "Off by:  %4d", distance);
    oled.setCursor(0, 52);
    oled.print(buf);

    oled.display();
}

// ----------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    Serial.println("\n--- Press Right ESP32 ---");
    Serial.println("Target: 1000 counts (10.00 s), win zone ±10");

    // Buzzer — attach LEDC channel (v2 API: setup + attachPin)
    ledcSetup(BUZZER_CH, 1000, 8);
    ledcAttachPin(PIN_BUZZER, BUZZER_CH);
    ledcWriteTone(BUZZER_CH, 0);   // start silent

    // UART2: RX = GPIO17 (from FPGA GPIO[1]), TX = GPIO16 (unused here)
    FpgaSerial.begin(FPGA_BAUD, SERIAL_8N1, PIN_FPGA_RX, PIN_FPGA_TX);

    // OLED — give module time to power up before init
    delay(200);
    Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
    Wire.setTimeOut(500);   // prevent I2C from hanging indefinitely
    oledOk = oled.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR);
    Serial.printf("[OLED] begin() returned %s (addr=0x%02X)\n",
                  oledOk ? "true" : "false", OLED_I2C_ADDR);
    if (!oledOk) {
        // Try alternate address 0x3D
        oledOk = oled.begin(SSD1306_SWITCHCAPVCC, 0x3D);
        Serial.printf("[OLED] retry 0x3D returned %s\n",
                      oledOk ? "true" : "false");
    }
    if (!oledOk) {
        Serial.println("[!] OLED not found — continuing without display");
    } else {
        showWaiting();
    }
}

// ----------------------------------------------------------------
void loop() {
    while (FpgaSerial.available()) {
        char c = (char)FpgaSerial.read();

        if (c == '\n' || c == '\r') {
            if (rxLine.length() == 4) {
                int val      = rxLine.toInt();
                int distance = abs(val - 1000);
                bool win     = (distance <= 10);

                Serial.printf("Received: \"%s\" → %d  dist=%d  %s\n",
                              rxLine.c_str(), val, distance,
                              win ? "WIN!" : "MISS");

                showResult(val, win, distance);

                if (win) playVictory();
                else     playMiss();
            } else if (rxLine.length() > 0) {
                Serial.printf("[!] Bad frame len=%d: \"%s\"\n",
                              rxLine.length(), rxLine.c_str());
            }
            rxLine = "";

        } else if (rxLine.length() < 8) {
            rxLine += c;
        }
    }
}
