package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.JoyStick;
import org.ah.gcc.rover.JoystickComponentListener;
import org.ah.gcc.rover.controllers.AbstractController;
import org.ah.gcc.rover.controllers.ControllerStateImplementation;
import org.ah.gcc.rover.controllers.JoystickState;

import com.badlogic.gdx.controllers.Controller;
import com.badlogic.gdx.controllers.ControllerListener;
import com.badlogic.gdx.controllers.PovDirection;
import com.badlogic.gdx.math.Vector3;

public class ComboController extends AbstractController implements ControllerListener {

    public ControllerStateImplementation state;

    public ComboController() {
        state = new ControllerStateImplementation();
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

    @Override
    public void connected(Controller controller) {
    }

    @Override
    public void disconnected(Controller controller) {
    }

    @Override
    public boolean buttonDown(Controller controller, int buttonCode) {
        state.setButton(buttonCode, true);
        fireEvent(state);
        return false;
    }

    @Override
    public boolean buttonUp(Controller controller, int buttonCode) {
        state.setButton(buttonCode, false);
        fireEvent(state);
        return false;
    }

    @Override
    public boolean axisMoved(Controller controller, int axisCode, float value) {
        if (axisCode == 0) {
            state.setX1(value);
        } else if (axisCode == 1) {
            state.setY1(value);
        } else if (axisCode == 2) {
            state.setX2(value);
        } else if (axisCode == 3) {
            state.setY2(value);
        } else if (axisCode == 4) {
            state.setX3(value);
        } else if (axisCode == 5) {
            state.setY3(value);
        }
        fireEvent(state);
        return false;
    }

    @Override
    public boolean povMoved(Controller controller, int povCode, PovDirection value) {
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
}
