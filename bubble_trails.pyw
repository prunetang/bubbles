"""Windows 11 transparent bubble trails. Install: py -m pip install PySide6
Run with pythonw (or double-click this .pyw). Exit: Ctrl+Alt+Shift+Backspace.
"""
import sys
import math
import random as R
import time
import ctypes
from ctypes import wintypes


def main():
    if sys.platform != 'win32':
        raise SystemExit('This overlay requires Windows 10/11.')
    try:
        from PySide6.QtCore import Qt, QTimer, QRectF, QAbstractNativeEventFilter
        from PySide6.QtGui import QColor, QPainter, QPen, QFont
        from PySide6.QtWidgets import QApplication, QWidget
    except ImportError:
        ctypes.windll.user32.MessageBoxW(None,
            'Install the dependency first:\n\npy -m pip install PySide6',
            'Bubble Trails', 0x10)
        return 1

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = wintypes.BOOL
    hotkey_id = 0xB017
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    if not user32.RegisterHotKey(None, hotkey_id, 0x4000 | 1 | 2 | 4, 0x08):
        user32.MessageBoxW(None,
            'The exit shortcut is unavailable. Close any other Bubble Trails instance and try again.',
            'Bubble Trails', 0x10)
        return 1

    class ExitFilter(QAbstractNativeEventFilter):
        def nativeEventFilter(self, event_type, message):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == hotkey_id:
                app.quit()
                return True, 0
            return False, 0

    exit_filter = ExitFilter()
    app.installNativeEventFilter(exit_filter)

    class Trail:
        def __init__(self, width, height):
            self.w, self.h = width, height
            self.x, self.y = R.uniform(0, width), R.uniform(0, height)
            self.angle = R.uniform(0, math.tau)
            self.speed = 80
            self.hue = R.random()
            self.emission = 0
            self.change()

        def change(self):
            self.target_speed = R.uniform(650, 1900) if R.random() < .38 else R.uniform(35, 220)
            self.turn = R.uniform(-3.8, 3.8)
            self.angle += R.uniform(-2.5, 2.5)
            self.remaining = R.uniform(.12, .48) if self.target_speed > 600 else R.uniform(.5, 2.5)
            self.response = R.uniform(3, 16)

        def step(self, dt, bubbles):
            self.remaining -= dt
            if self.remaining <= 0:
                self.change()
            self.speed += (self.target_speed - self.speed) * (1 - math.exp(-self.response * dt))
            self.angle += self.turn * dt
            old_x, old_y = self.x, self.y
            self.x += math.cos(self.angle) * self.speed * dt
            self.y += math.sin(self.angle) * self.speed * dt
            if self.x < 0 or self.x > self.w:
                self.x = max(0, min(self.w, self.x))
                self.angle = math.pi - self.angle
            if self.y < 0 or self.y > self.h:
                self.y = max(0, min(self.h, self.y))
                self.angle = -self.angle
            self.hue = (self.hue + dt * .09) % 1
            distance = math.hypot(self.x-old_x, self.y-old_y)
            count = max(1, math.ceil(distance / 5))
            for i in range(count):
                t = (i + R.random()) / count
                numbered = R.random() < .006
                radius = R.uniform(8, 11) if numbered else R.uniform(2, 6.5)
                bubbles.append([old_x+(self.x-old_x)*t+R.gauss(0, 4),
                    old_y+(self.y-old_y)*t+R.gauss(0, 4), radius,
                    (self.hue+R.uniform(-.08, .08)) % 1, 0,
                    R.uniform(.65, 1.15) if numbered else R.uniform(.25, .72),
                    R.uniform(-10, 10), R.uniform(-14, 5),
                    str(R.randint(1, 24)) if numbered else ''])

    class Overlay(QWidget):
        def __init__(self, screen):
            super().__init__()
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool |
                Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.setGeometry(screen.geometry())
            self.bubbles = []
            self.trails = [Trail(self.width(), self.height()) for _ in range(4)]
            self.last = time.perf_counter()
            self.timer = QTimer(self)
            self.timer.setTimerType(Qt.TimerType.PreciseTimer)
            self.timer.timeout.connect(self.tick)
            self.timer.start(16)
            self.show()

        def tick(self):
            now = time.perf_counter()
            dt = min(now-self.last, .05)
            self.last = now
            live = []
            for b in self.bubbles:
                b[4] += dt
                if b[4] < b[5]:
                    b[0] += b[6]*dt
                    b[1] += b[7]*dt
                    live.append(b)
            self.bubbles = live
            for trail in self.trails:
                trail.step(dt, self.bubbles)
            self.update()

        def paintEvent(self, event):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Explicitly clear the alpha surface every frame, leaving no trails behind.
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            for x, y, radius, hue, age, life, vx, vy, number in self.bubbles:
                fade = min(1, age/.035) * (1-age/life)**.85
                r = radius * (1 + .16*age/life)
                skin = QColor.fromHsvF(hue, .65, 1, .075*fade)
                rim = QColor.fromHsvF(hue, .42, 1, .58*fade)
                p.setBrush(skin)
                p.setPen(QPen(rim, .9))
                p.drawEllipse(QRectF(x-r, y-r, 2*r, 2*r))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, int(125*fade)), 1))
                p.drawArc(QRectF(x-r*.72, y-r*.72, r*1.44, r*1.44), 45*16, 75*16)
                if number:
                    font = QFont('Segoe UI')
                    font.setPixelSize(10)
                    font.setBold(True)
                    p.setFont(font)
                    box = QRectF(x-r, y-r, 2*r, 2*r)
                    p.setPen(QColor(0, 0, 0, int(140*fade)))
                    p.drawText(box.translated(.7, .7), Qt.AlignmentFlag.AlignCenter, number)
                    p.setPen(QColor(255, 255, 255, int(230*fade)))
                    p.drawText(box, Qt.AlignmentFlag.AlignCenter, number)
            p.end()

    windows = []
    def rebuild(*args):
        for window in windows:
            window.timer.stop()
            window.close()
        windows.clear()
        windows.extend(Overlay(screen) for screen in app.screens())

    # Keep overlays on each monitor, including mixed DPI layouts.
    app.setQuitOnLastWindowClosed(False)
    app.screenAdded.connect(rebuild)
    app.screenRemoved.connect(rebuild)
    for screen in app.screens():
        screen.geometryChanged.connect(rebuild)
    try:
        rebuild()
        return app.exec()
    finally:
        user32.UnregisterHotKey(None, hotkey_id)


if __name__ == '__main__':
    sys.exit(main())
