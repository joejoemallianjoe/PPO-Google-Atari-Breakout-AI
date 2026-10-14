from mss import mss
import pydirectinput
import pyautogui
import pygetwindow as gw
import time
from gym import Env
from gym.spaces import Box, Discrete
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

        HEIGHT = 128
        WIDTH = 128

        self.action_space = spaces.Discrete(3)
        self.observation_space = Spaces.Box(
            low=0,
            high=255,
            shape=(1, HEIGHT, WIDTH)
        )