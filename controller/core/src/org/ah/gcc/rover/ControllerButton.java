/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

public enum ControllerButton {

    BUTTON_A(0),
    BUTTON_B(1),
    BUTTON_X(2),
    BUTTON_Y(3),
    BUTTON_LB(4),
    BUTTON_RB(5),
    BUTTON_BACK(6),
    BUTTON_START(7),
    BUTTON_LS(8), //Left Stick pressed down
    BUTTON_RS(9); //Right Stick pressed down

    private int button;

    ControllerButton(int button) {
        this.button = button;
    }

    public int getButtonCode() {
        return button;
    }

//    public static final int BUTTON_A = 0;
//    public static final int BUTTON_B = 1;
//    public static final int BUTTON_X = 2;
//    public static final int BUTTON_Y = 3;
//    public static final int BUTTON_LB = 4;
//    public static final int BUTTON_RB = 5;
//    public static final int BUTTON_BACK = 6;
//    public static final int BUTTON_START = 7;
//    public static final int BUTTON_LS = 8; //Left Stick pressed down
//    public static final int BUTTON_RS = 9; //Right Stick pressed down
//
//    public static final int POV = 0;
//
//    public static final int AXIS_LY = 0; //-1 is up | +1 is down
//    public static final int AXIS_LX = 1; //-1 is left | +1 is right
//    public static final int AXIS_RY = 2; //-1 is up | +1 is down
//    public static final int AXIS_RX = 3; //-1 is left | +1 is right
//    public static final int AXIS_TRIGGER = 4; //LT and RT are on the same Axis! LT > 0 | RT < 0
  }
