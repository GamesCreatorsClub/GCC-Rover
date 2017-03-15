package org.ah.gcc.rover.controllers;

public class ControllerStateImplementation implements ControllerState {

    private boolean[] buttons;
    private JoystickState hat1;
    private JoystickState joy2;
    private JoystickState joy1;

    public ControllerStateImplementation() {
        init(new JoystickState(0, 0), new JoystickState(0, 0), new JoystickState(0, 0), new boolean[12]);
    }

    public void init(JoystickState joy1, JoystickState joy2, JoystickState hat1, boolean[] buttons) {

        this.joy1 = joy1;
        this.joy2 = joy2;
        this.hat1 = hat1;
        this.buttons = buttons;

        for (int i = 0; i < 12; i++) {
            buttons[i] = false;
        }
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
        joy1.setX(v);
    }

    public void setY1(float v) {
        joy1.setY(v);
    }

    public void setX2(float v) {
        joy2.setX(v);
    }

    public void setY2(float v) {
        joy2.setY(v);
    }

    public void setX3(float v) {
        hat1.setX(v);
    }

    public void setY3(float v) {
        hat1.setY(v);
    }

    @Override
    public boolean getButton(int id) {

        return buttons[id];
    }

    public void setButton(int id, boolean state) {
        buttons[id] = state;
    }

    public boolean[] getButtons() {
        return buttons;
    }

    public void setButtons(boolean[] buttons) {
        this.buttons = buttons;
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

}
