import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "face_landmarker.task")
HAND_MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")
CAMERA_INDEX = 0
VERBOSE = False
CURSOR_SENSITIVITY = 0.55
CURSOR_SMOOTHING = 0.20
MOUSE_OVERRIDE_SECONDS = 2.0


def configure(arguments=None):
    global CAMERA_INDEX, VERBOSE

    if arguments is None:
        arguments = sys.argv[1:]

    for arg in arguments:
        if arg in ("--verbose", "-v"):
            VERBOSE = True
        elif arg.isdigit():
            CAMERA_INDEX = int(arg)
        else:
            print(f"Ignoring unknown argument: {arg}")
