#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

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

void Line(int32_t handle,
          int32_t x0,
          int32_t y0,
          int32_t x1,
          int32_t y1,
          uint32_t color,
          uint8_t blend);

void LineStroke(int32_t handle,
                float x0,
                float y0,
                float x1,
                float y1,
                float width,
                uint8_t cap,
                uint8_t join,
                uint32_t color,
                uint8_t blend);

void RectStroke(int32_t handle,
                float x,
                float y,
                float w,
                float h,
                float width,
                uint8_t join,
                uint32_t color,
                uint8_t blend);

void StrokeRoundedRect(int32_t handle,
                       float x,
                       float y,
                       float w,
                       float h,
                       float radius,
                       float bw,
                       uint8_t join,
                       uint32_t color,
                       uint8_t blend);

void EllipseStroke(int32_t handle,
                   float cx,
                   float cy,
                   float rx,
                   float ry,
                   float width,
                   uint32_t color,
                   uint8_t blend);

void HLine(int32_t handle, int32_t x, int32_t y, int32_t w, uint32_t color, uint8_t blend);

void VLine(int32_t handle, int32_t x, int32_t y, int32_t h, uint32_t color, uint8_t blend);

void Rect(int32_t handle,
          int32_t x,
          int32_t y,
          int32_t w,
          int32_t h,
          uint32_t color,
          uint8_t blend);

void FillRect(int32_t handle, float x, float y, float w, float h, uint32_t color, uint8_t blend);

void RoundedRect(int32_t handle,
                 int32_t x,
                 int32_t y,
                 int32_t w,
                 int32_t h,
                 int32_t radius,
                 uint32_t color,
                 uint8_t blend);

void FillRoundedRect(int32_t handle,
                     float x,
                     float y,
                     float w,
                     float h,
                     float radius,
                     uint32_t color,
                     uint8_t blend);

void Circle(int32_t handle, int32_t cx, int32_t cy, int32_t r, uint32_t color, uint8_t blend);

void FillCircle(int32_t handle, float cx, float cy, float r, uint32_t color, uint8_t blend);

void Ellipse(int32_t handle,
             int32_t cx,
             int32_t cy,
             int32_t rx,
             int32_t ry,
             uint32_t color,
             uint8_t blend);

void FillEllipse(int32_t handle,
                 float cx,
                 float cy,
                 float rx,
                 float ry,
                 uint32_t color,
                 uint8_t blend);

void EllipseArc(int32_t handle,
                int32_t cx,
                int32_t cy,
                int32_t rx,
                int32_t ry,
                double start_angle,
                double end_angle,
                uint32_t color,
                uint8_t blend);

void BlitRGBA(int32_t handle,
              const uint8_t *src_data,
              int32_t src_w,
              int32_t src_h,
              int32_t dst_x,
              int32_t dst_y,
              int32_t blend);

void BlitRGBAScaled(int32_t handle,
                    const uint8_t *src_data,
                    int32_t src_w,
                    int32_t src_h,
                    int32_t dst_x,
                    int32_t dst_y,
                    int32_t dst_w,
                    int32_t dst_h,
                    int32_t blend);

void Scroll(int32_t handle, int32_t dx, int32_t dy);

void SetAntiAlias(int32_t handle, int32_t enabled);

int32_t GetAntiAlias(int32_t handle);

void SetCTM(int32_t handle, float a, float b, float c, float d, float tx, float ty);

void ApplyYUV422Compensation(int32_t handle, int32_t x, int32_t y, int32_t w, int32_t h);

int32_t DrawText(int32_t handle,
                 int32_t font_handle,
                 float size,
                 const char *text,
                 float x,
                 float y,
                 uint32_t anchor,
                 uint32_t color,
                 float spacing);

int32_t MeasureText(int32_t font_handle, float size, const char *text, float spacing);

int32_t GetTextMetrics(int32_t font_handle,
                       float size,
                       int32_t *ascent,
                       int32_t *descent,
                       int32_t *height);

int32_t GetTextHeight(int32_t font_handle, float size);

void GStatePush(int32_t handle);

void GStatePop(int32_t handle);

int32_t CreateOwnedFB(int32_t width, int32_t height);

void ClearFB(int32_t handle);

void CompositeFB(int32_t dst_handle, int32_t src_handle, int32_t x, int32_t y, float alpha);

void CompositeFBRounded(int32_t dst_handle,
                        int32_t src_handle,
                        int32_t x,
                        int32_t y,
                        float alpha,
                        float radius);

int32_t CreateTransform(float a, float b, float c, float d, float tx, float ty);

int32_t DestroyTransform(int32_t handle);

int32_t TransformRotation(float radians);

int32_t TransformScale(float sx, float sy);

int32_t TransformTranslation(float tx, float ty);

int32_t TransformConcat(int32_t handle_a, int32_t handle_b);

int32_t TransformInvert(int32_t handle);

int32_t TransformGet(int32_t handle, float *a, float *b, float *c, float *d, float *tx, float *ty);

int32_t CreatePath(void);

int32_t DestroyPath(int32_t handle);

void PathMoveTo(int32_t handle, float x, float y);

void PathLineTo(int32_t handle, float x, float y);

void PathAddCurve(int32_t handle, float cp1x, float cp1y, float cp2x, float cp2y, float x, float y);

void PathAddQuadCurve(int32_t handle, float cpx, float cpy, float x, float y);

void PathAddArc(int32_t handle,
                float cx,
                float cy,
                float r,
                float start,
                float end,
                int32_t clockwise);

void PathClose(int32_t handle);

void PathAppend(int32_t dst, int32_t src);

int32_t PathRect(float x, float y, float w, float h);

int32_t PathOval(float x, float y, float w, float h);

int32_t PathRoundedRect(float x, float y, float w, float h, float r);

void PathSetLineWidth(int32_t handle, float width);

void PathSetLineCap(int32_t handle, uint8_t cap);

void PathSetLineJoin(int32_t handle, uint8_t join);

void PathSetLineDash(int32_t handle, const float *intervals, int32_t count, float phase);

void PathFill(int32_t fb_handle, int32_t path_handle, uint32_t color, uint8_t blend);

void PathSetEoFillRule(int32_t handle, int32_t value);

void PathStroke(int32_t fb_handle, int32_t path_handle, uint32_t color, uint8_t blend);

int32_t PathHitTest(int32_t path_handle, float x, float y);

int32_t PathGetBounds(int32_t path_handle, float *x_out, float *y_out, float *w_out, float *h_out);

void PathAddClip(int32_t fb_handle, int32_t path_handle);

void DrawCheckerBoard(int32_t fb_handle, int32_t size);

int32_t DrawStringCoreGraphics(int32_t fb_handle,
                               int32_t font_handle,
                               const char *text,
                               float x,
                               float y,
                               float w,
                               float h,
                               float size,
                               uint32_t color,
                               uint32_t alignment,
                               uint32_t line_break_mode);

int32_t MeasureStringCoreGraphics(int32_t font_handle,
                                  const char *text,
                                  float max_width,
                                  float size,
                                  uint32_t line_break_mode,
                                  float *out_width,
                                  float *out_height);
