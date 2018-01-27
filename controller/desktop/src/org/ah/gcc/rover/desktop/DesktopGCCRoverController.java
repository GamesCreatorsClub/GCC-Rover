/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.desktop;

import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;

import org.ah.gcc.rover.JoystickComponentListener;
import org.ah.gcc.rover.PlatformSpecific;
import org.ah.gcc.rover.RoverDriver;
import org.ah.gcc.rover.RoverHandler;
import org.ah.gcc.rover.controllers.ControllerInterface;
import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.JoystickState;
import org.ah.gcc.rover.controllers.ScreenController;
import org.ah.gcc.rover.ui.Button;
import org.ah.gcc.rover.ui.ExpoGraph;
import org.ah.gcc.rover.ui.JoyStick;
import org.ah.gcc.rover.ui.LogoDrawer;
import org.ah.gcc.rover.ui.Orientation;
import org.ah.gcc.rover.ui.POV;
import org.ah.gcc.rover.ui.RoundButton;
import org.ah.gcc.rover.ui.SquareButton;
import org.ah.gcc.rover.ui.Switch;

import com.badlogic.gdx.ApplicationAdapter;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.InputMultiplexer;
import com.badlogic.gdx.InputProcessor;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Pixmap.Format;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.GlyphLayout;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.input.GestureDetector;
import com.badlogic.gdx.input.GestureDetector.GestureListener;
import com.badlogic.gdx.math.Vector2;

public class DesktopGCCRoverController extends ApplicationAdapter implements InputProcessor, GestureListener {

    private PlatformSpecific platformSpecific;

    private RoverHandler roverHandler;

    private SpriteBatch batch;
    private Texture img;

    private ShapeRenderer shapeRenderer;

    private OrthographicCamera camera;

    private InputMultiplexer inputMultiplexer;

    private BitmapFont font;
    private static GlyphLayout glyphLayout;

    private JoyStick leftjoystick;
    private JoyStick rightjoystick;

    private ExpoGraph leftExpo;
    private ExpoGraph rightExpo;

    private int messageCounter = 10;

    private String roverSpeed = "";
    private String roverTurningDistance = "";

    private double cellSize;

    private Switch switchLB;
    private SquareButton switchLT;

    private Switch switchRB;
    private SquareButton switchRT;

    private Button roverSelectButton;

    private RoundButton button1;

    private boolean logos = true;

    private long alpha = 0;

    private ComboController comboController;

    private LogoDrawer logoDrawer;

    private RoverDriver roverDriver;

    private POV pov;

    private ScreenController screenController;

    private ControllerInterface realController;

    private boolean grid = false;

    public DesktopGCCRoverController(PlatformSpecific platformSpecific) {
        this.platformSpecific = platformSpecific;
        this.roverHandler = platformSpecific.getRoverControl();
    }

