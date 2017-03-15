package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.JoystickState;

public interface JoystickComponentListener {
    public void changed(JoystickState state);
}
