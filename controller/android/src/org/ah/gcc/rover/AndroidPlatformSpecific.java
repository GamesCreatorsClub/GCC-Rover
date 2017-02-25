package org.ah.gcc.rover;

import android.content.Context;

public class AndroidPlatformSpecific implements PlatformSpecific {

    private AndroidRoverControl roverControl;
    private JoystickInterface leftJoystick = new DummyJoystickInterface();
    private JoystickInterface rightJoystick = new DummyJoystickInterface();
    
    public AndroidPlatformSpecific(Context applicationContext) {
        roverControl = new AndroidRoverControl(applicationContext);
    }
    
    @Override
    public void init() {
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

}
