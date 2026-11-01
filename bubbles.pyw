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
        from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath
        from PySide6.QtWidgets import QApplication, QWidget
    except ImportError:
        ctypes.windll.user32.MessageBoxW(None,
            'Install the dependency first:\n\npy -m pip install PySide6',
            'Bubble Trails', 0x10)
        return 1

    # Native Windows APIs register a global shortcut without taking keyboard focus.
    # Explicit ctypes signatures keep window handles safe on 64-bit Python.
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = wintypes.BOOL
    # Shortcut: MOD_NOREPEAT | ALT | CONTROL | SHIFT, with virtual key 0x08 (Backspace).
    hotkey_id = 0xB017
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    if not user32.RegisterHotKey(None, hotkey_id, 0x4000 | 1 | 2 | 4, 0x08):
        user32.MessageBoxW(None,
            'The exit shortcut is unavailable. Close any other Bubble Trails instance and try again.',
            'Bubble Trails', 0x10)
        return 1

    # Qt forwards native Windows messages here, including WM_HOTKEY (0x0312).
    class ExitFilter(QAbstractNativeEventFilter):
        def nativeEventFilter(self, event_type, message):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == hotkey_id:
                app.quit()
                return True, 0
            return False, 0

    exit_filter = ExitFilter()
    app.installNativeEventFilter(exit_filter)

    # One invisible moving fingertip. Several independent fingertips create the trails.
    # Positions are Qt logical pixels; speeds are logical pixels per second.
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
            # CUSTOMIZE MOTION: fast/slow speeds, fast-move probability (.38),
            # turn rate (radians/second), segment duration, and smoothing response.
            self.target_speed = R.uniform(650, 1900) if R.random() < .38 else R.uniform(35, 220)
            self.turn = R.uniform(-3.8, 3.8)
            self.angle += R.uniform(-2.5, 2.5)
            self.remaining = R.uniform(.12, .48) if self.target_speed > 600 else R.uniform(.5, 2.5)
            self.response = R.uniform(3, 16)

        def step(self, dt, bubbles):
            self.remaining -= dt
            if self.remaining <= 0:
                self.change()
            # Exponential easing blends speeds smoothly, independently of frame rate.
            self.speed += (self.target_speed - self.speed) * (1 - math.exp(-self.response * dt))
            self.angle += self.turn * dt
            old_x, old_y = self.x, self.y
            self.x += math.cos(self.angle) * self.speed * dt
            self.y += math.sin(self.angle) * self.speed * dt
            # Reflect off monitor edges instead of leaving the overlay.
            if self.x < 0 or self.x > self.w:
                self.x = max(0, min(self.w, self.x))
                self.angle = math.pi - self.angle
            if self.y < 0 or self.y > self.h:
                self.y = max(0, min(self.h, self.y))
                self.angle = -self.angle
            # CUSTOMIZE COLOR: .09 controls hue cycling speed; hue wraps at 1.0.
            self.hue = (self.hue + dt * .09) % 1
            distance = math.hypot(self.x-old_x, self.y-old_y)
            # CUSTOMIZE DENSITY: smaller spacing (5) makes a denser foam trail.
            # Interpolating emissions keeps fast movements from becoming dotted lines.
            count = max(1, math.ceil(distance / 5))
            for i in range(count):
                t = (i + R.random()) / count
                # CUSTOMIZE BUBBLES: probability per bubble, radius, lifetime,
                # drift velocity, and the inclusive random number range (1 through 24).
                numbered = R.random() < .006
                radius = R.uniform(12, 14) if numbered else R.uniform(2, 6.5)
                # Bubble record indexes used by tick():
                # 0=x, 1=y, 2=radius, 3=hue, 4=age, 5=lifetime,
                # 6=horizontal drift, 7=vertical drift, 8=number text (or empty).
                bubbles.append([old_x+(self.x-old_x)*t+R.gauss(0, 4),
                    old_y+(self.y-old_y)*t+R.gauss(0, 4), radius,
                    (self.hue+R.uniform(-.08, .08)) % 1, 0,
                    R.uniform(1.4, 1.9) if numbered else R.uniform(.25, .72),
                    R.uniform(-10, 10), R.uniform(-14, 5),
                    str(R.randint(1, 24)) if numbered else ''])

    # Each monitor gets its own frameless, always-on-top, click-through surface.
    class Overlay(QWidget):
        def __init__(self, screen):
            super().__init__()
            # Input passes through; the overlay does not activate or accept focus.
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool |
                Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.setGeometry(screen.geometry())
            self.bubbles = []
            # CUSTOMIZE ACTIVITY: range(4) means four independent trails per monitor.
            self.trails = [Trail(self.width(), self.height()) for _ in range(4)]
            self.last = time.perf_counter()
            self.timer = QTimer(self)
            self.timer.setTimerType(Qt.TimerType.PreciseTimer)
            self.timer.timeout.connect(self.tick)
            # CUSTOMIZE FRAME RATE: 16 ms targets about 60 updates per second.
            self.timer.start(16)
            self.show()

        def tick(self):
            now = time.perf_counter()
            # Cap elapsed time to prevent giant movement jumps after a stall.
            dt = min(now-self.last, .05)
            self.last = now
            # Discard expired bubbles and move survivors by their gentle drift.
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

        def draw_guides(self, p):
            # Identical fixed-size mirrored geometry on each monitor; no text.
            # Open brackets and ticks leave the desktop visible through the guides.
            # CUSTOMIZE GUIDES: maximum arm length is 116 logical pixels.
            # Small screens clamp that length; this is a visual marker, not a ruler.
            # QColor uses red, green, blue, alpha: alpha 0=clear and 255=opaque.
            arm = min(116, self.width() * .14, self.height() * .2)
            for right, bottom in ((False, False), (True, False),
                                  (False, True), (True, True)):
                p.save()
                p.translate(self.width() - 1 if right else 0,
                            self.height() - 1 if bottom else 0)
                # Mirror one corner design horizontally/vertically for all four corners.
                p.scale(-1 if right else 1, -1 if bottom else 1)
                p.setBrush(Qt.BrushStyle.NoBrush)
                path = QPainterPath()
                path.moveTo(5, arm)
                path.lineTo(5, 18)
                path.lineTo(18, 5)
                path.lineTo(arm, 5)
                # Three strokes: dark contrast edge, soft cyan halo, bright cyan rim.
                for color, width in ((QColor(0, 10, 25, 90), 9),
                                     (QColor(0, 210, 255, 45), 7),
                                     (QColor(60, 225, 255, 165), 2.5)):
                    p.setPen(QPen(color, width))
                    p.drawPath(path)
                inner = QPainterPath()
                inner.moveTo(18, arm * .7)
                inner.lineTo(18, 29)
                inner.lineTo(29, 18)
                inner.lineTo(arm * .7, 18)
                p.setPen(QPen(QColor(255, 255, 255, 115), 1))
                p.drawPath(inner)
                # Alternating long/short ticks and a small gold registration target.
                for d in range(36, int(arm), 12):
                    length = 9 if d % 24 == 12 else 5
                    p.setPen(QPen(QColor(90, 230, 255, 135), 1))
                    p.drawLine(d, 5, d, 5 + length)
                    p.drawLine(5, d, 5 + length, d)
                p.setPen(QPen(QColor(255, 195, 65, 170), 1.5))
                p.drawEllipse(QRectF(28, 28, 12, 12))
                p.drawLine(25, 34, 30, 34)
                p.drawLine(38, 34, 43, 34)
                p.drawLine(34, 25, 34, 30)
                p.drawLine(34, 38, 34, 43)
                p.restore()

        def paintEvent(self, event):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Explicitly clear the alpha surface every frame, leaving no trails behind.
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            # Draw the current bubble list with age-dependent transparency.
            for x, y, radius, hue, age, life, vx, vy, number in self.bubbles:
                fade = min(1, age/.035) * (1-age/life)**.85
                if number:
                    # Keep digits readable until the final short fade-out.
                    fade = min(1, age/.07, (life-age)/.35)
                r = radius * (1 + .16*age/life)
                # CUSTOMIZE TRANSPARENCY: .075 is fill alpha; .58 is rim alpha.
                skin = QColor.fromHsvF(hue, .65, 1, .075*fade)
                rim = QColor.fromHsvF(hue, .42, 1, .58*fade)
                p.setBrush(skin)
                p.setPen(QPen(rim, .9))
                p.drawEllipse(QRectF(x-r, y-r, 2*r, 2*r))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, int(125*fade)), 1))
                p.drawArc(QRectF(x-r*.72, y-r*.72, r*1.44, r*1.44), 45*16, 75*16)
                if number:
                    # CUSTOMIZE NUMBER READABILITY: font size, outline, and fill.
                    # A stroked text path stays visible over both light and dark apps.
                    font = QFont('Segoe UI')
                    font.setPixelSize(15)
                    font.setBold(True)
                    p.setFont(font)
                    box = QRectF(x-r, y-r, 2*r, 2*r)
                    text = QPainterPath()
                    metrics = p.fontMetrics()
                    text.addText(x - metrics.horizontalAdvance(number)/2,
                                 y + (metrics.ascent()-metrics.descent())/2,
                                 font, number)
                    p.setPen(QPen(QColor(0, 0, 0, int(210*fade)), 2.5,
                                  Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                  Qt.PenJoinStyle.RoundJoin))
                    p.setBrush(QColor(255, 255, 255, int(245*fade)))
                    p.drawPath(text)
            # Draw fixed guides last so passing bubbles cannot cover their edges.
            self.draw_guides(p)
            p.end()

    # Hold references so overlays stay alive; rebuild when monitor layout changes.
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
        # Always release the global shortcut on normal exit or an exception.
        user32.UnregisterHotKey(None, hotkey_id)


if __name__ == '__main__':
    sys.exit(main())
