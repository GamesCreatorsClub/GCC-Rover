package org.ah.gcc.rover.desktop;

import static org.ah.gcc.rover.MathUtil.calculateExpo;

import org.ah.gcc.rover.DummyJoystickInterface;
import org.ah.gcc.rover.JoystickInterface;
import org.ah.gcc.rover.PlatformSpecific;
import org.ah.gcc.rover.RoverControl;

import com.badlogic.gdx.controllers.Controller;
import com.badlogic.gdx.controllers.Controllers;

public class DesktopPlatformSpecfic implements PlatformSpecific {

    private DesktopRoverControl roverControl;
    private Controller c;

    private JoystickInterface leftJoystick = new JoystickInterface() {
        @Override
        public float getXValue() { return sanitise(c.getAxis(0)); }

        @Override
        public float getYValue() { return sanitise(c.getAxis(1)); }
    };

    private JoystickInterface rightJoystick = new JoystickInterface() {
        @Override
        public float getXValue() { return sanitise(c.getAxis(3)); }

        @Override
        public float getYValue() { return sanitise(c.getAxis(4)); }
    };

    public DesktopPlatformSpecfic() {
        roverControl = new DesktopRoverControl();
    }

    @Override
    public void init() {
        if (Controllers.getControllers().size > 0) {
            if (Controllers.getControllers().first() != null) {
                c = Controllers.getControllers().first();
            }
        }
        if (c == null) {
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
