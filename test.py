import cv2

target_size = (128, 128)

for i in range(5,24):
    img = cv2.imread(f"second{i}.png")
    resized = cv2.resize(img, target_size, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f"AI-vision-second{i}.png", resized)


# OpenCV has to decide how to downscale/upscale an image.
# When upscaling, it has to figure out how to fill in missing pixels.
# When downscaling, it has to figure out how to merge pixels together.