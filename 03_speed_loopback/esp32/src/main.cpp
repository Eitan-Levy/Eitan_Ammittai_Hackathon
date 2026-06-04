// ============================================================
// CrashTech VLSI-2026 — Speed Loopback  OPTIMIZED  (Challenge 3)
// ============================================================
// FPGA sends: 4-byte header (N LE) + N random bytes at 1 Mbaud
// ESP32 does: receive all bytes, sum & 0xFF, send 1 byte back
// Target time: ~100 ms for N=10,000 bytes
//
// Key optimizations vs 9600-baud baseline (~10,400 ms):
//   1. 1,000,000 baud  (50 MHz / 1_000_000 = 50 exactly, zero clock error)
//   2. RX buffer 16 KB so all 10,000 bytes can be held without overflow
//   3. readBytes() bulk reads in 256-byte chunks — no per-byte polling
//   4. OLED updated only at start and end — zero blocking during transfer
//
// Wiring (Arduino header, male-male jumpers):
//   FPGA ARDUINO_IO[0]  (TX from baseline → NOT USED, this is FPGA RX)
//   FPGA ARDUINO_IO[1]  → ESP32 GPIO17  (UART2 RX on ESP32)
//   FPGA ARDUINO_IO[0]  ← ESP32 GPIO16  (UART2 TX on ESP32 → FPGA RX)
//   FPGA GND pin        → ESP32 GND
//
// Wait — check base top module:
//   ARDUINO_IO[0] = FPGA RX from ESP32   → wire to ESP32 GPIO16 (TX)
//   ARDUINO_IO[1] = FPGA TX to ESP32     → wire to ESP32 GPIO17 (RX)
// ============================================================

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "../../../../projects/common/esp32/pin_config.h"

// Must match FPGA uart_tx/uart_rx BAUD parameter (50 MHz / 1_000_000 = 50 exact)
#define FAST_BAUD  1000000UL

// OLED
Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
bool oledOk = false;

// UART2 (RX = GPIO17 ← FPGA ARDUINO_IO[1], TX = GPIO16 → FPGA ARDUINO_IO[0])
HardwareSerial FpgaSerial(2);

// ---- OLED helper ----
void oledShow(const char* l1, const char* l2 = nullptr, const char* l3 = nullptr) {
    if (!oledOk) return;
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("Speed Loopback");
    display.drawFastHLine(0, 9, 128, SSD1306_WHITE);
    if (l1) { display.setCursor(0, 14); display.println(l1); }
    if (l2) { display.setCursor(0, 28); display.println(l2); }
    if (l3) { display.setCursor(0, 42); display.println(l3); }
    display.display();
}

void setup() {
    Serial.begin(115200);
    Serial.printf("\n--- Speed Loopback OPTIMIZED @ %lu baud ---\n", FAST_BAUD);

    Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
    oledOk = display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR);

    // CRITICAL: enlarge RX buffer BEFORE begin() so all 10,000 bytes fit
    // Default ESP32 UART buffer = 256 bytes; at 1 Mbaud that fills in 2.56 ms
    FpgaSerial.setRxBufferSize(16384);
    FpgaSerial.begin(FAST_BAUD, SERIAL_8N1, PIN_FPGA_RX, PIN_FPGA_TX);
    FpgaSerial.setTimeout(500);   // 500 ms read timeout — plenty for 100 ms transfer

    oledShow("Ready", "Waiting for FPGA", "Press KEY[0]");
}

void loop() {
    // ---- Wait for 4-byte header (N, little-endian) ----
    while (FpgaSerial.available() < 4) { /* spin — no delay, keep latency minimal */ }

    uint32_t N = 0;
    N |= (uint32_t)FpgaSerial.read();
    N |= (uint32_t)FpgaSerial.read() << 8;
    N |= (uint32_t)FpgaSerial.read() << 16;
    N |= (uint32_t)FpgaSerial.read() << 24;

    Serial.printf("Header: N=%u, starting receive...\n", N);

    // Kick off OLED update BEFORE the tight receive loop (non-blocking after display())
    char hdrBuf[32];
    snprintf(hdrBuf, sizeof(hdrBuf), "N=%u @ 1Mbaud", N);
    oledShow("Receiving...", hdrBuf);

    // ---- Bulk receive + accumulate sum ----
    uint8_t  chunk[256];
    uint32_t sum       = 0;
    uint32_t remaining = N;
    unsigned long t0   = millis();

    while (remaining > 0) {
        size_t want = (remaining < sizeof(chunk)) ? (size_t)remaining : sizeof(chunk);
        size_t got  = FpgaSerial.readBytes(chunk, want);

        // Tight sum loop — compiler will auto-vectorize with -O2
        for (size_t i = 0; i < got; i++) {
            sum += chunk[i];
        }

        remaining -= got;

        if (got == 0) {
            // Timeout guard — shouldn't happen at 1 Mbaud with 500 ms timeout
            Serial.printf("[!] readBytes timeout, remaining=%u\n", remaining);
            break;
        }
    }

    unsigned long elapsed = millis() - t0;

    // ---- Send checksum ----
    uint8_t checksum = (uint8_t)(sum & 0xFF);
    FpgaSerial.write(checksum);
    FpgaSerial.flush();

    Serial.printf("Done! elapsed=%lu ms | sum=0x%08X | checksum=0x%02X\n",
                  elapsed, sum, checksum);

    // ---- OLED result ----
    char l2[24], l3[24];
    snprintf(l2, sizeof(l2), "Time:  %lu ms", elapsed);
    snprintf(l3, sizeof(l3), "Chk: 0x%02X", checksum);
    oledShow("DONE!", l2, l3);

    // Small gap before accepting next run (FPGA shows result on 7-seg)
    delay(2000);
}
