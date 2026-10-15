import cv2
import mss
import time

monitor_region = {
    "left": 576,
    "top": 210,
    "width": 749,
    "height": 749
}

target_size = (128, 128)

with mss.mss() as sct:
    for i in range(10000):
        screenshot = sct.grab(monitor_region)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=f"second{i}.png")
        time.sleep(1)