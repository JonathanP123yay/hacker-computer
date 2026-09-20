import ctypes

import cv2
import mediapipe as mp
import numpy as np
from PIL import ImageGrab

from gaze_utils import average_points, get_gaze, landmark_to_pixel


def calibrate_monitor_mapping(camera, landmarker, verbose=False):
    targets = [
        (0.10, 0.10),
        (0.90, 0.10),
        (0.10, 0.90),
        (0.90, 0.90),
        (0.50, 0.50),
    ]

    samples = []

    cv2.namedWindow("User Preview", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("User Preview", 480, 270)

    for target_x, target_y in targets:
        print(
            "Look at the target circle and press Y when your eye is locked on it: "
            f"({target_x:.0%}, {target_y:.0%})"
        )

        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        circle_x = int(target_x * screen_width)
        circle_y = int(target_y * screen_height)

        background = ImageGrab.grab(
            bbox=(0, 0, screen_width, screen_height)
        )
        image = cv2.cvtColor(
            np.array(background),
            cv2.COLOR_RGB2BGR
        )
        cv2.circle(
            image,
            (circle_x, circle_y),
            max(20, min(screen_width, screen_height) // 30),
            (0, 255, 255),
            -1
        )
        cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(
            "Calibration",
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN
        )
        cv2.imshow("Calibration", image)

        while True:
            success, preview_frame = camera.read()
            if success:
                preview_frame = cv2.flip(preview_frame, 1)
                cv2.imshow("User Preview", preview_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                cv2.destroyAllWindows()
                camera.release()
                print("Eye tracking stopped.")
                raise SystemExit
            if key == ord("y"):
                break

        cv2.destroyWindow("Calibration")

        collected = []
        for _ in range(8):
            success, frame = camera.read()
            if not success:
                continue

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame
            )

            result = landmarker.detect(mp_image)
            if not result.face_landmarks:
                continue

            landmarks = result.face_landmarks[0]
            right_iris_points = []
            for i in range(473, 478):
                point = landmark_to_pixel(
                    landmarks[i], frame.shape[1], frame.shape[0]
                )
                right_iris_points.append(point)

            right_iris = average_points(right_iris_points)
            right_eye_left = landmark_to_pixel(
                landmarks[362], frame.shape[1], frame.shape[0]
            )
            right_eye_right = landmark_to_pixel(
                landmarks[263], frame.shape[1], frame.shape[0]
            )
            right_top = landmark_to_pixel(
                landmarks[386], frame.shape[1], frame.shape[0]
            )
            right_bottom = landmark_to_pixel(
                landmarks[374], frame.shape[1], frame.shape[0]
            )

            right_gaze_x, right_gaze_y = get_gaze(
                right_iris,
                right_eye_left,
                right_eye_right,
                right_top,
                right_bottom
            )
            right_gaze_x = max(0.0, min(1.0, 1.0 - right_gaze_x))
            right_gaze_y = max(0.0, min(1.0, 1.0 - right_gaze_y))
            collected.append((right_gaze_x, right_gaze_y))

        if collected:
            avg_x = sum(x for x, _ in collected) / len(collected)
            avg_y = sum(y for _, y in collected) / len(collected)
            samples.append(((avg_x, avg_y), (target_x, target_y)))

    if samples:
        print("Calibration complete. Mapping created.")
        if verbose:
            print(f"Calibration samples: {samples}")
    else:
        print("Calibration failed: no suitable gaze samples were collected.")

    return samples
