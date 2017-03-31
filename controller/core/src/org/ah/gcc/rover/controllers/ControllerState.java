/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.controllers;

public interface ControllerState {

    enum ButtonType {
        ORBIT_BUTTON,
        KICK_BUTTON,
        BOOST_BUTTON,
        LOCK_AXIS_BUTTON,
        READ_DISTANCE_BUTTON,
        SLING_SHOT_BUTTON,
        SELECT_BUTTON,
        SPEED_UP_BUTTON,
        SPEED_DOWN_BUTTON
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
