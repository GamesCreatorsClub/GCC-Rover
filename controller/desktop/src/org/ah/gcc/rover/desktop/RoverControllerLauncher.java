package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.RoverController;

import com.badlogic.gdx.backends.lwjgl.LwjglApplication;
import com.badlogic.gdx.backends.lwjgl.LwjglApplicationConfiguration;

public class RoverControllerLauncher {
    public static void main(String[] arg) {
        LwjglApplicationConfiguration config = new LwjglApplicationConfiguration();
        config.width = 800;
        config.height = 500;
        new LwjglApplication(new RoverController(new DesktopPlatformSpecfic()), config);
    }
}
