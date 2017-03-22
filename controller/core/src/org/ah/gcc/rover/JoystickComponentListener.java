package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.JoystickState;

public interface JoystickComponentListener {

    void changed(JoystickState state);

}
