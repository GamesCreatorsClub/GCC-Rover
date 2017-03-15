package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.controllers.AbstractController;
import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.ControllerStateImplementation;

import com.badlogic.gdx.controllers.Controller;
import com.badlogic.gdx.controllers.ControllerListener;
import com.badlogic.gdx.controllers.PovDirection;
import com.badlogic.gdx.math.Vector3;

public class RealController extends AbstractController implements ControllerListener {

    private ControllerStateImplementation state;

    public RealController() {
        state = new ControllerStateImplementation();
    }

    public ControllerState getState() {
        return state;
    }

    public void setState(ControllerStateImplementation state) {
        this.state = state;
    }

    @Override
    public void connected(Controller controller) {
        // TODO Auto-generated method stub

    }

    @Override
    public void disconnected(Controller controller) {
        // TODO Auto-generated method stub

    }

    @Override
    public boolean buttonDown(Controller controller, int buttonCode) {
        state.setButton(buttonCode, true);
        //fireEvent(state);
        return false;
    }

    @Override
    public boolean buttonUp(Controller controller, int buttonCode) {
        state.setButton(buttonCode, false);
        //fireEvent(state);
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
        //fireEvent(state);
        return false;
    }

    @Override
    public boolean povMoved(Controller controller, int povCode, PovDirection value) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean xSliderMoved(Controller controller, int sliderCode, boolean value) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean ySliderMoved(Controller controller, int sliderCode, boolean value) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean accelerometerMoved(Controller controller, int accelerometerCode, Vector3 value) {
        // TODO Auto-generated method stub
        return false;
    }

}
