/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.controllers;

public class ControllerStateImplementation implements ControllerState {

    private boolean[] buttons = new boolean[ButtonType.values().length];
    private JoystickState hat1;
    private JoystickState joy2;
    private JoystickState joy1;

    public ControllerStateImplementation() {
        init(new JoystickState(0, 0), new JoystickState(0, 0), new JoystickState(0, 0));
    }

    public void init(JoystickState joy1, JoystickState joy2, JoystickState hat1) {

        this.joy1 = joy1;
        this.joy2 = joy2;
        this.hat1 = hat1;

        for (int i = 0; i < buttons.length; i++) {
            buttons[i] = false;
        }
    }


    @Override
    public JoystickState getLeft() {
        return joy1;
    }
    @Override
    public JoystickState getRight() {
        return joy2;
    }
    @Override
    public JoystickState getHat() {
        return hat1;
    }

    @Override
    public float getX1() {
        return joy1.getX();
    }

    @Override
    public float getY1() {
        return joy1.getY();
    }

    @Override
    public float getX2() {
        return joy2.getX();
    }

    @Override
    public float getY2() {
        return joy2.getY();
    }

    @Override
    public float getX3() {
        return hat1.getX();
    }

    @Override
    public float getY3() {
        return hat1.getY();
    }

    public void setX1(float v) {
        joy1.setX(fixZero(v));
    }

    public void setY1(float v) {
        joy1.setY(fixZero(v));
    }

    public void setX2(float v) {
        joy2.setX(fixZero(v));
    }

    public void setY2(float v) {
        joy2.setY(fixZero(v));
    }

    public void setX3(float v) {
        hat1.setX(fixZero(v));
    }

    public void setY3(float v) {
        hat1.setY(fixZero(v));
    }

    @Override
    public boolean getButton(ButtonType buttonType) {
        return buttons[buttonType.ordinal()];
    }

    public void setButton(ButtonType buttonType, boolean state) {
        buttons[buttonType.ordinal()] = state;
    }

    public JoystickState getJoy2() {
        return joy2;
    }

    public void setJoy2(JoystickState joy2) {
        this.joy2 = joy2;
    }

    public JoystickState getJoy1() {
        return joy1;
    }

    public void setJoy1(JoystickState joy1) {
        this.joy1 = joy1;
    }

    public JoystickState getHat1() {
        return hat1;
    }

    public void setHat1(JoystickState hat1) {
        this.hat1 = hat1;
    }

    public String toString() {
        return "Left: " + getLeft().toString() + " Right: " + getRight().toString() + "  Buttons: " + buttons.toString();
    }

    private float fixZero(float v) {
        if (Math.abs(v) < 0.01f) {
            return 0f;
        }
        return v;
    }
}
