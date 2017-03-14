package org.ah.gcc.rover;

import java.util.Map;

public interface PlatformSpecific {

    void init();

    RoverControl getRoverControl();

    JoystickInterface getLeftJoystick();

    JoystickInterface getRightJoystick();

    void updateControllerButtons(Map<ControllerButton, Boolean> buttons);
}
