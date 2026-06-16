"""
HSV Tuner — find the right color range for your target.
Run this, point camera at your target, drag sliders until
only the target shows white in the mask window. Note the values,
paste into Config in cv_pipeline.py.

Usage: python hsv_tuner.py
       python hsv_tuner.py --camera 1   # if wrong camera
"""
import cv2
import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--camera", type=int, default=0)
args = parser.parse_args()

cap = cv2.VideoCapture(args.camera)
cv2.namedWindow("HSV Tuner")

# Sliders
for name, val, max_val in [
    ("H low", 5, 180), ("H high", 20, 180),
    ("S low", 150, 255), ("S high", 255, 255),
    ("V low", 150, 255), ("V high", 255, 255),
]:
    cv2.createTrackbar(name, "HSV Tuner", val, max_val, lambda x: None)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lo = np.array([cv2.getTrackbarPos(n, "HSV Tuner") for n in ("H low", "S low", "V low")])
    hi = np.array([cv2.getTrackbarPos(n, "HSV Tuner") for n in ("H high", "S high", "V high")])
    mask = cv2.inRange(hsv, lo, hi)
    result = cv2.bitwise_and(frame, frame, mask=mask)

    cv2.imshow("HSV Tuner", np.hstack([frame, result]))
    print(f"\r hsv_lower=({lo[0]},{lo[1]},{lo[2]})  hsv_upper=({hi[0]},{hi[1]},{hi[2]})", end="")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
