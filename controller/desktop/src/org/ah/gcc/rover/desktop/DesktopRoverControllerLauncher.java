package org.ah.gcc.rover.desktop;

import com.badlogic.gdx.backends.lwjgl.LwjglApplication;
import com.badlogic.gdx.backends.lwjgl.LwjglApplicationConfiguration;

public class DesktopRoverControllerLauncher {
    public static void main(String[] arg) {
        LwjglApplicationConfiguration config = new LwjglApplicationConfiguration();
        config.width = 800;
        config.height = 500;
        new LwjglApplication(new DesktopGCCRoverController(new DesktopPlatformSpecfic()), config);
    }
}
