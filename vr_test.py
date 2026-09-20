import openvr
import time

openvr.init(openvr.VRApplication_Other)

system = openvr.VRSystem()

print("SteamVR connected.")
print("Move your controllers around.")
print("Press Ctrl+C to stop.")
print()

try:
    while True:
        poses = system.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseStanding,
            0,
            openvr.k_unMaxTrackedDeviceCount
        )

        for device_index in range(openvr.k_unMaxTrackedDeviceCount):

            if not system.isTrackedDeviceConnected(device_index):
                continue

            device_class = system.getTrackedDeviceClass(device_index)

            if device_class != openvr.TrackedDeviceClass_Controller:
                continue

            pose = poses[device_index]

            if not pose.bPoseIsValid:
                continue

            # Determine controller side
            role = system.getControllerRoleForTrackedDeviceIndex(
                device_index
            )

            if role == openvr.TrackedControllerRole_LeftHand:
                name = "LEFT"

            elif role == openvr.TrackedControllerRole_RightHand:
                name = "RIGHT"

            else:
                name = "UNKNOWN"

            # Get position
            matrix = pose.mDeviceToAbsoluteTracking

            x = matrix[0][3]
            y = matrix[1][3]
            z = matrix[2][3]

            print(
                f"{name} controller | "
                f"X: {x:.3f} "
                f"Y: {y:.3f} "
                f"Z: {z:.3f}"
            )

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    openvr.shutdown()