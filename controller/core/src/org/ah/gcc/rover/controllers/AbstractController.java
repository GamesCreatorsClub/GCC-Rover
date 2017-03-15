package org.ah.gcc.rover.controllers;

import java.util.ArrayList;
import java.util.List;

public abstract class AbstractController implements ControllerInterface {

    public List<ControllerListener> listeners;

    public AbstractController() {
        listeners = new ArrayList<ControllerListener>();
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


}
