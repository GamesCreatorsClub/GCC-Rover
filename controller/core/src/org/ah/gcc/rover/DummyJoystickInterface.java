/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

public class DummyJoystickInterface implements JoystickInterface {

    @Override
    public float getXValue() {
        return 0f;
    }

    @Override
    public float getYValue() {
        return 0f;
    }

}
