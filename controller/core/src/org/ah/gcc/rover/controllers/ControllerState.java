package org.ah.gcc.rover.controllers;

public interface ControllerState {

    JoystickState getLeft();
    JoystickState getRight();
    JoystickState getHat();

    float getX1();
    float getY1();

    float getX2();
    float getY2();

    float getX3();
    float getY3();

    boolean getButton(int id);

}
