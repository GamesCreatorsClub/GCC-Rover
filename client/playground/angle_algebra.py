def normaiseAngle(a):
    if a < 0:
        a += 360
    if a >= 360:
        a -= 360
    return a


def angleDiference(a1, a2):
    diff = a1 - a2
    if diff > 180:
        return diff - 360
    elif diff < -180:
        return diff + 360
    else:
        return diff


def addAngles(a1, a2):
    return normaiseAngle(a1 + a2)


def subAngles(a1, a2):
    return normaiseAngle(a1 - a2)


def oppositeAngle(a, mod):
    if mod >= 0:
        return a
    return normaiseAngle(a + 180)


def smallestAngleChange(old_angle, mod, new_angle):
    real_old_angle = oppositeAngle(old_angle, mod)
    angle_diff = angleDiference(real_old_angle, new_angle)
    if angle_diff > 90:
        new_diff = angle_diff - 180
        return normaiseAngle(old_angle + new_diff), -mod
    elif angle_diff < -90:
        new_diff = 180 - angle_diff
        return normaiseAngle(old_angle + new_diff), -mod
    elif mod < 0:
        return normaiseAngle(old_angle + angle_diff), mod
    else:
        return new_angle, mod


new_angle, mod = smallestAngleChange(0, 1, 135)
print(new_angle, mod)

new_angle, mod = smallestAngleChange(315, -1, 135)
print(new_angle, mod)

new_angle, mod = smallestAngleChange(315, -1, 130)
print(new_angle, mod)

new_angle, mod = smallestAngleChange(315, -1, 140)
print(new_angle, mod)

new_angle, mod = smallestAngleChange(315, 1, 130)
print(new_angle, mod)

new_angle, mod = smallestAngleChange(315, 1, 270)
print(new_angle, mod)
