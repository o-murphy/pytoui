#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

#define TextAnchor_CENTER 0

#define TextAnchor_TOP 1

#define TextAnchor_BOTTOM 2

#define TextAnchor_LEFT 4

#define TextAnchor_RIGHT 8

int32_t RegisterFont(const unsigned char *data, int len);

int32_t LoadFont(const char *path);

int32_t UnloadFont(int32_t handle);

int32_t GetDefaultFont(void);

int32_t GetFontCount(void);

int32_t GetFontIDs(int *buf, int max_count);

int CreateFrameBuffer(unsigned char *data, int width, int height);

void DestroyFrameBuffer(int handle);

void Fill(int32_t handle, uint32_t color);

void FillOver(int32_t handle, uint32_t color);

void SetPixel(int32_t handle, int32_t x, int32_t y, uint32_t color);

uint32_t GetPixel(int32_t handle, int32_t x, int32_t y);

void CSetPixel(int32_t handle, int32_t x, int32_t y, uint32_t color);

uint32_t CGetPixel(int32_t handle, int32_t x, int32_t y);

void Line(int32_t handle, int32_t x0, int32_t y0, int32_t x1, int32_t y1, uint32_t color);

void HLine(int32_t handle, int32_t x, int32_t y, int32_t w, uint32_t color);

void VLine(int32_t handle, int32_t x, int32_t y, int32_t h, uint32_t color);

void Rect(int32_t handle, int32_t x, int32_t y, int32_t w, int32_t h, uint32_t color);

void FillRect(int32_t handle, int32_t x, int32_t y, int32_t w, int32_t h, uint32_t color);

void FillRectOver(int32_t handle, int32_t x, int32_t y, int32_t w, int32_t h, uint32_t color);

void Circle(int32_t handle, int32_t cx, int32_t cy, int32_t r, uint32_t color);

void FillCircle(int32_t handle, int32_t cx, int32_t cy, int32_t r, uint32_t color);

void Ellipse(int32_t handle, int32_t cx, int32_t cy, int32_t rx, int32_t ry, uint32_t color);

void FillEllipse(int32_t handle, int32_t cx, int32_t cy, int32_t rx, int32_t ry, uint32_t color);

void EllipseArc(int32_t handle,
                int32_t cx,
                int32_t cy,
                int32_t rx,
                int32_t ry,
                double start_angle,
                double end_angle,
                uint32_t color);

void BlitRGBA(int32_t handle,
              const uint8_t *src_data,
              int32_t src_w,
              int32_t src_h,
              int32_t dst_x,
              int32_t dst_y,
              int32_t blend);

void Scroll(int32_t handle, int32_t dx, int32_t dy);

int32_t DrawText(int32_t handle,
                 int32_t font_handle,
                 float size,
                 const char *text,
                 int32_t x,
                 int32_t y,
                 uint32_t anchor,
                 uint32_t color);

int32_t MeasureText(int32_t font_handle, float size, const char *text);

int32_t GetTextMetrics(int32_t font_handle,
                       float size,
                       int32_t *ascent,
                       int32_t *descent,
                       int32_t *height);

int32_t GetTextHeight(int32_t font_handle, float size);
