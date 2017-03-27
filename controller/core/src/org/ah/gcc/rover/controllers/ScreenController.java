package org.ah.gcc.rover.controllers;

import org.ah.gcc.rover.HatComponentListener;
import org.ah.gcc.rover.JoystickComponentListener;
import org.ah.gcc.rover.controllers.ControllerState.ButtonType;
import org.ah.gcc.rover.ui.ButtonComponentListener;
import org.ah.gcc.rover.ui.JoyStick;
import org.ah.gcc.rover.ui.POV;
import org.ah.gcc.rover.ui.ScreenButton;

public class ScreenController extends AbstractController {

    private ControllerStateImplementation state;

    public ScreenController() {
        state = new ControllerStateImplementation();
    }

    public ScreenController(String name) {
        super(name);
        state = new ControllerStateImplementation();
    }

    public void stickMoved(int number, JoystickState position) {
        if (number == 0) {
            state.setJoy1(position);
        } else if (number == 1) {
            state.setJoy2(position);
        } else if (number == 2) {
            state.setHat1(position);
        }
        fireEvent(state);
    }

    public void setLeftJotstick(JoyStick joystick) {
        joystick.setListener(new JoystickComponentListener() {
            @Override public void changed(JoystickState stickstate) {
                state.setJoy1(stickstate);
                fireEvent(state);
            }
        });
    }

    public void setRightJotstick(JoyStick joystick) {
        joystick.setListener(new JoystickComponentListener() {
            @Override public void changed(JoystickState stickstate) {
                state.setJoy2(stickstate);
                fireEvent(state);
            }
        });
    }

    public void setButton(ScreenButton component, final ButtonType buttonID) {
        component.setListener(new ButtonComponentListener() {
            @Override public void changed(boolean on) {
                state.setButton(buttonID, on);
                fireEvent(state);
            }
        });
    }

    public void setHat(POV hat) {
        hat.setListener(new HatComponentListener() {
            @Override public void changed(JoystickState stickstate) {
                state.setHat1(stickstate);
            }
        });

    }
}
