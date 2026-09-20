import ctypes
import time
from ctypes import wintypes

from gaze_utils import interpolate_mapping


class CursorController:
    def __init__(self, sensitivity=0.55, smoothing=0.20, mouse_override_seconds=2.0):
        self.sensitivity = sensitivity
        self.smoothing = smoothing
        self.mouse_override_seconds = mouse_override_seconds
        self.smooth_x = None
        self.smooth_y = None
        self.last_cursor_x = None
        self.last_cursor_y = None
        self.manual_override_until = 0.0

    def manual_mouse_moved(self):
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))

        if self.last_cursor_x is None or self.last_cursor_y is None:
            self.last_cursor_x = point.x
            self.last_cursor_y = point.y
            return False

        moved = (
            abs(point.x - self.last_cursor_x) > 3 or
            abs(point.y - self.last_cursor_y) > 3
        )
        if moved:
            self.manual_override_until = (
                time.monotonic() + self.mouse_override_seconds
            )
            self.last_cursor_x = point.x
            self.last_cursor_y = point.y

        return time.monotonic() < self.manual_override_until

    def move_from_gaze(self, gaze_x, gaze_y, calibration_samples):
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        gaze_x = 1.0 - gaze_x
        gaze_y = 1.0 - gaze_y
        gaze_x = 0.5 + (gaze_x - 0.5) * self.sensitivity
        gaze_y = 0.5 + (gaze_y - 0.5) * self.sensitivity

        if calibration_samples:
            x_map = [(sample[0][0], sample[1][0]) for sample in calibration_samples]
            y_map = [(sample[0][1], sample[1][1]) for sample in calibration_samples]

            target_x = interpolate_mapping(gaze_x, x_map)
            target_y = interpolate_mapping(gaze_y, y_map)

            x = int(target_x * screen_width)
            y = int(target_y * screen_height)
        else:
            center_x = screen_width // 2
            center_y = screen_height // 2
            x = int(center_x + (gaze_x - 0.5) * screen_width * 1.4)
            y = int(center_y + (gaze_y - 0.5) * screen_height * 1.4)

        x = max(0, min(screen_width - 1, x))
        y = max(0, min(screen_height - 1, y))

        if self.smooth_x is None or self.smooth_y is None:
            self.smooth_x = x
            self.smooth_y = y
        else:
            self.smooth_x += (x - self.smooth_x) * self.smoothing
            self.smooth_y += (y - self.smooth_y) * self.smoothing

        x = int(self.smooth_x)
        y = int(self.smooth_y)
        ctypes.windll.user32.SetCursorPos(x, y)
        self.last_cursor_x = x
        self.last_cursor_y = y


def trigger_mouse_click():
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
