from __future__ import annotations

from typing import Any, Protocol

from pytoui._platform import IS_PYTHONISTA
from pytoui.ui._constants import ALIGN_CENTER, LB_WORD_WRAP
from pytoui.ui._draw import draw_string, measure_string
from pytoui.ui._internals import _final_
from pytoui.ui._view import View

__all__ = ("WebView", "_WebView", "_WebViewDelegate")


class _WebViewDelegate(Protocol):
    def webview_should_start_load(self, webview: WebView, url, nav_type) -> bool:
        return True

    def webview_did_start_load(self, webview: WebView): ...
    def webview_did_finish_load(self, webview: WebView): ...
    def webview_did_fail_load(self, webview: WebView, error_code, error_msg): ...


@_final_
class _WebView(View):
    def __init__(self, *args, **kwargs):
        self.background_color = "black"

        self._delegate: _WebViewDelegate | None = None
        self._scales_page_to_fit: bool = True

        self._url: str | None = None
        super().__init__(*args, **kwargs)

    @property
    def delegate(self) -> _WebViewDelegate | None:
        return self._delegate

    @delegate.setter
    def delegate(self, value: _WebViewDelegate | None):
        self._delegate = value

    @property
    def scales_page_to_fit(self) -> bool:
        return self._scales_page_to_fit

    @scales_page_to_fit.setter
    def scales_page_to_fit(self, value: bool):
        self._scales_page_to_fit = bool(value)

    def load_url(self, url: str) -> None:
        self._url = url
        if self._url:
            import webbrowser

            webbrowser.open(url, new=1)

    def load_html(self, html: str, base_url: str | None = None) -> None:
        pass

    def evaluate_javascript(self, script: str) -> Any:
        pass

    eval_js = evaluate_javascript

    def go_back(self) -> None:
        pass

    def go_forward(self) -> None:
        pass

    def reload(self) -> None:
        if self._url:
            import webbrowser

            webbrowser.open(self._url, new=0)

    def stop(self) -> None:
        self._url = None

    def draw(self):
        # Draw text
        x, y, w, h = self.frame

        try:
            string = "Not yet supported\nin pytoui for desktop"
            font = ("<system-bold>", 17)
            url_font = ("<system>", 15)
            alignment = ALIGN_CENTER
            lb = LB_WORD_WRAP
            _, sh = measure_string(
                string,
                max_width=0,
                font=font,
                alignment=alignment,
                line_break_mode=lb,
            )
            draw_string(
                string,
                rect=(x, y + h / 2 - sh, w, h),
                font=font,
                color="orange",
                alignment=alignment,
                line_break_mode=lb,
            )
            if self._url:
                draw_string(
                    f"Url is opened in deafault browser\n{self._url}",
                    rect=(x, y + h / 2, w, h),
                    font=url_font,
                    color="white",
                    alignment=alignment,
                    line_break_mode=lb,
                )
        except Exception:
            pass  # Silently fail if drawing fails


if not IS_PYTHONISTA:
    WebView = _WebView
else:
    import ui

    WebView = ui.WebView  # type: ignore[misc,assignment]
