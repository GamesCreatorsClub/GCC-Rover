package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.ControllerInterface;
import org.ah.gcc.rover.controllers.JoystickState;

public class RoverDriver {

    private RoverHandler roverHandler;
    private ControllerInterface controllerInterface;

    private Exponent rightExpo;
    private Exponent leftExpo;
    private int roverSpeed;

    private JoystickState leftjoystick;
    private JoystickState rightjoystick;
    private int roverTurningDistance;

    private boolean switchLB;


    public RoverDriver(RoverHandler roverHandler, ControllerInterface controllerInterface) {
        this.roverHandler = roverHandler;
        this.controllerInterface = controllerInterface;


        rightExpo = new Exponent();
        leftExpo = new Exponent();

        rightjoystick = new JoystickState(0, 0);
        leftjoystick = new JoystickState(0, 0);

    }

    public RoverHandler getRoverHandler() {
        return roverHandler;
    }

    public void setRoverHandler(RoverHandler roverHandler) {
        this.roverHandler = roverHandler;
    }

    public ControllerInterface getControllerInterface() {
        return controllerInterface;
    }

    public void setControllerInterface(ControllerInterface controllerInterface) {
        this.controllerInterface = controllerInterface;
    }

    public void processJoysticks() {
        if (leftjoystick.getDistanceFromCentre() < 0.1f && rightjoystick.getDistanceFromCentre() > 0.1f) {
            if (switchLB) {
                float distance = rightjoystick.getDistanceFromCentre();
                rightExpo.setValue(distance);

                rightExpo.setValue(distance);
                distance = leftExpo.calculate(distance);

                roverSpeed = calcRoverSpeed(distance);
                roverHandler.publish("move/drive", String.format("%.2f %.0f", rightjoystick.getAngleFromCentre(), (float)(roverSpeed)));
            } else {
                roverSpeed = calcRoverSpeed(rightjoystick.getDistanceFromCentre());
                roverHandler.publish("move/orbit", roverSpeed + "");
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
            roverHandler.publish("move/steer", roverTurningDistance + " " + roverSpeed);
        } else if (leftjoystick.getDistanceFromCentre() > 0.1f) {
            float leftX = leftjoystick.getX();
            leftExpo.setValue(leftX);
            leftX = leftExpo.calculate(leftX);
            roverSpeed = calcRoverSpeed(leftX) / 4;
            roverHandler.publish("move/rotate", Integer.toString(roverSpeed));
        } else {
            roverHandler.publish("move/drive", rightjoystick.getAngleFromCentre() + " 0");
            roverSpeed = 0;
            roverHandler.publish("move/stop", "0");
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

}