    @Override
    public void create() {
        // platformSpecific.init();

        String fontName = "fonts/din-alternate-bold-64.fnt";
        if (Gdx.graphics.getWidth() <= 320) {
            fontName = "fonts/din-alternate-bold-15.fnt";
        }

        font = new BitmapFont(Gdx.files.internal(fontName), true);
        glyphLayout = new GlyphLayout();

        font.setColor(Color.BLACK);
        batch = new SpriteBatch();
        img = new Texture("badlogic.jpg");

        camera = new OrthographicCamera(Gdx.graphics.getWidth(), Gdx.graphics.getHeight());

        cellSize = Gdx.graphics.getWidth() / 20;

        shapeRenderer = new ShapeRenderer();

        leftjoystick = new JoyStick((int) cellSize * 8, (int) cellSize * 4, (int) cellSize * 4);
        rightjoystick = new JoyStick((int) cellSize * 8, (int) cellSize * 16, (int) cellSize * 4);

        leftExpo = new ExpoGraph((int) cellSize * 5, (int) cellSize * 2, (int) cellSize * 2, (int) cellSize * 2);
        rightExpo = new ExpoGraph((int) cellSize * 13, (int) cellSize * 2, (int) cellSize * 2, (int) cellSize * 2);

        leftExpo.setPercentage(0.75f);
        rightExpo.setPercentage(0.90f);

        roverSelectButton = new Button((int) cellSize * 6, 0, (int) cellSize * 8, (int) (cellSize * 1.5), new Button.ButtonCallback() {
            @Override
            public void invoke(boolean state) {
                if (state) {
                    int selectedRover = roverDriver.getSelectedRover().getValue() + 1;
                    if (selectedRover >= RoverHandler.ROVERS.length) {
                        selectedRover = 0;
                    }
                    roverDriver.getSelectedRover().setValue(selectedRover);
                }
            }
        });

        pov = new POV((int) cellSize * 9, (int) cellSize * 4, (int) cellSize * 2);


        button1 = new RoundButton((int) cellSize * 6, (int) cellSize * 11, (int) cellSize / 2);

        switchLT = new SquareButton((int) cellSize * 0, (int) (cellSize * 0), (int) cellSize * 4, (int) cellSize * 2);
        switchLT.setState(false);
        switchLB = new Switch((int) cellSize * 0, (int) (cellSize * 2), (int) cellSize * 2, Orientation.HORIZONTAL);
        switchLB.setState(false);

        switchRT = new SquareButton((int) cellSize * 16, (int) (cellSize * 0), (int) cellSize * 4, (int) cellSize * 2);
        switchRT.setState(false);
        switchRB = new Switch((int) cellSize * 16, (int) (cellSize * 2), (int) cellSize * 2, Orientation.HORIZONTAL);
        switchRB.setState(false);

        inputMultiplexer = new InputMultiplexer();
        inputMultiplexer.addProcessor(this);
        inputMultiplexer.addProcessor(new GestureDetector(this));
        Gdx.input.setInputProcessor(inputMultiplexer);

        screenController = new ScreenController();
        realController = platformSpecific.getRealController();

        screenController.setLeftJotstick(leftjoystick);
        screenController.setRightJotstick(rightjoystick);
        screenController.setHat(pov);
        screenController.setButton(switchLB, ControllerState.ButtonType.ORBIT_BUTTON);
        screenController.setButton(switchRB, ControllerState.ButtonType.LOCK_AXIS_BUTTON);
        screenController.setButton(switchLT, ControllerState.ButtonType.BOOST_BUTTON);
        screenController.setButton(switchRT, ControllerState.ButtonType.KICK_BUTTON);
        screenController.setButton(roverSelectButton, ControllerState.ButtonType.SELECT_BUTTON);

        if (realController != null) {
            comboController = new ComboController(screenController, realController);
            roverDriver = new RoverDriver(roverHandler, comboController);
        } else {
            roverDriver = new RoverDriver(roverHandler, screenController);
        }

        roverDriver.getLeftJoystick().addListener(new JoystickComponentListener() {
            @Override public void changed(JoystickState state) {
                leftjoystick.setValues(state.getX(), state.getY());
            }
        });

        roverDriver.getRightJoystick().addListener(new JoystickComponentListener() {
            @Override public void changed(JoystickState state) {
                rightjoystick.setValues(state.getX(), state.getY());
            }
        });

        roverDriver.getRoverSpeedValue().addListener(new PropertyChangeListener() {
            @Override public void propertyChange(PropertyChangeEvent evt) {
                roverSpeed = evt.getNewValue().toString();
            }
        });

        roverDriver.getReadDistanceValue().addListener(new PropertyChangeListener() {
            @Override public void propertyChange(PropertyChangeEvent evt) {
                roverTurningDistance = evt.getNewValue().toString();
            }
        });



        logoDrawer = new LogoDrawer(batch, camera);

        Pixmap pixmap = new Pixmap(32, 32, Format.RGBA8888);
        //Cursor customCursor = Gdx.graphics.newCursor(pixmap, 0, 0);
        //Gdx.graphics.setCursor(customCursor);
    }

    @Override
    public void render() {
        alpha++;
        if (logos) {
            logoDrawer.draw();
            logos = !logoDrawer.done();
        } else {
            messageCounter--;
            if (messageCounter < 0) {
                messageCounter = 5;
            }

            camera.setToOrtho(true);

            Gdx.gl.glClearColor(1, 1, 1, 1);
            Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

            batch.setProjectionMatrix(camera.combined);
            shapeRenderer.setProjectionMatrix(camera.combined);
            shapeRenderer.setAutoShapeType(true);

            String connectedStr = RoverHandler.ROVERS[roverDriver.getSelectedRover().getValue()].getName();

            shapeRenderer.begin();
            if (grid ) {
                shapeRenderer.setColor(0.9f, 0.9f, 0.9f, 1f);
                for (int x = 0; x < Gdx.graphics.getWidth(); x = (int) (x + cellSize)) {
                    shapeRenderer.line(x, 0, x, Gdx.graphics.getHeight());
                }
                for (int y = 0; y < Gdx.graphics.getHeight(); y = (int) (y + cellSize)) {
                    shapeRenderer.line(0, y, Gdx.graphics.getWidth(), y);
                }
            }
            shapeRenderer.setColor(Color.BLACK);

            leftjoystick.draw(shapeRenderer);
            rightjoystick.draw(shapeRenderer);
            leftExpo.draw(shapeRenderer);
            rightExpo.draw(shapeRenderer);

            button1.draw(shapeRenderer);
            switchLB.draw(shapeRenderer);
            switchLT.draw(shapeRenderer);
            pov.draw(shapeRenderer);
            switchRB.draw(shapeRenderer);
            switchRT.draw(shapeRenderer);

            roverSelectButton.draw(shapeRenderer);

            shapeRenderer.end();
            batch.begin();
            glyphLayout.setText(font, connectedStr);
            if (roverHandler.isConnected()) {
                font.setColor(Color.GREEN);
            } else {
                font.setColor(Color.RED);
            }
            font.draw(batch, connectedStr, (Gdx.graphics.getWidth() - glyphLayout.width) / 2, 0);
            font.setColor(Color.BLACK);
            font.draw(batch, String.format("S: " + roverSpeed), Gdx.graphics.getWidth() - 200, 0);
            font.draw(batch, String.format("D: " + roverTurningDistance), 0, 0);
            batch.end();

            if (alpha % 12 == 0) {
                roverDriver.processJoysticks();
            }

        }
    }

