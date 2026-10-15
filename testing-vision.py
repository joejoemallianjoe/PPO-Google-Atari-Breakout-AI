import cv2
import mss
import time
import numpy as np

monitor_region = {"left": 576, "top": 210, "width": 749, "height": 749}
target_size = (128, 128)

time.sleep(5)

with mss.MSS() as sct:
    for i in range(100):
        # Screenshot the target region, convert to np BGRA array, then drop alpha channel
        screenshot = sct.grab(monitor_region)

        # Grab the raw bgra buffer and construct an np array. reshape to correct
        # dimensions (height, width, channels)
        img = np.frombuffer(screenshot.bgra, dtype=np.uint8)
        img = img.reshape((screenshot.height, screenshot.width, 4))

        # Drop the alpha channel
        img_bgr = img[:, :, :3]

        resized_img = cv2.resize(img_bgr, target_size, interpolation=cv2.INTER_AREA)

        cv2.imwrite(f"ai-vision-second{i}.png", resized_img)

        time.sleep(1)