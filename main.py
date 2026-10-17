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
from playwright.sync_api import sync_playwright
import asyncio
import re

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
gym.spaces.Discrete: A class for defining discrete action and observation spaces.
matplotlib.pyplot: A library for creating plots and visualizations.
cv2: The OpenCV library, used for image processing tasks.
playwright: A Python library for browser automation. It allows me to interact
            with the JS code so I can get the score and game over stuff
            really quickly without having to use some OCR or CV solution.
"""

class GoogleAtariBreakout(Env): # This signifies it inherits from gym.Env
    
    def __init__(self, page):
        super().__init__() # just good practice. always call super constructor

        self.first_start = True

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

        self.cap = mss.MSS()
        self.page = page

        # We are going to manually intercept every JS script that's downloaded
        # Then if we find the target one containing the game's code, we
        # intercept it and overwrite part of its code to expose its
        # local variables so we can actually read the score and
        # the game over flag
        # I had AI help me with this because there's no way I know how to
        # reverse engineer stuff sorry I'm not cracked at CS
        def inject_memory_leak(route):
            if "m=syjv" not in route.request.url:
                route.continue_()
                return

            response = route.fetch()
            original_text = response.text()
            target_signature = ",IXE=function(a,b){"

            if target_signature in original_text:
                # REMOVED 'debugger;' so the game runs at full speed automatically!
                print("Injected successfully!")
                injected_text = original_text.replace(
                    target_signature,
                    target_signature + "window.top.__stolen_game_state=a;"
                )
                route.fulfill(response=response, body=injected_text)
            else:
                route.continue_()

        self.page.route("**/xjs/_/js/**", inject_memory_leak)

        # 2. Now run your normal flow
        self.page.goto("https://www.google.com/search?q=block+breaker")
        self.page.get_by_role("button", name="Daily Challenge").click()

        # Finds the game's iframe, then waits for it to be visible
        # Aight so ima be honest this isn't the most elegant solution but I think it works lmao
        game_frame_locator = self.page.frame_locator('iframe[jsname="V42h1d"]')
        canvas_locator = game_frame_locator.locator("canvas")
        mute_button_locator = game_frame_locator.get_by_role("button", name="Mute")
        progress_bar = game_frame_locator.locator('div[aria-label="Loading..."]')

        mute_button_locator.wait_for(state="visible", timeout=15000)
        progress_bar.wait_for(state="hidden", timeout=15000)

        time.sleep(2)

        print("Game loaded successfully!")

        # Ok this JS code is stuff I learned myself and WHAT A PAIN IN THE AHH
        # getting the exact pixel is a pain in the AHH too

        # Playwright is gonna deal with all the iframe BS for us
        # (because an iframe is like another webpage so getBoundingClientRect() is relative to)

        """
        A long, long time ago, CSS was being made... but its creators realized that one
        pixel on your laptop screen wasn't the same physical size in say inches as a
        pixel on your phone... so they created CSS PIXELS! AND NOW THAT'S WHY WE GET
        A CONFUSING WAY TO GET THE ABSOLUTE PIXEL POSITION!!

        Physical pixel: An actual pixel on your screen. Depends on how densely packed
                        pixels are. Think "PPI" -- pixels per inch.
        CSS pixel:      An angular measurement, defined as one pixel on a standard
                        96 PPI monitor from an arm's length (~28 inches)

        Software has no way of knowing how big one pixel is on your display, so a
        scaling factor needs to be specified. This is called DPR.

        Physical pixel = CSS pixel * DPR 
        """

        canvas_viewport_coordinates = canvas_locator.bounding_box()

        # It's not perfect, but it works. it's like off by +-2 pixels on average, which makes
        # no difference for a CNN.

        mss_region = self.page.evaluate(
            """
            // Define an anonymous function
            // We can pass python values into the function by creating parameters
            (canvas_viewport_coords) => {
                // Use the difference between the browser's width and the webpage's width
                // as a reliable way to get border thickness
                // Divide by two because there are two borders on the side
                const borderThickness = (window.outerWidth - window.innerWidth) / 2;
                const tabHeight = window.outerHeight - borderThickness - window.innerHeight;

                // Calculate the device pixel ratio (e.g., 1.0 = 100%, 1.25 = 125%, stuff scale)
                const dpr = window.devicePixelRatio || 1;

                // Now get the actual screen coordinates
                // We add window.screenX and window.screenY in case the window is dragged
                // around and not in the top-left corner

                // screenX and screenY are gonna be super precise (sub-pixel positions),
                // so we will need to round down on the position
                // and then round up on the width and height to ensure that the entire window
                // actually gets captured
                const screenX = Math.floor(window.screenX + borderThickness + canvas_viewport_coords.x);
                const screenY = Math.floor(window.screenY + tabHeight + canvas_viewport_coords.y);

                // If top-left corner is at some super precise position like 572.2, 370.5, and width is 750 with a height of 750, what's effectively gonna happen
                // is that we get some decimal value --> it gets rounded
                const effectiveWidth = Math.round(canvas_viewport_coords.width);
                const effectiveHeight = Math.round(canvas_viewport_coords.height);

                return {
                    left: Math.round(screenX * dpr),
                    top: Math.round(screenY * dpr),
                    width: Math.round(effectiveWidth * dpr),
                    height: Math.round(effectiveHeight * dpr)
                };
            }
            """,
            canvas_viewport_coordinates
        )

        self.game_location = mss_region
        self.old_score = 0
        self.game_iframe = game_frame_locator

        print("Grabbed monitor-specific coordinates of game window")
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.old_score = 0

        if self.first_start:
            self.page.keyboard.press("ArrowUp")
            self.first_start = False
        else:
            self.game_iframe.get_by_text("Play again", exact=True).click()
            self.page.keyboard.press("ArrowUp")

        return self.get_observation(), {}

    def step(self, action):
        # 0 - left
        # 1 - right
        # 2 - up
        # 3 - no-op

        # Have a dictionary map indices to actions (even if it's sort of redundant, it's nice
        # to see for us)

        action_map = {
            0:  "ArrowLeft",
            1:  "ArrowRight",
            2:  "ArrowUp",
            3:  "no-op"
        }

        if action != 3:
            # Key up everything first
            for a in action_map.values():
                if a != "no-op":
                    self.page.keyboard.up(a)

            self.page.keyboard.down(action_map[action])

        observation = self.get_observation() 
        done, score = self.get_score_and_done()

        if self.old_score != score:
            reward = (score - self.old_score) / 1000
            self.old_score = score
        elif not done:
            reward = 0
        else:
            reward = -1

        return observation, reward, done, False, {}

    def get_score_and_done(self):
        # Fetch the real-time variables from memory at lightning speed
        metrics = self.page.evaluate("""() => {
            const game = window.top.__stolen_game_state;
            if (!game) return { score: 0, done: false };

            return {
                score: game.Ji,    // Perfect reward signal
                done: game.Cj      // True/False game-over state flag
            };
        }""")
        return metrics["done"], metrics["score"]

    def get_observation(self):
        screenshot = self.cap.grab(self.game_location)

        # Convert to BGRA numpy array

        img_data = np.frombuffer(screenshot.bgra, dtype=np.uint8)
        img_data = img_data.reshape((screenshot.height, screenshot.width, 4))

        # (For debugging purposes)

        cv2.imwrite("what_ai_sees_test.png", img_data)

        # Grayscale it and downscale

        grayscale_data = cv2.cvtColor(img_data, cv2.COLOR_BGRA2GRAY)
        target_size = (self.IMAGE_WIDTH, self.IMAGE_HEIGHT)
        resized_img = cv2.resize(grayscale_data, target_size, interpolation=cv2.INTER_AREA)

        # Add a new dimension b/c SB3 (or rather PyTorch) 
        # will expect (channels, height, width)

        resized_img = resized_img[np.newaxis, :, :]

        return resized_img

    def close(self):
        super().close()
        self.cap.close()

"""
I apologize for this sacrilege but trying to find the game's internal JS was
and trying to get it to launch properly genuinely pmo so much that I used Gemini to
generate some of the code below here. I needed the game's internal JS
because it was either that or a super slow OCR algorithm to get the score
in order to reward the agent. I figured if I was gonna get the game's internal JS
why not just scrap the done mechanic that uses OpenCV template matching
and just directly listen to whatever function is called when the game is over
in the JS
"""

def main():
    with sync_playwright() as p:
        # Launch the browser. headless=False means we actually show the browser being launched
        # Start-maximized maximizes the window
        # disable blink features makes it look less like a bot so chrome doesn't give us
        # the annoying "Are you a human?" captcha pop-up
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        # This opens the new window in sort of incognito mode. no viewport 
        # = true was some fix that was needed because it was ignoring start-maximized by making the
        # page's viewport not take up the entire window
        # user_agent is just some other stuff to mimic being a human

        context = browser.new_context(
            bypass_csp=True,
            no_viewport=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
                " like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        # This opens a new page
        page = context.new_page()

        env = GoogleAtariBreakout(page)
        
        while True:
            init_observation, info = env.reset()

            timestep = 0
            done = False

            while not done:
                observation, reward, done, truncated, info = env.step(env.action_space.sample())
                print(f"Timestep: {timestep} |", reward, done, truncated, info)
                time.sleep(4 / 60)
                timestep += 1

        #while True:
        #    time.sleep(1)
        #    print(env.get_score_and_done())
        # img = print(env.get_done())
        # img = np.array(img).reshape((img.height, img.width, 4))
        # img_bgr = img[:, :, :3]
        # cv2.imwrite("done_img_test.png", img_bgr)

        time.sleep(500)
        browser.close()

main()