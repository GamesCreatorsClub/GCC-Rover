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

    private double calcAngleAtPointFromCentre(float x, float y) {
        return Math.atan2(x, -y) * 180 / Math.PI;
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

    public JoystickState set(JoystickState state) {
        setX(state.x);
        setY(state.y);
        return state;
    }

    @Override
    public String toString() {
        return "(" + x + ", " + y + ")";
    }
}
