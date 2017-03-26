package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.ControllerInterface;
import org.ah.gcc.rover.controllers.ControllerListener;
import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.ControllerState.ButtonType;
import org.ah.gcc.rover.controllers.JoystickState;

public class RoverDriver implements ControllerListener {

    private RoverHandler roverControl;
    private ControllerInterface controllerInterface;

    private Exponent rightExpo;
    private Exponent leftExpo;
    private int roverSpeed;

    private JoystickState leftjoystick;
    private JoystickState rightjoystick;
    private JoystickState hat1;

    private int roverTurningDistance;

    private boolean[] buttons = new boolean[ButtonType.values().length];
    private boolean[] prevButtons = new boolean[ButtonType.values().length];

    public RoverDriver(RoverHandler roverControl, ControllerInterface controllerInterface) {
        this.roverControl = roverControl;
        this.controllerInterface = controllerInterface;
        controllerInterface.addListener(this);

        rightExpo = new Exponent();
        leftExpo = new Exponent();

        rightjoystick = new JoystickState(0, 0);
        leftjoystick = new JoystickState(0, 0);
        hat1 = new JoystickState(0, 0);

        controllerInterface.addListener(this);
    }

    public void setRover(RoverHandler roverHandler) {
        this.roverControl = roverHandler;
    }

    public ControllerInterface getControllerInterface() {
        return controllerInterface;
    }

    public void setControllerInterface(ControllerInterface controllerInterface) {
        this.controllerInterface = controllerInterface;
    }

    public void processJoysticks() {
        if (leftjoystick.getDistanceFromCentre() < 0.1f && rightjoystick.getDistanceFromCentre() > 0.1f) {
            if (!buttons[ButtonType.ORBIT_BUTTON.ordinal()]) {
                float distance = rightjoystick.getDistanceFromCentre();
                rightExpo.setValue(distance);

                distance = rightExpo.calculate(distance);

                roverSpeed = calcRoverSpeed(distance);
                roverControl.publish("move/drive", String.format("%.2f %.0f", rightjoystick.getAngleFromCentre(), (float)(roverSpeed)));
            } else {

                float distance = rightjoystick.getX();
                rightExpo.setValue(distance);
                distance = rightExpo.calculate(distance);

                roverSpeed = calcRoverSpeed(distance);
                roverControl.publish("move/orbit",  "150 " + roverSpeed);
            }
        } else if (leftjoystick.getDistanceFromCentre() > 0.1f && rightjoystick.getDistanceFromCentre() > 0.1f) {
            float rightY = rightjoystick.getY();
            float leftX = leftjoystick.getX();

            rightExpo.setValue(rightY);
            rightY = rightExpo.calculate(rightY);

            leftExpo.setValue(leftX);
            leftX = leftExpo.calculate(leftX);

            roverSpeed = -calcRoverSpeed(rightY);
            roverTurningDistance = calcRoverDistance(leftX);
            roverControl.publish("move/steer", roverTurningDistance + " " + roverSpeed);
        } else if (leftjoystick.getDistanceFromCentre() > 0.1f) {
            float leftX = leftjoystick.getX();
            leftExpo.setValue(leftX);
            leftX = leftExpo.calculate(leftX);
            roverSpeed = calcRoverSpeed(leftX) / 4;
            roverControl.publish("move/rotate", Integer.toString(roverSpeed));
        } else {
            roverControl.publish("move/drive", rightjoystick.getAngleFromCentre() + " 0");
            roverSpeed = 0;
            roverControl.publish("move/stop", "0");
        }
    }

    private int calcRoverSpeed(float speed) {
        return (int)(speed * 150);
    }

    private int calcRoverDistance(float distance) {
        if (distance >= 0) {
            distance = Math.abs(distance);
            distance = 1.0f - distance;
            distance = distance + 0.2f;
            distance = distance * 500f;
        } else {
            distance = Math.abs(distance);
            distance = 1.0f - distance;
            distance = distance + 0.2f;
            distance = - distance * 500f;
        }

        return (int)distance;
    }

    @Override
    public void controllerUpdate(ControllerState state) {
//        System.out.println("state: " + state);

        for (int i = 0; i < buttons.length; i++) {
            prevButtons[i] = buttons[i];
        }

        for (ButtonType buttonType : ButtonType.values()) {
            buttons[buttonType.ordinal()] = state.getButton(buttonType);
        }

        leftjoystick.set(state.getLeft());
        rightjoystick.set(state.getRight());
        hat1.set(state.getHat());
    }
}
