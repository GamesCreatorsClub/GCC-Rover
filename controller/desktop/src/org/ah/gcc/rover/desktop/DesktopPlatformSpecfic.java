/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.PlatformSpecific;
import org.ah.gcc.rover.RoverHandler;
import org.ah.gcc.rover.controllers.ControllerInterface;

public class DesktopPlatformSpecfic implements PlatformSpecific {

    private DesktopRoverControl roverControl;

    public DesktopPlatformSpecfic() {
        roverControl = new DesktopRoverControl();
    }

    @Override
    public RoverHandler getRoverControl() {
        return roverControl;
    }

    @Override
    public void renderCallback() {
    }

    @Override
    public ControllerInterface getRealController() {
        return new DesktopRealController();
    }
}
