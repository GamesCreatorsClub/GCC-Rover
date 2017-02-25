package org.ah.gcc.rover;

public interface PlatformSpecific {

    void init();
    
    RoverControl getRoverControl();
    
    JoystickInterface getLeftJoystick();
    
    JoystickInterface getRightJoystick();
}
