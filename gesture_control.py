import ctypes
import math
import time


PINCH_THRESHOLD = 0.045
CLICK_COOLDOWN = 0.35
DRAG_HOLD_SECONDS = 0.25


class GestureController:
    def __init__(self):
        self.previous_gesture = "NONE"
        self.last_left_click = 0.0
        self.last_right_click = 0.0
        self.left_button_down = False
        self.paused = False
        self.pinch_started_at = None

    @staticmethod
    def distance(first, second):
        return math.sqrt(
            (first.x - second.x) ** 2 +
            (first.y - second.y) ** 2 +
            (first.z - second.z) ** 2
        )

    @staticmethod
    def finger_up(hand, tip, pip):
        return hand[tip].y < hand[pip].y

    def identify(self, hand):
        if hand is None:
            return "NONE"

        index_up = self.finger_up(hand, 8, 6)
        middle_up = self.finger_up(hand, 12, 10)
        ring_up = self.finger_up(hand, 16, 14)
        pinky_up = self.finger_up(hand, 20, 18)
        pinch = self.distance(hand[4], hand[8])

        if pinch < PINCH_THRESHOLD:
            return "PINCH"
        if index_up and middle_up and not ring_up and not pinky_up:
            return "TWO FINGER"
        if index_up and not middle_up and not ring_up and not pinky_up:
            return "POINT"
        if not index_up and not middle_up and not ring_up and not pinky_up:
            return "FIST"
        if index_up and middle_up and ring_up and pinky_up:
            return "OPEN HAND"
        return "OTHER"

    @staticmethod
    def click(button):
        if button == "left":
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        else:
            ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)

    @staticmethod
    def button_down(button):
        if button == "left":
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)

    @staticmethod
    def button_up(button):
        if button == "left":
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

    def update(self, hand):
        gesture = self.identify(hand)
        now = time.monotonic()

        if gesture == "FIST":
            self.paused = True
            self.release_drag()
            self.pinch_started_at = None
        else:
            self.paused = False

            if gesture == "TWO FINGER" and self.previous_gesture != "TWO FINGER":
                if now - self.last_right_click >= CLICK_COOLDOWN:
                    self.click("right")
                    self.last_right_click = now
            elif gesture == "PINCH":
                if self.pinch_started_at is None:
                    self.pinch_started_at = now
                if (
                    not self.left_button_down
                    and now - self.pinch_started_at >= DRAG_HOLD_SECONDS
                ):
                    self.button_down("left")
                    self.left_button_down = True
            else:
                if (
                    self.previous_gesture == "PINCH"
                    and self.pinch_started_at is not None
                    and not self.left_button_down
                    and now - self.last_left_click >= CLICK_COOLDOWN
                ):
                    self.click("left")
                    self.last_left_click = now
                self.release_drag()
                self.pinch_started_at = None

        self.previous_gesture = gesture
        return gesture

    def release_drag(self):
        if self.left_button_down:
            self.button_up("left")
            self.left_button_down = False

    def close(self):
        self.release_drag()

    def reset(self):
        self.update(None)
        self.paused = False
        self.previous_gesture = "NONE"


def draw_hand(frame, hand):
    height, width, _ = frame.shape
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)
    ]

    for first, second in connections:
        start = (int(hand[first].x * width), int(hand[first].y * height))
        end = (int(hand[second].x * width), int(hand[second].y * height))
        import cv2
        cv2.line(frame, start, end, (0, 255, 0), 2)

    import cv2
    for index, point in enumerate(hand):
        center = (int(point.x * width), int(point.y * height))
        cv2.circle(frame, center, 8 if index == 8 else 4, (0, 255, 255), -1)
