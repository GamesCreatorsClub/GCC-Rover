package org.ah.gcc.rover.controllers;

public interface ControllerState {

    enum ButtonType {
        ORBIT_BUTTON,
        KICK_BUTTON,
        BOOST_BUTTON,
        LOCK_AXIS_BUTTON,
        READ_DISTANCE_BUTTON,
        SLING_SHOT_BUTTON,
        SELECT_BUTTON
    };

    JoystickState getLeft();
    JoystickState getRight();
    JoystickState getHat();

    float getX1();
    float getY1();

    float getX2();
    float getY2();

    float getX3();
    float getY3();

    boolean getButton(ButtonType buttonType);
}
