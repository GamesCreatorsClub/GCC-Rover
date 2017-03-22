package org.ah.gcc.rover.controllers;

import org.ah.gcc.rover.JoyStick;
import org.ah.gcc.rover.JoystickComponentListener;

public class ScreenController extends AbstractController {

    private ControllerStateImplementation state;

    public ScreenController() {
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

    public void buttonUp(int number, boolean state) {

    }

    public void buttonDown(int number, boolean state) {
    }

    public void setLeftJotstick(JoyStick joystick) {
        joystick.setListener(new JoystickComponentListener() {
            @Override
            public void changed(JoystickState stickstate) {
                state.setJoy1(stickstate);
                fireEvent(state);
            }
        });
    }

    public void setRightJotstick(JoyStick joystick) {
        joystick.setListener(new JoystickComponentListener() {
            @Override
            public void changed(JoystickState stickstate) {
                state.setJoy2(stickstate);
                fireEvent(state);

            }
        });
    }

    public void setHat(JoyStick joystick) {
        joystick.setListener(new JoystickComponentListener() {
            @Override
            public void changed(JoystickState stickstate) {
                state.setHat1(stickstate);
            }
        });

    }
//
//    public void setRightJotstick(JoyStick joystick) {
//        joystick.setListener(new JoystickCompon               entListener() {
//            public void changed(float x, float y) {
//                state.setX2(x);
//                state.setY2(y);
//            }
//        });
//    }

}
