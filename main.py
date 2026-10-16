import mss
import pydirectinput
import pyautogui
import pygetwindow as gw
import time
from gymnasium import Env
from gymnasium.spaces import Box, Discrete
from matplotlib import pyplot as plt
import cv2
import numpy as np

"""
Import explanation (for me to remember):
mss: Stands for "multi-screen shot". Library used for capturing screenshots of the screen.
pydirectinput: A library that allows for simulating keyboard and mouse input. 
               It is used to send input commands to the game.
pyautogui: A library for GUI automation, used for locating images on the screen and 
           performing mouse actions.
pygetwindow: A library for interacting with windows, used to get the position and 
             size of the game window.
gym: A library for creating custom reinforcement learning environments.
gym.spaces: Modules for defining action and observation spaces in the reinforcement learning
            environment.
gym.spaces.Box: A class for defining continuous action or observation spaces.
                (think like an n-dimensional continuous "vector"
                 e.g., for pixel values in an image).
gym.spaces.Discrete: A class for defining discrete action or observation spaces.
matplotlib.pyplot: A library for creating plots and visualizations.
cv2: The OpenCV library, used for image processing tasks.
"""

class GoogleAtariBreakout(Env): # This signifies it inherits from gym.Env
    def __init__(self):
        super().__init__() # just good practice. always call super constructor

        self.IMAGE_HEIGHT = 128
        self.IMAGE_WIDTH = 128

        # Define our action and observation spaces
        # We'll have 4 actions (left, right, up, no-op) 
        # and a 128x128 downscaled grayscale iamge

        self.action_space = Discrete(4)
        self.observation_space = Box(
            low=0,
            high=255,
            shape=(1, self.IMAGE_HEIGHT, self.IMAGE_WIDTH),
            dtype = np.uint8
        )

        self.game_location = {"left": 576, "top": 210, "width": 749, "height": 749}

        # Two corners for PLAY AGAIN button:
        # 759, 713
        # 1050, 769
        # Width: 292, Height: 57

        # Create MSS instance and save it as a field so we don't re-create it
        # every frame

        self.done_location = {"left": 759, "top": 713, "width": 292, "height": 57}
        self.cap = mss.MSS()
        self.done_image = cv2.imread("done_img.png", cv2.IMREAD_GRAYSCALE)

        # cv2.imread will do (WIDTH, HEIGHT), excluding channels b/c grayscale

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

    def step(self, action):
        # 0 - left
        # 1 - right
        # 2 - up
        # 3 - no-op
        pass

    def get_observation(self):
        screenshot = self.cap.grab(self.game_location)

        # Convert to BGRA numpy array

        img_data = np.frombuffer(screenshot.bgra, dtype=np.uint8)
        img_data = img_data.reshape((screenshot.height, screenshot.width, 4))

        # Grayscale it and downscale

        grayscale_data = cv2.cvtColor(img_data, cv2.COLOR_BGRA2GRAY)
        target_size = (self.IMAGE_WIDTH, self.IMAGE_HEIGHT)
        resized_img = cv2.resize(grayscale_data, target_size, interpolation=cv2.INTER_AREA)

        # Add a new dimension b/c SB3 (or rather PyTorch) 
        # will expect (channels, height, width)

        resized_img = resized_img[np.newaxis, :, :]

        return resized_img

    def get_done(self):
        target_region_img = self.cap.grab(self.done_location)
        region_data = np.frombuffer(target_region_img.bgra, dtype=np.uint8)
        region_data = region_data.reshape((target_region_img.height, target_region_img.width, 4))
        grayscale_data = cv2.cvtColor(region_data, cv2.COLOR_BGRA2GRAY)

        # Use OpenCV template mattching to detect if it's there or not (overkill but i'm lazy)
        # We don't care about the min value or the max or min locations

        result = cv2.matchTemplate(grayscale_data, self.done_image, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _, = cv2.minMaxLoc(result)

        # This represents 0.8 or more correlation

        return max_val > 0.8

    def close(self):
        super().close()
        self.cap.close()

env = GoogleAtariBreakout()
img = print(env.get_done())
#img = np.array(img).reshape((img.height, img.width, 4))
#img_bgr = img[:, :, :3]
#cv2.imwrite("done_img_test.png", img_bgr)