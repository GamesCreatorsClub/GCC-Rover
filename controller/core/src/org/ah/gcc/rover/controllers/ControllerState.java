package org.ah.gcc.rover.controllers;

public interface ControllerState {

    public float getX1();
    public float getY1();

    public float getX2();
    public float getY2();

    public float getX3();
    public float getY3();

    public boolean getButton(int id);

}
