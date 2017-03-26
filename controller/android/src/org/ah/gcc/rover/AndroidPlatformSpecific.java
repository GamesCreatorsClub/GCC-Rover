package org.ah.gcc.rover;

import android.content.Context;

public class AndroidPlatformSpecific implements PlatformSpecific {

    private AndroidRoverControl roverControl;

    public AndroidPlatformSpecific(Context applicationContext) {
        roverControl = new AndroidRoverControl(applicationContext);
    }

    @Override
    public RoverHandler getRoverControl() {
        return roverControl;
    }
}
