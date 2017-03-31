/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.controllers;

public interface ControllerInterface {

    void addListener(ControllerListener listener);
    void removeListener(ControllerListener listener);

    //boolean isActive();
}
