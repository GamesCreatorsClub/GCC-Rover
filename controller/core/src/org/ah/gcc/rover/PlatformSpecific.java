/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.ControllerInterface;

public interface PlatformSpecific {

    RoverHandler getRoverControl();

    void renderCallback();

    ControllerInterface getRealController();
}
