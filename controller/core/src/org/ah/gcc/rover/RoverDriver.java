package org.ah.gcc.rover;

import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.beans.PropertyChangeSupport;
import java.util.ArrayList;
import java.util.List;

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

    private JoystickState hat1;
    private JoystickState lasthat1;

    private JoystickAdapter leftJoystick = new JoystickAdapter();
    private JoystickAdapter rightJoystick = new JoystickAdapter();

    private int roverTurningDistance;

    private int roverSpeedMultiplier = 40;

    private boolean[] buttons = new boolean[ButtonType.values().length];
    private boolean[] prevButtons = new boolean[ButtonType.values().length];

    private StringValueAdapter readDistanceValue = new StringValueAdapter("distance");
    private StringValueAdapter roverSpeedValue = new StringValueAdapter("speed");

    private float readDistance = 0f;
    private long timeWhenReadDistance = 0;

    public RoverDriver(RoverHandler roverControl, ControllerInterface controllerInterface) {
        this.roverControl = roverControl;
        this.controllerInterface = controllerInterface;
        controllerInterface.addListener(this);

        rightExpo = new Exponent();
        leftExpo = new Exponent();

        hat1 = new JoystickState(0, 0);
        lasthat1 = new JoystickState(0, 0);

        controllerInterface.addListener(this);
        roverControl.subscribe("sensor/distance", new RoverMessageListener() {
            @Override public void onMessage(String topic, String message) {
                String[] splitMessage = message.split(",")[0].split(":");

                readDistance = Float.parseFloat(splitMessage[1]);
                timeWhenReadDistance = System.currentTimeMillis();

                readDistanceValue.setValue(String.format("%.2f", readDistance));
            }
        });
        readDistanceValue.setValue(Integer.toString(roverSpeedMultiplier));
    }

    public JoystickAdapter getLeftJoystick() {
        return leftJoystick;
    }

    public JoystickAdapter getRightJoystick() {
        return rightJoystick;
    }

    public StringValueAdapter getReadDistanceValue() {
        return readDistanceValue;
    }

    public StringValueAdapter getRoverSpeedValue() {
        return roverSpeedValue;
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
        divider++;

        JoystickState leftJoystickState = leftJoystick.getState();
        JoystickState rightJoystickState = rightJoystick.getState();

        if (buttons[ButtonType.KICK_BUTTON.ordinal()]) {
            roverControl.publish("servo/9", "90");
        } else {
            roverControl.publish("servo/9", "145");
        }

        if (leftJoystickState.getDistanceFromCentre() < 0.1f && rightJoystickState.getDistanceFromCentre() > 0.1f) {
            if (!buttons[ButtonType.ORBIT_BUTTON.ordinal()]) {
                float distance = rightJoystickState.getDistanceFromCentre();
                rightExpo.setValue(distance);

                distance = rightExpo.calculate(distance);

                roverSpeed = calcRoverSpeed(distance);
                if (!buttons[ButtonType.LOCK_AXIS_BUTTON.ordinal()]) {
                    roverControl.publish("move/drive", String.format("%.2f %.0f", rightJoystickState.getAngleFromCentre(), (float)(roverSpeed)));
                } else {
                    roverControl.publish("move/drive", "0.0 " + (float)(roverSpeed));
                }
            } else {
                float orbitDistance = 150;
                if (System.currentTimeMillis() - timeWhenReadDistance < 2000) {
                    orbitDistance = readDistance + 100;
                }

                float distance = rightJoystickState.getX();
                rightExpo.setValue(distance);
                distance = rightExpo.calculate(distance);

                roverSpeed = calcRoverSpeed(distance);
                roverControl.publish("move/orbit",  (int)orbitDistance + " " + roverSpeed);
            }
        } else if (leftJoystickState.getDistanceFromCentre() > 0.1f && rightJoystickState.getDistanceFromCentre() > 0.1f) {
            float rightY = rightJoystickState.getY();
            float leftX = leftJoystickState.getX();

            rightExpo.setValue(rightY);
            rightY = rightExpo.calculate(rightY);

            leftExpo.setValue(leftX);
            leftX = leftExpo.calculate(leftX);

            roverSpeed = -calcRoverSpeed(rightY);
            roverTurningDistance = calcRoverDistance(leftX);
            roverControl.publish("move/steer", roverTurningDistance + " " + roverSpeed);
        } else if (leftJoystickState.getDistanceFromCentre() > 0.1f) {
            float leftX = leftJoystickState.getX();
            leftExpo.setValue(leftX);
            leftX = leftExpo.calculate(leftX);
            roverSpeed = calcRoverSpeed(leftX) / 4;
            roverControl.publish("move/rotate", Integer.toString(roverSpeed));
        } else {
            roverControl.publish("move/drive", rightJoystickState.getAngleFromCentre() + " 0");
            roverSpeed = 0;
            roverControl.publish("move/stop", "0");
        }
        if (buttons[ButtonType.ORBIT_BUTTON.ordinal()] && divider % 10 == 0) {
            roverControl.publish("sensor/distance/read", "0");
        }

        if (buttons[ButtonType.SPEED_UP_BUTTON.ordinal()] && !prevButtons[ButtonType.SPEED_UP_BUTTON.ordinal()]) {
            if (roverSpeedMultiplier < 10) {
                roverSpeedMultiplier += 1;
            } else if (roverSpeedMultiplier < 50) {
                roverSpeedMultiplier += 5;
            } else if (roverSpeedMultiplier < 300) {
                roverSpeedMultiplier += 10;
            }
            roverSpeedValue.setValue(Integer.toString(roverSpeedMultiplier));
        }

        if (buttons[ButtonType.SPEED_DOWN_BUTTON.ordinal()] && !prevButtons[ButtonType.SPEED_DOWN_BUTTON.ordinal()]) {
            if (roverSpeedMultiplier > 50) {
                roverSpeedMultiplier -= 10;
            } else if (roverSpeedMultiplier < 10) {
                roverSpeedMultiplier -= 5;
            } else if (roverSpeedMultiplier < 0) {
                roverSpeedMultiplier -= 1;
            }
            roverSpeedValue.setValue(Integer.toString(roverSpeedMultiplier));
        }

        for (int i = 0; i < buttons.length; i++) {
            prevButtons[i] = buttons[i];
        }
    }

    private int calcRoverSpeed(float speed) {
        if (buttons[ButtonType.BOOST_BUTTON.ordinal()]) {
            return (int) (speed * 300);
        } else {
            return (int) (speed * roverSpeedMultiplier);
        }
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
        // System.out.println("state: " + state);

        for (ButtonType buttonType : ButtonType.values()) {
            buttons[buttonType.ordinal()] = state.getButton(buttonType);
        }

        lasthat1.set(hat1);

        leftJoystick.update(state.getLeft());
        rightJoystick.update(state.getRight());
        hat1.set(state.getHat());
    }

    public int getRoverSpeedMultiplier() {
        return roverSpeedMultiplier;
    }

    public void setRoverSpeedMultiplier(int roverSpeedMultiplier) {
        this.roverSpeedMultiplier = roverSpeedMultiplier;
    }

    public static class JoystickAdapter {
        private List<JoystickComponentListener> listeners = new ArrayList<JoystickComponentListener>();
        private JoystickState state = new JoystickState(0f, 0f);

        public JoystickAdapter() { }

        public JoystickState getState() {
            return state;
        }

        public void update(JoystickState state) {
            if (this.state.set(state)) {
                fireEvent();
            }
        }

        public void fireEvent() {
            for (JoystickComponentListener listener : listeners) {
                listener.changed(getState());
            }
        }

        public void addListener(JoystickComponentListener listener) {
            listeners.add(listener);
        }

        public void removeListener(JoystickComponentListener listener) {
            listeners.remove(listener);
        }
    }

    public static class StringValueAdapter {
        private PropertyChangeSupport propertyChangeSupport = new PropertyChangeSupport(this);

        private String propertyName = "";
        private String value = "";

        public StringValueAdapter(String propertyName) {
            this.propertyName = propertyName;
        }

        public void setValue(String value) {
            if (!value.equals(this.value)) {
                propertyChangeSupport.firePropertyChange(propertyName, this.value, value);
            }
            this.value = value;
        }

        public void addListener(PropertyChangeListener listener) {
            propertyChangeSupport.addPropertyChangeListener(listener);
            listener.propertyChange(new PropertyChangeEvent(this, propertyName, "", value));
        }

        public void removeListener(PropertyChangeListener listener) {
            propertyChangeSupport.removePropertyChangeListener(listener);
        }
    }
}
