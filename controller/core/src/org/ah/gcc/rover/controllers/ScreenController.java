package org.ah.gcc.rover.controllers;

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

//    public void setLeftJotstick(JoyStick joystick) {
//        joystick.setListener(new JoystickComponentListener() {
//            public void changed(float x, float y) {
//                state.setX1(x);
//                state.setY1(y);
//            }
//        });
//    }
//
//    public void setRightJotstick(JoyStick joystick) {
//        joystick.setListener(new JoystickComponentListener() {
//            public void changed(float x, float y) {
//                state.setX2(x);
//                state.setY2(y);
//            }
//        });
//    }

}
