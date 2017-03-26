package org.ah.gcc.rover;

import org.ah.gcc.rover.RoverHandler.RoverMessageListener;
import org.ah.gcc.rover.controllers.ControllerInterface;
import org.ah.gcc.rover.controllers.ControllerListener;
import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.ControllerState.ButtonType;
import org.ah.gcc.rover.controllers.JoystickState;

public class RoverDriver implements ControllerListener {

    private int divider = 0;

    private RoverHandler roverControl;
    private ControllerInterface controllerInterface;

    private Exponent rightExpo;
    private Exponent leftExpo;
    private int roverSpeed;

    private JoystickState leftjoystick;
    private JoystickState rightjoystick;
    private JoystickState hat1;

    private int roverTurningDistance;

    private int roverSpeedMultiplier = 150;
    private boolean[] buttons = new boolean[ButtonType.values().length];
    private boolean[] prevButtons = new boolean[ButtonType.values().length];

    private float readDistance = 0f;
    private long timeWhenReadDistance = 0;

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
        roverControl.subscribe("sensor/distance", new RoverMessageListener() {
            @Override public void onMessage(String topic, String message) {
                String[] splitMessage = message.split(",")[0].split(":");

                readDistance = Float.parseFloat(splitMessage[1]);
                timeWhenReadDistance = System.currentTimeMillis();
                System.out.println("Got distance " + message);
            }
        });
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
<<<<<<< HEAD
        divider++;
=======
        if (buttons[ButtonType.KICK_BUTTON.ordinal()]) {
            roverControl.publish("servo/9", "90");
        } else {
            roverControl.publish("servo/9", "145");
        }

>>>>>>> Addes speed and boost
        if (leftjoystick.getDistanceFromCentre() < 0.1f && rightjoystick.getDistanceFromCentre() > 0.1f) {
            if (!buttons[ButtonType.ORBIT_BUTTON.ordinal()]) {
                float distance = rightjoystick.getDistanceFromCentre();
                rightExpo.setValue(distance);

                distance = rightExpo.calculate(distance);

                roverSpeed = calcRoverSpeed(distance);
                roverControl.publish("move/drive", String.format("%.2f %.0f", rightjoystick.getAngleFromCentre(), (float)(roverSpeed)));
            } else {
                System.out.println("In orbit");
                float orbitDistance = 150;
                if (System.currentTimeMillis() - timeWhenReadDistance < 2000) {
                    orbitDistance = readDistance + 100;
                }

                float distance = rightjoystick.getX();
                rightExpo.setValue(distance);
                distance = rightExpo.calculate(distance);

                roverSpeed = calcRoverSpeed(distance);
                roverControl.publish("move/orbit",  (int)orbitDistance + " " + roverSpeed);
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
        if (buttons[ButtonType.ORBIT_BUTTON.ordinal()] && divider % 10 == 0) {
            roverControl.publish("sensor/distance/read", "0");
        }

        if (hat1.getX() > 0 && lasthat1.getX() <= 0) {
            roverSpeedMultiplier += 10;
        }

        if (hat1.getX() < 0 && lasthat1.getX() >= 0) {
            roverSpeedMultiplier -= 10;
        }

        if (buttons[ButtonType.BOOST_BUTTON.ordinal()]) {
            roverSpeedMultiplier = 150;
        } else {
            roverSpeedMultiplier = 30;
        }

        System.out.println("Speed: " + roverSpeedMultiplier);
    }

    private int calcRoverSpeed(float speed) {
        return (int) (speed * roverSpeedMultiplier);
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

    public int getRoverSpeedMultiplier() {
        return roverSpeedMultiplier;
    }

    public void setRoverSpeedMultiplier(int roverSpeedMultiplier) {
        this.roverSpeedMultiplier = roverSpeedMultiplier;
    }
}
