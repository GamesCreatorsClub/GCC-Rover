/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.controllers;

import java.util.ArrayList;
import java.util.List;

public abstract class AbstractController implements ControllerInterface {

    public List<ControllerListener> listeners;

    private String name;

    public AbstractController() {
        listeners = new ArrayList<ControllerListener>();
        name = "controller";
    }

    public AbstractController(String name) {
        listeners = new ArrayList<ControllerListener>();
        this.name = name;
    }


    public void addListener(ControllerListener listener) {
        listeners.add(listener);
    }

    public void removeListener(ControllerListener listener) {
        listeners.remove(listener);
    }

    public void fireEvent(ControllerState state) {
        for (ControllerListener listener : listeners) {
            listener.controllerUpdate(state);
        }
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;

    }
}
