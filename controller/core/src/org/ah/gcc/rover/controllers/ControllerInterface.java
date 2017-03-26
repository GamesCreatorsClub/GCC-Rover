package org.ah.gcc.rover.controllers;

public interface ControllerInterface {

    void addListener(ControllerListener listener);
    void removeListener(ControllerListener listener);

    //boolean isActive();
}
