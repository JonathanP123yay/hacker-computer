import cv2
import os
import time

# --------------------------------------------------
# Settings
# --------------------------------------------------

CAMERA_INDEX = 0

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "face_detection_yunet_2023mar.onnx"
)

CONFIDENCE_THRESHOLD = 0.7
NMS_THRESHOLD = 0.3
TOP_K = 5000

# --------------------------------------------------
# Check OpenCV
# --------------------------------------------------

print("OpenCV version:", cv2.__version__)

if not hasattr(cv2, "FaceDetectorYN"):
    print("ERROR: FaceDetectorYN is not available in this OpenCV installation.")
    print("Your OpenCV installation may be incomplete.")
    exit()

# --------------------------------------------------
# Check model
# --------------------------------------------------

if not os.path.exists(MODEL_PATH):
    print("ERROR: YuNet model was not found.")
    print()
    print("Expected model:")
    print(MODEL_PATH)
    print()
    print("Download it with:")
    print(
        'Invoke-WebRequest -Uri '
        '"https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" '
        '-OutFile "face_detection_yunet_2023mar.onnx"'
    )
    exit()

# --------------------------------------------------
# Open webcam
# --------------------------------------------------

camera = cv2.VideoCapture(CAMERA_INDEX)

if not camera.isOpened():
    print("ERROR: Could not access the camera.")
    print("Try changing CAMERA_INDEX from 0 to 1.")
    exit()

# Try to use a reasonable camera resolution
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# --------------------------------------------------
# Get actual camera resolution
# --------------------------------------------------

width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Camera resolution: {width}x{height}")

# --------------------------------------------------
# Create YuNet face detector
# --------------------------------------------------

detector = cv2.FaceDetectorYN.create(
    MODEL_PATH,
    "",
    (width, height),
    CONFIDENCE_THRESHOLD,
    NMS_THRESHOLD,
    TOP_K
)

# --------------------------------------------------
# FPS tracking
# --------------------------------------------------

previous_time = time.perf_counter()

print()
print("Camera started.")
print("Face tracking is active.")
print("Press Q to quit.")
print()

# --------------------------------------------------
# Main loop
# --------------------------------------------------

while True:

    # Read camera frame
    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera frame.")
        break

    # Update detector input size
    detector.setInputSize((frame.shape[1], frame.shape[0]))

    # Detect faces
    _, faces = detector.detect(frame)

    # Number of detected faces
    face_count = 0

    if faces is not None:

        face_count = len(faces)

        for face in faces:

            # --------------------------------------------------
            # Face bounding box
            # --------------------------------------------------

            x = int(face[0])
            y = int(face[1])
            w = int(face[2])
            h = int(face[3])

            # Make sure coordinates stay inside the image
            x = max(0, x)
            y = max(0, y)

            w = min(w, frame.shape[1] - x)
            h = min(h, frame.shape[0] - y)

            # --------------------------------------------------
            # Face center
            # --------------------------------------------------

            center_x = x + w // 2
            center_y = y + h // 2

            # --------------------------------------------------
            # Confidence
            # --------------------------------------------------

            confidence = float(face[14])

            # --------------------------------------------------
            # Draw face box
            # --------------------------------------------------

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            # --------------------------------------------------
            # Draw center point
            # --------------------------------------------------

            cv2.circle(
                frame,
                (center_x, center_y),
                6,
                (0, 0, 255),
                -1
            )

            # --------------------------------------------------
            # Draw face center lines
            # --------------------------------------------------

            cv2.line(
                frame,
                (center_x, y),
                (center_x, y + h),
                (0, 0, 255),
                1
            )

            cv2.line(
                frame,
                (x, center_y),
                (x + w, center_y),
                (0, 0, 255),
                1
            )

            # --------------------------------------------------
            # Display position
            # --------------------------------------------------

            position_text = f"X: {center_x}  Y: {center_y}"

            cv2.putText(
                frame,
                position_text,
                (x, max(25, y - 35)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2
            )

            # --------------------------------------------------
            # Display confidence
            # --------------------------------------------------

            confidence_text = f"Confidence: {confidence:.2f}"

            cv2.putText(
                frame,
                confidence_text,
                (x, max(50, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2
            )

            # --------------------------------------------------
            # Draw facial landmarks
            # --------------------------------------------------

            # Right eye
            right_eye_x = int(face[4])
            right_eye_y = int(face[5])

            # Left eye
            left_eye_x = int(face[6])
            left_eye_y = int(face[7])

            # Nose
            nose_x = int(face[8])
            nose_y = int(face[9])

            # Right side of mouth
            mouth_right_x = int(face[10])
            mouth_right_y = int(face[11])

            # Left side of mouth
            mouth_left_x = int(face[12])
            mouth_left_y = int(face[13])

            # Draw landmarks
            cv2.circle(
                frame,
                (right_eye_x, right_eye_y),
                4,
                (255, 0, 0),
                -1
            )

            cv2.circle(
                frame,
                (left_eye_x, left_eye_y),
                4,
                (255, 0, 0),
                -1
            )

            cv2.circle(
                frame,
                (nose_x, nose_y),
                4,
                (0, 255, 255),
                -1
            )

            cv2.circle(
                frame,
                (mouth_right_x, mouth_right_y),
                4,
                (255, 0, 255),
                -1
            )

            cv2.circle(
                frame,
                (mouth_left_x, mouth_left_y),
                4,
                (255, 0, 255),
                -1
            )

    # --------------------------------------------------
    # FPS calculation
    # --------------------------------------------------

    current_time = time.perf_counter()

    elapsed = current_time - previous_time

    if elapsed > 0:
        fps = 1.0 / elapsed
    else:
        fps = 0

    previous_time = current_time

    # --------------------------------------------------
    # Information panel
    # --------------------------------------------------

    cv2.putText(
        frame,
        f"Faces: {face_count}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    # --------------------------------------------------
    # Show camera
    # --------------------------------------------------

    cv2.imshow("OpenCV 5 Face Tracking", frame)

    # --------------------------------------------------
    # Quit with Q
    # --------------------------------------------------

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

# --------------------------------------------------
# Cleanup
# --------------------------------------------------

camera.release()
cv2.destroyAllWindows()

print("Camera stopped.")