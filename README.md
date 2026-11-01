# Bubbles

A transparent, click-through Windows desktop overlay with colorful foam-like bubble trails and glowing corner guides.

## About

Small bubbles follow invisible, randomly moving fingertips across your screen. Motion shifts between slow, smooth curves and sudden zips in every direction. Colors and sizes change continuously, and bubbles fade quickly. Occasionally, a slightly larger bubble contains a readable number from **1–24**.

Translucent cyan brackets, ticks, and gold accents mark all four corners of each monitor without words. They provide visual reference points when comparing screens; they do not measure physical screen size or calibrate monitors.

- Transparent background, bubble skins, and corner guides
- Clicks pass through to the apps underneath
- Independent animation with no mouse interaction
- Multiple-monitor support
- No menus, control panels, or sound
- One app file: `bubbles.pyw`

## Made with ChatGPT · #vibecoding

All of this project's application code, code comments, and README were generated with **ChatGPT**, guided by human descriptions and feedback. This project was made through **#vibecoding**: describing an idea, generating an app, trying it, and refining it through conversation.

You can do this too: describe a cool app of your own, work through the details with ChatGPT, test what it creates, and share your code so others can read it and learn. The comments in `bubbles.pyw` explain the animation and point out values you can customize.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer with pip and the `py` launcher
- PySide6

## Install and run

1. Download this repository and extract it if it is a ZIP.
2. Open Command Prompt and install the dependency:

   ```bat
   py -m pip install PySide6
   ```

3. Double-click `bubbles.pyw` to start the overlay.

If double-clicking does not launch it, open Command Prompt in the folder containing the file and run:

```bat
py bubbles.pyw
```

This also lets you see error messages. If your installation uses `python` instead of `py`, substitute `python` in both commands.

## Exit

Press **Ctrl + Alt + Shift + Backspace** from any normal desktop app.

Close the running version before starting another copy. If the shortcut is unavailable, the app displays a message and does not start. If needed, end the corresponding Python process in Windows Task Manager.

## Customize

Open `bubbles.pyw` in a text editor. Search for **CUSTOMIZE** to find the main settings. Save your changes, close the running overlay, and restart it.

| Setting | Where to look |
| --- | --- |
| Slow movement, fast zips, turns, and easing | `Trail.change()` |
| Color cycling, bubble spacing, size, lifetime, and number probability | `Trail.step()` |
| Number range | `R.randint(1, 24)` |
| Trails per monitor | `range(4)` in `Overlay.__init__()` |
| Refresh interval | `self.timer.start(16)` |
| Guide dimensions, colors, and transparency | `Overlay.draw_guides()` |
| Bubble transparency and number font/outline | `Overlay.paintEvent()` |

Sizes use Qt logical pixels, so Windows display scaling affects their physical appearance. Smaller bubble spacing or more trails increases rendering work.

## Validation

Python syntax was checked. The commenting update was checked to preserve executable behavior. Windows overlay behavior has not been verified in the Linux development environment.
