/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.controllers.AbstractController;
import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.ControllerState.ButtonType;
import org.ah.gcc.rover.controllers.ControllerStateImplementation;
import org.ah.gcc.rover.controllers.JoystickState;

import com.badlogic.gdx.controllers.Controller;
import com.badlogic.gdx.controllers.ControllerListener;
import com.badlogic.gdx.controllers.Controllers;
import com.badlogic.gdx.controllers.PovDirection;
import com.badlogic.gdx.math.Vector3;

public class DesktopRealController extends AbstractController implements ControllerListener {

    private ControllerStateImplementation state;

    private boolean speedModifier = false;
    private int lastX = 0;

    public DesktopRealController() {
        state = new ControllerStateImplementation();
        Controllers.addListener(this);
    }

    public DesktopRealController(String name) {
        super(name);
        state = new ControllerStateImplementation();
        Controllers.addListener(this);
    }

    public ControllerState getState() {
        return state;
    }

    public void setState(ControllerStateImplementation state) {
        this.state = state;
    }

    @Override
    public void connected(Controller controller) {
        System.out.println("connected to a controller " + controller);
    }

    @Override
    public void disconnected(Controller controller) {
    }

    @Override
    public boolean buttonDown(Controller controller, int buttonCode) {
        System.out.println("Button down " + buttonCode);

        if (buttonCode == 3) {
            speedModifier = true;
        } else {
            ControllerState.ButtonType buttonType = toButtonType(buttonCode);
            if (buttonType != null) {
                state.setButton(buttonType, true);
                fireEvent(state);
            }
        }
        return true;
    }

    @Override
    public boolean buttonUp(Controller controller, int buttonCode) {
        if (buttonCode == 3) {
            speedModifier = false;
            state.setButton(ButtonType.SPEED_UP_BUTTON, false);
            state.setButton(ButtonType.SPEED_DOWN_BUTTON, false);
            fireEvent(state);
        } else {
            ControllerState.ButtonType buttonType = toButtonType(buttonCode);
            if (buttonType != null) {
                state.setButton(toButtonType(buttonCode), false);
                fireEvent(state);
            }
        }
        return true;
    }

    @Override
    public boolean axisMoved(Controller controller, int axisCode, float value) {
        float oldValue = 0f;
        if (axisCode == 0) {
            if (speedModifier) {
            } else {
                oldValue = state.getX1();
                state.setX1(value);
            }
        } else if (axisCode == 1) {
            if (speedModifier) {
                if (value < -0.1f && lastX >= 0) {
                    System.out.println("SPEED UP   x1 " + value + " lastX1 " + lastX);
                    state.setButton(ButtonType.SPEED_UP_BUTTON, true);
                    state.setButton(ButtonType.SPEED_DOWN_BUTTON, false);
                    lastX = -1;
                    fireEvent(state);
                } else if (value > 0.1f && lastX <= 0) {
                    System.out.println("SPEED DOWN x1 " + value + " lastX1 " + lastX);
                    state.setButton(ButtonType.SPEED_UP_BUTTON, false);
                    state.setButton(ButtonType.SPEED_DOWN_BUTTON, true);
                    lastX = 1;
                    fireEvent(state);
                } else if (Math.abs(value) < 0.1f && lastX != 0) {
                    System.out.println("SPEED ---- x1 " + value + " lastX1 " + lastX);
                    state.setButton(ButtonType.SPEED_UP_BUTTON, false);
                    state.setButton(ButtonType.SPEED_DOWN_BUTTON, false);
                    lastX = 0;
                    fireEvent(state);
                // } else {
                //    System.out.println("----- ---- x1 " + value + " lastX1 " + lastX);
                }
            } else {
                oldValue = state.getY1();
                state.setY1(value);
            }
        } else if (axisCode == 3) {
            oldValue = state.getX2();
            state.setX2(value);
        } else if (axisCode == 4) {
            oldValue = state.getY2();
            state.setY2(value);
        } else if (axisCode == 4) {
            oldValue = state.getY3();
            state.setY3(value);
        } else if (axisCode == 5) {
            oldValue = state.getX3();
            state.setX3(value);
        }

        if (Math.abs(oldValue - value) >= 0.01f) {
            fireEvent(state);
            // System.out.println("new joystick: " + axisCode);

        }



        return false;
    }

    @Override
    public boolean povMoved(Controller controller, int povCode, PovDirection value) {
        // System.out.println("new pov: " + value.toString());
        if (value == PovDirection.center) {
            state.getHat1().set(JoystickState.zero());
        } else if (value == PovDirection.north) {
            state.getHat1().set(0, 1);
        } else if (value == PovDirection.south) {
            state.getHat1().set(0, -1);
        } else if (value == PovDirection.east) {
            state.getHat1().set(1, 0);
        } else if (value == PovDirection.west) {
            state.getHat1().set(-1, 0);
        } else if (value == PovDirection.northEast) {
            state.getHat1().set(1, 1);
        } else if (value == PovDirection.northWest) {
            state.getHat1().set(-1, 1);
        } else if (value == PovDirection.southEast) {
            state.getHat1().set(1, -1);
        } else if (value == PovDirection.southWest) {
            state.getHat1().set(-1, -1);
        }
        return false;
    }

    @Override
    public boolean xSliderMoved(Controller controller, int sliderCode, boolean value) {
        return false;
    }

    @Override
    public boolean ySliderMoved(Controller controller, int sliderCode, boolean value) {
        return false;
    }

    @Override
    public boolean accelerometerMoved(Controller controller, int accelerometerCode, Vector3 value) {
        return false;
    }

    private ControllerState.ButtonType toButtonType(int buttonCode) {
        if (buttonCode == 0) {
            return ButtonType.SLING_SHOT_BUTTON;
        } else if (buttonCode == 1) {
            return ButtonType.READ_DISTANCE_BUTTON;
        } else if (buttonCode == 2) {
        } else if (buttonCode == 3) {
        } else if (buttonCode == 4) {
            return ButtonType.ORBIT_BUTTON;
        } else if (buttonCode == 5) {
            return ButtonType.LOCK_AXIS_BUTTON;
        } else if (buttonCode == 6) {
            return ButtonType.BOOST_BUTTON;
        } else if (buttonCode == 7) {
            return ButtonType.KICK_BUTTON;
        } else if (buttonCode == 8) {
        } else if (buttonCode == 9) {
            return ButtonType.SELECT_BUTTON;
        } else if (buttonCode == 10) {
        } else if (buttonCode == 11) {
        } else if (buttonCode == 12) {
        } else if (buttonCode == 13) {
        }
        return null;
    }
}
