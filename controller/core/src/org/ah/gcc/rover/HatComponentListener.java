/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

import org.ah.gcc.rover.controllers.JoystickState;

public interface HatComponentListener {

    void changed(JoystickState state);

}
