#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>

#define TFT_CS     10
#define TFT_DC      9
#define TFT_RST     8

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

#define TFT_WIDTH 128
#define TFT_HEIGHT 160

void setup() {
  Serial.begin(250000); // Baud rate seguro (cambiar el numero de ser necesario)
  tft.initR(INITR_BLACKTAB);
  tft.fillScreen(ST77XX_BLACK);
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    if (cmd == "START") {
      uint16_t color;
      for (int y = 0; y < TFT_HEIGHT; y++) {
        for (int x = 0; x < TFT_WIDTH; x++) {
          while (Serial.available() < 2); // Esperar 2 bytes
          uint8_t hi = Serial.read();
          uint8_t lo = Serial.read();
          color = (hi << 8) | lo;
          tft.drawPixel(x, y, color);
        }
      }
      // Esperar comando END (solo para sincronizar)
      while (Serial.available() > 0) {
        Serial.read();
      }
    }
  }
}
