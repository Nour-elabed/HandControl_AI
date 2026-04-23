# 🖐 Hand Gesture Control — YouTube Controller via Webcam

> Control YouTube (or any media player) entirely with hand gestures — no mouse, no keyboard, just your hand in front of a webcam.

Built with **Python**, **MediaPipe Hands**, **OpenCV**, and **PyAutoGUI**.

---

## 📋 Table of Contents

- [Demo](#-demo)
- [Features](#-features)
- [Gestures](#-gestures)
- [How It Works](#-how-it-works)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Launch](#-launch)
- [Testing & Troubleshooting](#-testing--troubleshooting)
- [Project Structure](#-project-structure)
- [Known Limitations](#-known-limitations)
- [Future Improvements](#-future-improvements)

---

## 🎬 Demo

```
Webcam feed opens in a window titled "Hand Gesture Control".
Show your hand → landmarks appear → gesture is recognized → YouTube responds.
Press ESC to quit.
```

The HUD shows:
- **Top bar** — current gesture name + mapped action
- **Progress bar** — gesture stability (fills over 4 frames before firing)
- **Green dot** — lights up when a gesture is confirmed and active
- **Cheat-sheet panel** — bottom-left corner, always visible

---

## ✨ Features

- Real-time hand detection at 30 FPS on CPU (no GPU required)
- 21 landmark overlay drawn directly on the webcam feed
- 5 distinct gestures → 5 mapped actions
- Supports both **left and right hand** automatically
- Anti-debounce system (HOLD_FRAMES + per-gesture cooldowns)
- Volume control with smooth throttle (no key spamming)
- Window focus management — keeps YouTube active without stealing the OpenCV window
- Clean exit on ESC or camera failure

---

## 🤚 Gestures

| Gesture | Hand Shape | Action | Type |
|---------|-----------|--------|------|
| ✊ **FIST** | All fingers closed | ⏯ Pause / Play (`K`) | Single-fire (1.5s cooldown) |
| 🖐 **OPEN** | All 5 fingers open | 🔉 Volume DOWN (`↓`) | Continuous (150ms throttle) |
| 👍 **THUMBS UP** | Only thumb extended | 🔊 Volume UP (`↑`) | Continuous (150ms throttle) |
| ✌ **PEACE** | Index + Middle up | ⏭ Next Video (`Shift+N`) | Single-fire (2.0s cooldown) |
| ☝ **POINT** | Only index finger up | ⏪ Rewind 10s (`J`) | Single-fire (2.0s cooldown) |

---

## ⚙️ How It Works

```
Webcam Frame
    │
    ▼
cv2.flip() ──► BGR→RGB conversion
    │
    ▼
MediaPipe Hands
    │  detects up to 1 hand
    │  returns 21 landmarks (x, y, z) per hand
    ▼
fingers_up(landmarks, handedness)
    │  thumb  → compared on X axis (flipped for left hand)
    │  fingers → compared on Y axis (tip.y < pip.y = raised)
    ▼
classify_gesture([thumb, index, middle, ring, pinky])
    │  maps boolean array to gesture name
    ▼
Stability Check (HOLD_FRAMES = 4)
    │  gesture must be stable for 4 consecutive frames
    ▼
do_action(gesture)
    │  continuous → throttled every 150ms
    │  single-fire → per-gesture cooldown (1.5s or 2.0s)
    ▼
PyAutoGUI → keypress sent to OS
    │
    ▼
focus_youtube() → rate-limited to once every 3s
```

### Key algorithm — `fingers_up()`

```python
def fingers_up(lm, handedness="Right"):
    # Thumb: lateral axis (X), direction flips for left hand
    if handedness == "Right":
        thumb = lm[4].x < lm[3].x
    else:
        thumb = lm[4].x > lm[3].x

    # Fingers 2–5: vertical axis (Y), tip above PIP = raised
    for tip, pip in zip([8,12,16,20], [6,10,14,18]):
        state.append(lm[tip].y < lm[pip].y)
```

---

## 📦 Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| Python | ≥ 3.8 | Runtime |
| opencv-python | ≥ 4.5 | Webcam capture & display |
| mediapipe | ≥ 0.10 | Hand landmark detection |
| pyautogui | ≥ 0.9 | Keyboard simulation |
| pygetwindow | ≥ 0.0.9 | Window focus management |
| absl-py | any | Suppress MediaPipe logs |

> **OS:** Windows 10/11 recommended (PyGetWindow is Windows-optimized).
> On macOS/Linux, `pygetwindow` may need replacement with `wmctrl` or `applescript`.

---

## 🛠 Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/hand-gesture-control.git
cd hand-gesture-control
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install opencv-python mediapipe pyautogui pygetwindow absl-py
```

Or install all at once from the requirements file:

```bash
pip install -r requirements.txt
```

**`requirements.txt`:**
```
opencv-python>=4.5.0
mediapipe>=0.10.0
pyautogui>=0.9.53
pygetwindow>=0.0.9
absl-py
```

### 4. Verify your camera

Make sure your webcam is connected and not used by another application (Zoom, Teams, etc.).

---

## 🚀 Launch

### Basic launch

```bash
python gesture_control.py
```

The script will:
1. Try camera index `1` first (external webcam), then fall back to `0` (built-in)
2. Flush 20 warm-up frames
3. Open the `Hand Gesture Control` window (1280×720)
4. Attempt to focus any YouTube/browser window

### Expected output in terminal

```
Hand Gesture Control started. Press ESC in the window to quit.
[ACTION] ⏯  Pause / Play       ← when you make a FIST
[ACTION] ⏭  Next video         ← when you make a PEACE sign
[ACTION] ⏪  Rewind 10 s        ← when you point with one finger
Done.                            ← after pressing ESC
```

### Stop the script

Press **ESC** inside the `Hand Gesture Control` window.

> ⚠️ Do not close the terminal directly — it will orphan the camera process.

---

## 🧪 Testing & Troubleshooting

### Test 1 — Camera check

Run this before the main script to confirm your camera works:

```python
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print("Camera OK:", ret, frame.shape if ret else "NO FRAME")
cap.release()
```

Expected output: `Camera OK: True (720, 1280, 3)`

If `ret` is `False`, try index `1` or `2`.

---

### Test 2 — MediaPipe install check

```python
import mediapipe as mp
hands = mp.solutions.hands.Hands()
print("MediaPipe OK")
```

---

### Test 3 — Gesture-by-gesture checklist

Open the script, then test each gesture in front of the webcam:

| Step | Gesture | Expected HUD text | Expected action |
|------|---------|-------------------|-----------------|
| 1 | Show open hand 🖐 | `OPEN → Volume DOWN` | Volume decreases |
| 2 | Thumb up 👍 | `THUMB UP → Volume UP` | Volume increases |
| 3 | Make a fist ✊ | `FIST → Pause/Play` | YouTube pauses |
| 4 | Peace sign ✌ | `PEACE → Next Video` | Next video loads |
| 5 | Point with index ☝ | `POINT → Rewind 10s` | Video rewinds |

Check the **green dot** (top-right corner of the window) — it should light up when the gesture is confirmed.

---

### Common issues

**❌ `ERROR: No camera found.`**
```bash
# List available cameras
python -c "import cv2; [print(i, cv2.VideoCapture(i).isOpened()) for i in range(4)]"
```
Change the index in the script: `cv2.VideoCapture(1)` → `cv2.VideoCapture(0)`

---

**❌ `ModuleNotFoundError: No module named 'mediapipe'`**
```bash
pip install mediapipe
# If that fails on Python 3.12+:
pip install mediapipe --pre
```

---

**❌ Window closes immediately / freezes**

This is the known `focus_youtube()` bug — already fixed in this version.
Make sure you are running the corrected script. Check that `_last_focus_attempt` and `_youtube_focused` globals exist at the top of the file.

---

**❌ Gestures fire randomly / too sensitive**

Increase `HOLD_FRAMES` in the script (default: 4):
```python
HOLD_FRAMES = 6   # requires 6 stable frames before triggering
```

---

**❌ Volume changes too fast**

Increase `CONTINUOUS_INTERVAL` (default: 0.15 seconds):
```python
CONTINUOUS_INTERVAL = 0.3   # slower volume steps
```

---

**❌ Actions go to wrong window (not YouTube)**

Make sure a browser with YouTube is open. The script searches window titles for:
`"YouTube"`, `"Chrome"`, `"Firefox"`, `"Edge"`, `"Opera"`

If your browser title doesn't include any of these, add it:
```python
for title_fragment in ("YouTube", "Chrome", "Firefox", "Edge", "Opera", "Brave"):
```

---

**❌ Left hand not detected correctly (wrong gestures)**

MediaPipe returns handedness automatically. The script handles it:
```python
handedness_label = handInfo.classification[0].label  # "Left" or "Right"
```
Check the top-right corner of the HUD window — it shows `Left hand` or `Right hand`.
If it shows the wrong one, your camera may be mirrored differently; try removing `cv2.flip(img, 1)`.

---

## 📁 Project Structure

```
hand-gesture-control/
│
├── gesture_control.py      # Main script — run this
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## ⚠️ Known Limitations

| Limitation | Severity | Workaround |
|-----------|----------|------------|
| Poor performance in low light | High | Improve room lighting or add a desk lamp |
| Only 1 hand processed at a time | Medium | By design — reduces false positives |
| Static gestures only (no swipe/pinch) | Medium | Planned for future version |
| Window focus can drift on multi-monitor setups | Medium | Click the browser once manually to refocus |
| PEACE vs POINT confusion (~5% error) | Low | Hold the gesture a bit longer |
| Requires Windows for full PyGetWindow support | Low | Use `wmctrl` on Linux |

---

## 🚀 Future Improvements

- [ ] Dynamic gestures (swipe left/right, pinch zoom)
- [ ] Two-hand support (double the gesture vocabulary)
- [ ] Config file for custom gesture→action mapping
- [ ] Support for Spotify, VLC, Netflix
- [ ] Startup calibration wizard (lighting check, hand positioning guide)
- [ ] Web dashboard to monitor gesture confidence in real time

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Credits

- [MediaPipe Hands](https://developers.google.com/mediapipe/solutions/vision/hand_landmarker) — Google's hand landmark detection model
- [OpenCV](https://opencv.org/) — computer vision and webcam capture
- [PyAutoGUI](https://pyautogui.readthedocs.io/) — cross-platform keyboard/mouse automation
