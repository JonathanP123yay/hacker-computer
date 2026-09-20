import math


def landmark_to_pixel(landmark, width, height):
    x = int(landmark.x * width)
    y = int(landmark.y * height)
    return x, y


def distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2
    )


def average_points(points):
    if not points:
        return 0, 0

    x = sum(point[0] for point in points) / len(points)
    y = sum(point[1] for point in points) / len(points)

    return int(x), int(y)


def get_gaze(iris, left_corner, right_corner, top, bottom):
    eye_width = distance(left_corner, right_corner)
    eye_height = distance(top, bottom)

    if eye_width == 0 or eye_height == 0:
        return 0.5, 0.5

    horizontal = distance(left_corner, iris) / eye_width
    vertical = distance(top, iris) / eye_height

    horizontal = max(0.0, min(1.0, horizontal))
    vertical = max(0.0, min(1.0, vertical))

    return horizontal, vertical


def get_blink_ratio(left_corner, right_corner, top1, bottom1, top2, bottom2):
    eye_width = distance(left_corner, right_corner)

    if eye_width == 0:
        return 0

    vertical1 = distance(top1, bottom1)
    vertical2 = distance(top2, bottom2)
    vertical = (vertical1 + vertical2) / 2

    return vertical / eye_width


def interpolate_mapping(value, mapping):
    if len(mapping) == 0:
        return 0.5
    if len(mapping) == 1:
        return mapping[0][1]

    mapping = sorted(mapping, key=lambda item: item[0])

    if value <= mapping[0][0]:
        return mapping[0][1]
    if value >= mapping[-1][0]:
        return mapping[-1][1]

    for i in range(len(mapping) - 1):
        x1, y1 = mapping[i]
        x2, y2 = mapping[i + 1]
        if x1 <= value <= x2:
            if x2 == x1:
                return y1
            fraction = (value - x1) / (x2 - x1)
            return y1 + fraction * (y2 - y1)

    return mapping[-1][1]
