package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.ControllerInterface;

public interface PlatformSpecific {

    RoverHandler getRoverControl();

    void renderCallback();

    ControllerInterface getRealController();
}
