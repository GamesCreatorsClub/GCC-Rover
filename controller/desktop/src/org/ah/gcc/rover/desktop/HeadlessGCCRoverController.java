package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.PlatformSpecific;
import org.ah.gcc.rover.RoverDriver;
import org.ah.gcc.rover.RoverHandler;
import org.ah.gcc.rover.controllers.ControllerInterface;

import com.badlogic.gdx.ApplicationAdapter;

public class HeadlessGCCRoverController extends ApplicationAdapter {

    private PlatformSpecific platformSpecific;

    private RoverHandler roverHandler;

    private int messageCounter = 10;

    private String roverSpeed = "";
    private String roverTurningDistance = "";

    private long alpha = 0;

    private RoverDriver roverDriver;

    private ControllerInterface realController;


    public HeadlessGCCRoverController(PlatformSpecific platformSpecific) {
        this.platformSpecific = platformSpecific;
        this.roverHandler = platformSpecific.getRoverControl();
    }

    @Override
    public void create() {
        realController = platformSpecific.getRealController();
        roverDriver = new RoverDriver(roverHandler, realController);
    }

    @Override
    public void render() {
        alpha++;
        if (alpha % 10 == 0) {
            System.out.println("All's good!");
            roverDriver.processJoysticks();
        }
    }

    @Override
    public void dispose() {
    }

}
