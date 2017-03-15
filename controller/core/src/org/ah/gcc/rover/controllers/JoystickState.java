package org.ah.gcc.rover.controllers;

public class JoystickState {
    private float x;
    private float y;

    public JoystickState(float x, float y) {
        this.x = x;
        this.y = y;

    }

    public float getX() {
        return x;
    }

    public void setX(float x) {
        this.x = x;
    }

    public float getY() {
        return y;
    }

    public void setY(float y) {
        this.y = y;
    }
}
