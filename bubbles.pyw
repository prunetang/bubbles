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
        from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath, QLinearGradient
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

    class EdgeCurrent:
        """One jagged packet running clockwise or counterclockwise around the bezel."""
        def __init__(self, width, height):
            self.w, self.h = width, height
            self.perimeter = 2 * (width + height)
            self.position = R.uniform(0, self.perimeter)
            self.speed = R.choice((-1, 1)) * R.uniform(450, 2200)
            self.length = R.uniform(65, 290)
            self.offset = R.uniform(-4, 8)
            self.hue = R.uniform(.48, .64)
            self.age = 0
            self.life = R.uniform(.45, 2.4)
            self.reshape = 0
            self.noise = [R.uniform(-5, 5) for _ in range(35)]

        def step(self, dt):
            self.age += dt
            self.position = (self.position + self.speed * dt) % self.perimeter
            self.reshape -= dt
            if self.reshape <= 0:
                self.reshape = R.uniform(.035, .10)
                self.noise = [R.uniform(-5, 5) for _ in range(35)]
                self.speed *= R.uniform(.88, 1.12)
                self.speed = math.copysign(min(2800, max(300, abs(self.speed))), self.speed)

        def point(self, distance, inset):
            # Negative insets place parts outside the monitor; clipping is intentional.
            d = distance % self.perimeter
            if d < self.w:
                return d, inset
            d -= self.w
            if d < self.h:
                return self.w-inset, d
            d -= self.h
            if d < self.w:
                return self.w-d, self.h-inset
            return inset, self.h-(d-self.w)

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
            # CUSTOMIZE ELECTRICITY: 1-10 packets per monitor, refreshed at random times.
            self.currents = [EdgeCurrent(self.width(), self.height())
                             for _ in range(R.randint(1, 10))]
            self.current_change = time.perf_counter() + R.uniform(.4, 2.5)
            # CUSTOMIZE GLASS: start-to-start intervals are uniformly 30-300 seconds.
            # Flash alpha remains low; random blink gaps are never a fixed strobe.
            self.next_flash = time.perf_counter() + R.uniform(30, 300)
            self.flash_start = None
            self.flash_schedule = []
            self.flash_duration = 0
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
            for current in self.currents:
                current.step(dt)
            if now >= self.current_change:
                target = R.randint(1, 10)
                self.currents = self.currents[:target]
                while len(self.currents) < target:
                    self.currents.append(EdgeCurrent(self.width(), self.height()))
                self.current_change = now + R.uniform(.4, 2.5)
            self.currents = [EdgeCurrent(self.width(), self.height())
                             if c.age >= c.life else c for c in self.currents]
            if now >= self.next_flash:
                self.flash_start = now
                self.next_flash = now + R.uniform(30, 300)
                self.flash_schedule = []
                cursor = 0
                for _ in range(R.randint(2, 5)):
                    duration = R.uniform(.35, .65)
                    self.flash_schedule.append((cursor, cursor+duration, R.uniform(.10, .15)))
                    cursor += duration + R.uniform(.35, .80)
                # The last blink becomes a longer glass afterglow, then fades to clear.
                start, end, alpha = self.flash_schedule[-1]
                self.flash_schedule[-1] = (start, end+2.4, alpha)
                self.flash_duration = end+2.4
            if self.flash_start is not None and now-self.flash_start > self.flash_duration:
                self.flash_start = None
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

        def draw_electricity(self, p):
            p.setBrush(Qt.BrushStyle.NoBrush)
            for current in self.currents:
                fade = min(1, current.age/.06, (current.life-current.age)/.15)
                direction = 1 if current.speed > 0 else -1
                path = QPainterPath()
                for i in range(35):
                    x, y = current.point(current.position-direction*current.length*i/34,
                                         current.offset+current.noise[i])
                    if i == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                # CUSTOMIZE GLOW: three translucent strokes, never a solid edge panel.
                for width, alpha, saturation in ((12, .07, .9), (4, .30, .7), (1.1, .78, .15)):
                    p.setPen(QPen(QColor.fromHsvF(current.hue, saturation, 1,
                                                 max(0, alpha*fade)), width))
                    p.drawPath(path)

        def draw_glass(self, p):
            if self.flash_start is None:
                return
            elapsed = time.perf_counter()-self.flash_start
            strength = 0
            for i, (start, end, alpha) in enumerate(self.flash_schedule):
                if start <= elapsed < end:
                    # Each blink appears abruptly. Last blink fades smoothly to nothing.
                    strength = alpha
                    if i == len(self.flash_schedule)-1:
                        strength *= min(1, max(0, (end-elapsed)/1.8))
                    break
            if strength <= 0:
                return
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor.fromRgbF(.2, .85, 1, strength))
            gradient.setColorAt(.5, QColor.fromRgbF(.7, .65, 1, strength*.55))
            gradient.setColorAt(1, QColor.fromRgbF(.2, 1, .9, strength))
            p.fillRect(self.rect(), gradient)
            # CUSTOMIZE GLASS TEXTURE: fine scanlines, staggered micro-cells,
            # registration crosses, and a moving diagonal reflection. All are alpha-only.
            # Stable geometry avoids distracting frame-to-frame noise.
            w, h = self.width(), self.height()
            p.setPen(QPen(QColor.fromRgbF(.55, .95, 1, strength*.55), .7))
            for y in range(0, h, 8):
                p.drawLine(0, y, w, y)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor.fromRgbF(.55, .9, 1, strength*1.05), .9))
            for row, y in enumerate(range(20, h, 64)):
                for x in range(20 + (row % 2)*32, w, 64):
                    p.drawRoundedRect(QRectF(x, y, 19, 11), 2, 2)
                    p.drawLine(x+24, y+5, x+29, y+5)
            p.setPen(QPen(QColor.fromRgbF(.7, 1, 1, min(.24, strength*1.5)), 1))
            for y in range(48, h, 192):
                for x in range(48, w, 192):
                    p.drawLine(x-7, y, x+7, y)
                    p.drawLine(x, y-7, x, y+7)
                    p.drawEllipse(QRectF(x-12, y-12, 24, 24))
            # A broad sheen moves slowly across the glass while its texture stays fixed.
            center = (elapsed / max(.1, self.flash_duration)) * (w+h+500)-250
            sheen = QLinearGradient(center-200, 0, center+200, 200)
            sheen.setColorAt(0, QColor(170, 245, 255, 0))
            sheen.setColorAt(.5, QColor.fromRgbF(.75, .95, 1, strength*.55))
            sheen.setColorAt(1, QColor(170, 245, 255, 0))
            p.fillRect(self.rect(), sheen)

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
            self.draw_electricity(p)
            self.draw_glass(p)
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
