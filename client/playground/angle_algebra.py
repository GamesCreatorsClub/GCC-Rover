
from  wheels_service import smallestAngleChange


def test(old_angle_mod, new_angle, expected_angle_mod):
    res = smallestAngleChange(old_angle_mod[0], old_angle_mod[1], new_angle)

    if res != expected_angle_mod:
        print("Expected (" + str(old_angle_mod[0]) + ", " + str(old_angle_mod[1]) + ") • " + str(new_angle) + " -> (" + str(expected_angle_mod[0]) + ", " + str(expected_angle_mod[1]) + ")")
        print("But got  (" + str(old_angle_mod[0]) + ", " + str(old_angle_mod[1]) + ") • " + str(new_angle) + " -> (" + str(res[0]) + ", " + str(res[1]) + ")")
        raise AssertionError


test((0, 1), 0, (0, 1))
test((0, 1), 45, (45, 1))
test((45, 1), 0, (0, 1))

test((45, 1), 270, (90, -1))
test((45, -1), 270, (90, -1))
test((270, 1), 45, (225, -1))
test((270, -1), 45, (225, -1))

test((315, -1), 130, (310, -1))
test((315, -1), 135, (315, -1))
test((315, -1), 140, (320, -1))

test((315, 1), 130, (310, -1))
test((315, 1), 135, (315, -1))
test((315, 1), 140, (320, -1))

test((130, -1), 315, (135, -1))
test((135, -1), 315, (135, -1))
test((140, -1), 315, (135, -1))

test((130, 1), 315, (135, -1))
test((135, 1), 315, (135, -1))
test((140, 1), 315, (135, -1))

test((315, 1), 270, (270, 1))
test((315, 1), 90, (270, -1))
test((315, -1), 270, (270, 1))
test((315, -1), 90, (270, -1))

test((315, 1), 45, (45, 1))
test((315, -1), 45, (225, -1))
