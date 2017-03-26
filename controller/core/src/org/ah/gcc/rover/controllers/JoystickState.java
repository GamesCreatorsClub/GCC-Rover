package org.ah.gcc.rover.controllers;

public class JoystickState {
    private float x;
    private float y;

    public JoystickState(float x, float y) {
        this.x = x;
        this.y = y;
    }

    public float getDistanceFromCentre() {
        return (float) Math.sqrt((x*x) + (y*y));
    }

    public double getAngleFromCentre() {
        return calcAngleAtPointFromCentre(x, y);
    }

    private double calcAngleAtPointFromCentre(float x2, float y2) {
        return Math.atan2((x2 - 0), -(y2 - 0));
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