    @Override
    public void dispose() {
        batch.dispose();
        img.dispose();
    }

    @Override
    public boolean keyDown(int keycode) {
        return false;
    }

    @Override
    public boolean keyUp(int keycode) {
        return false;
    }

    @Override
    public boolean keyTyped(char character) {
        return false;
    }

    @Override
    public boolean touchDown(int screenX, int screenY, int pointer, int button) {
        if (comboController != null) {
            comboController.setTouchState(true);
        }
        leftjoystick.touchDown(screenX, screenY, pointer);
        rightjoystick.touchDown(screenX, screenY, pointer);
        switchLB.touchDown(screenX, screenY, pointer);
        switchLT.touchDown(screenX, screenY, pointer);
        switchRT.touchDown(screenX, screenY, pointer);
        switchRB.touchDown(screenX, screenY, pointer);

        button1.touchDown(screenX, screenY, pointer);
        roverSelectButton.touchDown(screenX, screenY, pointer);

        screenController.stickMoved(0, new JoystickState(leftjoystick.getXValue(), leftjoystick.getYValue()));
        screenController.stickMoved(1, new JoystickState(rightjoystick.getXValue(), rightjoystick.getYValue()));
        pov.touchDown(screenX, screenY, pointer);
        return false;
    }

    @Override
    public boolean touchUp(int screenX, int screenY, int pointer, int button) {
        if (comboController != null) {
            comboController.setTouchState(false);
        }
        leftjoystick.touchUp(screenX, screenY, pointer);
        rightjoystick.touchUp(screenX, screenY, pointer);
        button1.touchUp(screenX, screenY, pointer);
        roverSelectButton.touchUp(screenX, screenY, pointer);

        screenController.stickMoved(0, new JoystickState(leftjoystick.getXValue(), leftjoystick.getYValue()));
        screenController.stickMoved(1, new JoystickState(rightjoystick.getXValue(), rightjoystick.getYValue()));
        pov.touchUp(screenX, screenY, pointer);

        switchLT.touchUp(screenX, screenY, pointer);
        switchLB.touchUp(screenX, screenY, pointer);

        switchRT.touchUp(screenX, screenY, pointer);
        switchRB.touchUp(screenX, screenY, pointer);

        return false;
    }

    @Override
    public boolean touchDragged(int screenX, int screenY, int pointer) {
        leftjoystick.dragged(screenX, screenY, pointer);
        rightjoystick.dragged(screenX, screenY, pointer);
        button1.touchDragged(screenX, screenY, pointer);
        roverSelectButton.touchDragged(screenX, screenY, pointer);
        screenController.stickMoved(0, new JoystickState(leftjoystick.getXValue(), leftjoystick.getYValue()));
        screenController.stickMoved(1, new JoystickState(rightjoystick.getXValue(), rightjoystick.getYValue()));
        pov.dragged(screenX, screenY, pointer);

        switchLT.touchDragged(screenX, screenY, pointer);
        switchRT.touchDragged(screenX, screenY, pointer);
        return false;

    }

    @Override
    public boolean mouseMoved(int screenX, int screenY) {
        return false;
    }

    @Override
    public boolean scrolled(int amount) {
        return false;
    }

    @Override
    public boolean touchDown(float x, float y, int pointer, int button) {
        return false;
    }

    @Override
    public boolean tap(float x, float y, int count, int button) {
        return false;
    }

    @Override
    public boolean longPress(float x, float y) {
        return false;
    }

    @Override
    public boolean fling(float velocityX, float velocityY, int button) {
        return false;
    }

    @Override
    public boolean pan(float x, float y, float deltaX, float deltaY) {
        return false;
    }

    @Override
    public boolean panStop(float x, float y, int pointer, int button) {
        return false;
    }

    @Override
    public boolean zoom(float initialDistance, float distance) {
        return false;
    }

    @Override
    public boolean pinch(Vector2 initialPointer1, Vector2 initialPointer2, Vector2 pointer1, Vector2 pointer2) {
        return false;
    }

    @Override
    public void pinchStop() {
    }
}
