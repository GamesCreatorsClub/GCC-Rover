package org.ah.gcc.rover.desktop;

import static org.ah.gcc.rover.MathUtil.calculateExpo;

import java.util.Map;

import org.ah.gcc.rover.ControllerButton;
import org.ah.gcc.rover.DummyJoystickInterface;
import org.ah.gcc.rover.JoystickInterface;
import org.ah.gcc.rover.PlatformSpecific;
import org.ah.gcc.rover.RoverControl;

import com.badlogic.gdx.controllers.Controller;
import com.badlogic.gdx.controllers.Controllers;

public class DesktopPlatformSpecfic implements PlatformSpecific {

    private DesktopRoverControl roverControl;
    private Controller selectedController;

    private JoystickInterface leftJoystick = new JoystickInterface() {
        @Override
        public float getXValue() { return sanitise(selectedController.getAxis(0)); }

        @Override
        public float getYValue() { return sanitise(selectedController.getAxis(1)); }
    };

    private JoystickInterface rightJoystick = new JoystickInterface() {
        @Override
        public float getXValue() { return sanitise(selectedController.getAxis(3)); }

        @Override
        public float getYValue() { return sanitise(selectedController.getAxis(4)); }
    };

    public DesktopPlatformSpecfic() {
        roverControl = new DesktopRoverControl();
    }

    @Override
    public void init() {
        if (Controllers.getControllers().size > 0) {
            if (Controllers.getControllers().first() != null) {
                selectedController = Controllers.getControllers().first();
            }
        }
        if (selectedController == null) {
            leftJoystick = new DummyJoystickInterface();
            rightJoystick = new DummyJoystickInterface();
        }
    }

    @Override
    public RoverControl getRoverControl() {
        return roverControl;
    }

    @Override
    public JoystickInterface getLeftJoystick() {
        return leftJoystick;
    }

    @Override
    public JoystickInterface getRightJoystick() {
        return rightJoystick;
    }

    public void updateControllerButtons(Map<ControllerButton, Boolean> buttons) {
        for (ControllerButton button : ControllerButton.values()) {
            buttons.put(button, selectedController.getButton(button.getButtonCode()));
        }
    }

    private float sanitise(float input) {
        if (Math.abs(input) < 0.02f) {
            return 0;
        }

      input = calculateExpo(input, 1.00f);

        if (input > 1.0f) {
            input = 1.0f;
        } else if (input < -1.0f) {
            input = -1.0f;
        }

        return input;
    }
}
