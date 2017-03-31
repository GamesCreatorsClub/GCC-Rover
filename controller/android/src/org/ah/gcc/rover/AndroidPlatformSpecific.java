/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.ControllerInterface;

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

    @Override
    public void renderCallback() {
    }

    @Override
    public ControllerInterface getRealController() {
        return null;
    }
}
