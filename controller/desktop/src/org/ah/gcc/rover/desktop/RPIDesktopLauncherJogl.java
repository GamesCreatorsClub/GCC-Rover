/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.desktop;

import com.badlogic.gdx.backends.jogamp.JoglNewtApplication;
import com.badlogic.gdx.backends.jogamp.JoglNewtApplicationConfiguration;

public class RPIDesktopLauncherJogl {
    public static void main(String[] arg) {
        JoglNewtApplicationConfiguration config = new JoglNewtApplicationConfiguration();
        config.width = 640;
        config.height = 480;

        new JoglNewtApplication(new HeadlessGCCRoverController(new RPiDesktopPlatformSpecfic()), config);
    }
}
