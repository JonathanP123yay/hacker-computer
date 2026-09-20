import os
import sys
import tkinter as tk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "face_landmarker.task")
HAND_MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")
CAMERA_INDEX = 0
VERBOSE = False
EYE_TRACKING_ENABLED = True
CURSOR_SENSITIVITY = 0.55
CURSOR_SMOOTHING = 0.20
MOUSE_OVERRIDE_SECONDS = 2.0


def configure(arguments=None):
    global CAMERA_INDEX, VERBOSE, EYE_TRACKING_ENABLED

    if arguments is None:
        arguments = sys.argv[1:]

    for arg in arguments:
        if arg in ("--verbose", "-v"):
            VERBOSE = True
        elif arg in ("--no-eye-tracking", "--gestures-only"):
            EYE_TRACKING_ENABLED = False
        elif arg in ("--eye-tracking", "--eyes"):
            EYE_TRACKING_ENABLED = True
        elif arg.isdigit():
            CAMERA_INDEX = int(arg)
        else:
            print(f"Ignoring unknown argument: {arg}")


def request_settings():
    result = {"accepted": False}
    window = tk.Tk()
    window.title("Eye Tracker - Settings")
    window.geometry("440x360")
    window.resizable(False, False)
    window.protocol("WM_DELETE_WINDOW", window.destroy)

    tk.Label(
        window,
        text="Choose your tracking settings",
        font=("Segoe UI", 16, "bold")
    ).pack(pady=(20, 16))

    form = tk.Frame(window)
    form.pack(fill="x", padx=32)

    eye_tracking = tk.BooleanVar(value=EYE_TRACKING_ENABLED)
    camera_index = tk.StringVar(value=str(CAMERA_INDEX))
    sensitivity = tk.StringVar(value=str(CURSOR_SENSITIVITY))
    smoothing = tk.StringVar(value=str(CURSOR_SMOOTHING))

    tk.Checkbutton(
        form,
        text="Enable eye tracking and calibration",
        variable=eye_tracking,
        anchor="w"
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

    tk.Label(form, text="Camera index:").grid(row=1, column=0, sticky="w", pady=6)
    tk.Spinbox(
        form,
        from_=0,
        to=9,
        textvariable=camera_index,
        width=8
    ).grid(row=1, column=1, sticky="e", pady=6)

    tk.Label(form, text="Cursor sensitivity (0.1 - 1.0):").grid(
        row=2, column=0, sticky="w", pady=6
    )
    tk.Entry(form, textvariable=sensitivity, width=10).grid(
        row=2, column=1, sticky="e", pady=6
    )

    tk.Label(form, text="Cursor smoothing (0.05 - 1.0):").grid(
        row=3, column=0, sticky="w", pady=6
    )
    tk.Entry(form, textvariable=smoothing, width=10).grid(
        row=3, column=1, sticky="e", pady=6
    )

    error_label = tk.Label(window, text="", fg="red", wraplength=380)
    error_label.pack(pady=(12, 0))

    buttons = tk.Frame(window)
    buttons.pack(pady=18)

    def start():
        try:
            selected_camera = int(camera_index.get())
            selected_sensitivity = float(sensitivity.get())
            selected_smoothing = float(smoothing.get())
            if selected_camera < 0:
                raise ValueError("Camera index must be zero or greater.")
            if not 0.1 <= selected_sensitivity <= 1.0:
                raise ValueError("Sensitivity must be between 0.1 and 1.0.")
            if not 0.05 <= selected_smoothing <= 1.0:
                raise ValueError("Smoothing must be between 0.05 and 1.0.")
        except ValueError as error:
            error_label.configure(text=str(error))
            return

        global CAMERA_INDEX, CURSOR_SENSITIVITY, CURSOR_SMOOTHING
        global EYE_TRACKING_ENABLED
        CAMERA_INDEX = selected_camera
        CURSOR_SENSITIVITY = selected_sensitivity
        CURSOR_SMOOTHING = selected_smoothing
        EYE_TRACKING_ENABLED = eye_tracking.get()
        result["accepted"] = True
        window.destroy()

    tk.Button(buttons, text="Start", command=start, width=16).pack(
        side="left", padx=6
    )
    tk.Button(buttons, text="Exit", command=window.destroy, width=16).pack(
        side="left", padx=6
    )

    window.mainloop()
    return result["accepted"]
