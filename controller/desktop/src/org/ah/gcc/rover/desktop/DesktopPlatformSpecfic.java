package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.PlatformSpecific;
import org.ah.gcc.rover.RoverHandler;

public class DesktopPlatformSpecfic implements PlatformSpecific {

    private DesktopRoverControl roverControl;


    public DesktopPlatformSpecfic() {
        roverControl = new DesktopRoverControl();
    }

    @Override
    public RoverHandler getRoverControl() {
        return roverControl;
    }
}
