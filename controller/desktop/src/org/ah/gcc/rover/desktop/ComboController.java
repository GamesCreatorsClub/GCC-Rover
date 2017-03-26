package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.controllers.AbstractController;
import org.ah.gcc.rover.controllers.ControllerListener;
import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.ScreenController;

public class ComboController extends AbstractController {

    public ControllerState state;

    private ScreenController screenController;
    private RealController realController;

    private boolean mousedown = false;

    public ComboController() {
        screenController = new ScreenController("screen controller");
        screenController.addListener(new ControllerListener() {
            @Override
            public void controllerUpdate(ControllerState state) {
                if (mousedown) {
                    ComboController.this.state = state;
//                    fireEvent(state);
                }
            }
        });
        realController = new RealController("real controller");
        realController.addListener(new ControllerListener() {
            @Override
            public void controllerUpdate(ControllerState state) {
                if (!mousedown) {
                    ComboController.this.state = state;
                    fireEvent(state);
                }
            }
        });
    }

    public void setTouchState(boolean touchdown) {
        mousedown = touchdown;
    }

    public ScreenController getScreenController() {
        return screenController;
    }

    public void setScreenController(ScreenController screenController) {
        this.screenController = screenController;
    }

    public RealController getRealController() {
        return realController;
    }

    public void setRealController(RealController realController) {
        this.realController = realController;
    }
}
