package org.ah.gcc.rover;

import com.badlogic.gdx.controllers.Controller;
import com.badlogic.gdx.controllers.ControllerListener;
import com.badlogic.gdx.controllers.PovDirection;
import com.badlogic.gdx.math.Vector3;
public class MyControllerListener implements ControllerListener {

    @Override
    public void connected(Controller controller) {
        System.out.println("conected controller");
        
    }

    @Override
    public void disconnected(Controller controller) {
        System.out.println("disconected controller");
        
    }

    @Override
    public boolean buttonDown(Controller controller, int buttonCode) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean buttonUp(Controller controller, int buttonCode) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean axisMoved(Controller controller, int axisCode, float value) {
        // TODO Auto-generated method stub
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
