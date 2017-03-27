package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.controllers.AbstractController;
import org.ah.gcc.rover.controllers.ControllerInterface;
import org.ah.gcc.rover.controllers.ControllerListener;
import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.ScreenController;

public class ComboController extends AbstractController {

    public ControllerState state;

    private ControllerInterface controller1;
    private ControllerInterface controller2;

    private boolean mousedown = false;

    public ComboController(ControllerInterface controller1, ControllerInterface controller2) {
        this.controller1 = controller1;
        this.controller2 = controller2;
        controller1.addListener(new ControllerListener() {
            @Override
            public void controllerUpdate(ControllerState state) {
                if (mousedown) {
                    ComboController.this.state = state;
                    // fireEvent(state);
                }
            }
        });
        controller2.addListener(new ControllerListener() {
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

    public ControllerInterface getController1() {
        return controller1;
    }

    public void setController1(ScreenController controller1) {
        this.controller1 = controller1;
    }

    public ControllerInterface getController2() {
        return controller2;
    }

    public void setController2(RealController controller2) {
        this.controller2 = controller2;
    }
}
