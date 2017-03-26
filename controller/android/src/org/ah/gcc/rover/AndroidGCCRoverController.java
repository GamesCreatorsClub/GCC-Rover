package org.ah.gcc.rover;

import java.util.EnumMap;
import java.util.Map;

import org.ah.gcc.rover.controllers.ControllerState;
import org.ah.gcc.rover.controllers.JoystickState;
import org.ah.gcc.rover.controllers.ScreenController;
import org.ah.gcc.rover.ui.Button;
import org.ah.gcc.rover.ui.ExpoGraph;
import org.ah.gcc.rover.ui.JoyStick;
import org.ah.gcc.rover.ui.LogoDrawer;
import org.ah.gcc.rover.ui.Orientation;
import org.ah.gcc.rover.ui.RoundButton;
import org.ah.gcc.rover.ui.Switch;

import com.badlogic.gdx.ApplicationAdapter;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.InputMultiplexer;
import com.badlogic.gdx.InputProcessor;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.GlyphLayout;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.input.GestureDetector;
import com.badlogic.gdx.input.GestureDetector.GestureListener;
import com.badlogic.gdx.math.Vector2;

public class AndroidGCCRoverController extends ApplicationAdapter implements InputProcessor, GestureListener {
    private RoverDetails[] ROVERS = new RoverDetails[] {
            new RoverDetails("Rover 2", "172.24.1.184", 1883),
            new RoverDetails("Rover 3", "172.24.1.185", 1883),
            new RoverDetails("Rover 4", "172.24.1.186", 1883),
            new RoverDetails("Rover 2p", "gcc-wifi-ap", 1884),
            new RoverDetails("Rover 3p", "gcc-wifi-ap", 1885),
            new RoverDetails("Rover 4p", "gcc-wifi-ap", 1886)
    };

    private PlatformSpecific platformSpecific;
    private RoverHandler roverControl;

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

    private int selectedRover = 0;
    private int newSelectedRover = 0;

    private int retryCounter = 0;
    private int messageCounter = 10;

    private int roverSpeed = 0;
    private int roverTurningDistance = 0;

    private double cellSize;

    private Switch switchLB;

    private Switch switchLT;

    private Switch switch2;

    private Button roverSelectButton;

    private RoundButton button1;

    private boolean logos = true;

    private boolean mouseDown = false;

    private long alpha = 0;

    private ScreenController screenController;

    private Map<ControllerButton, Boolean> controllerButtons = new EnumMap<ControllerButton, Boolean>(ControllerButton.class);

    private LogoDrawer logoDrawer;

    private RoverHandler roverHandler;

    private RoverDriver roverDriver;

    public AndroidGCCRoverController(PlatformSpecific platformSpecific) {
        this.platformSpecific = platformSpecific;
        this.roverControl = platformSpecific.getRoverControl();
    }

    @Override
    public void create() {
        // platformSpecific.init();


        font = new BitmapFont(Gdx.files.internal("fonts/din-alternate-bold-64.fnt"), true);
        glyphLayout = new GlyphLayout();

        font.setColor(Color.BLACK);
        batch = new SpriteBatch();
        img = new Texture("badlogic.jpg");


        camera = new OrthographicCamera(Gdx.graphics.getWidth(), Gdx.graphics.getHeight());

        cellSize = Gdx.graphics.getWidth() / 20;

        shapeRenderer = new ShapeRenderer();

        leftjoystick = new JoyStick((int)cellSize * 8, (int)cellSize * 4, (int)cellSize * 4);
        rightjoystick = new JoyStick((int)cellSize * 8, (int)cellSize * 16, (int)cellSize * 4);

        leftExpo = new ExpoGraph((int)cellSize * 8, (int)cellSize * 2, (int)cellSize * 2, (int)cellSize * 2);
        rightExpo = new ExpoGraph((int)cellSize * 10, (int)cellSize * 2, (int)cellSize * 2, (int)cellSize * 2);

        leftExpo.setPercentage(0.75f);
        rightExpo.setPercentage(0.90f);

        roverSelectButton = new Button((int)cellSize * 6, 0, (int)cellSize * 8, (int)(cellSize * 1.5), new Button.ButtonCallback() {
            @Override
            public void invoke(boolean state) {
                if (state) {
                    newSelectedRover = selectedRover + 1;
                    if (newSelectedRover >= ROVERS.length) {
                        newSelectedRover = 0;
                    }
                }
            }
        });

        button1 = new RoundButton((int)cellSize * 6, (int)cellSize * 11, (int)cellSize / 2);

        switchLT = new Switch((int)cellSize * 0, (int)(cellSize * 1), (int)cellSize * 4, Orientation.HORIZONTAL);
        switchLT.setState(true);
        switchLB = new Switch((int)cellSize * 0, (int)(cellSize * 3), (int)cellSize * 4, Orientation.HORIZONTAL);
        switchLB.setState(true);
        switch2 = new Switch((int)cellSize * 13, (int)cellSize, (int)cellSize * 2, Orientation.VERTICAL);


        inputMultiplexer = new InputMultiplexer();
        inputMultiplexer.addProcessor(this);
        inputMultiplexer.addProcessor(new GestureDetector(this));
        Gdx.input.setInputProcessor(inputMultiplexer);

        screenController = new ScreenController();
        screenController.setLeftJotstick(leftjoystick);
        screenController.setRightJotstick(rightjoystick);

        screenController.setButton(switchLB, ControllerState.ButtonType.ORBIT_BUTTON);
        roverDriver = new RoverDriver(roverControl, screenController);

        logoDrawer = new LogoDrawer(batch, camera);

    }

    @Override
    public void render() {

        roverDriver.processJoysticks();

        alpha++;
        if (logos) {
            logoDrawer.draw();
            logos = logoDrawer.done();
        } else {
            testConnection();

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

            String connectedStr = ROVERS[selectedRover].getName();

            shapeRenderer.begin();
            shapeRenderer.setColor(0.9f, 0.9f, 0.9f, 1f);
            for (int x = 0; x < Gdx.graphics.getWidth(); x = (int) (x + cellSize)) {
                shapeRenderer.line(x, 0, x, Gdx.graphics.getHeight());
            }
            for (int y = Gdx.graphics.getHeight(); y > 0 ; y = (int) (y - cellSize)) {
                shapeRenderer.line(0, y, Gdx.graphics.getWidth(), y);
            }

            shapeRenderer.setColor(Color.BLACK);

            leftjoystick.draw(shapeRenderer);
            rightjoystick.draw(shapeRenderer);
            leftExpo.draw(shapeRenderer);
            rightExpo.draw(shapeRenderer);

            button1.draw(shapeRenderer);
            switchLB.draw(shapeRenderer);
            switchLT.draw(shapeRenderer);
            switch2.draw(shapeRenderer);
            roverSelectButton.draw(shapeRenderer);

            shapeRenderer.end();
            batch.begin();
            glyphLayout.setText(font, connectedStr);
            if (roverControl.isConnected()) {
                font.setColor(Color.GREEN);
            } else {
                font.setColor(Color.RED);
            }
            font.draw(batch, connectedStr, (Gdx.graphics.getWidth() - glyphLayout.width) / 2, 0);
            font.setColor(Color.BLACK);
            font.draw(batch, String.format("S: " + roverSpeed), Gdx.graphics.getWidth() - 200, 0);
            font.draw(batch, String.format("D: " + roverTurningDistance), 0, 0);
            batch.end();

        }
    }





    private void connectToRover() {
        // System.out.println("Connecting to rover " + ROVERS[selectedRover].getName());
        roverControl.connect(ROVERS[selectedRover].getFullAddress());
    }

    private void testConnection() {
        if (newSelectedRover != selectedRover) {
            selectedRover = newSelectedRover;
            roverControl.disconnect();
        }
        if (!roverControl.isConnected()) {
            retryCounter -= 1;
            if (retryCounter < 0) {
                retryCounter = 120;
                connectToRover();
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
        leftjoystick.touchDown(screenX, screenY, pointer);
        rightjoystick.touchDown(screenX, screenY, pointer);
        switchLB.touchDown(screenX, screenY, pointer);
        switchLT.touchDown(screenX, screenY, pointer);
        switch2.touchDown(screenX, screenY, pointer);
        button1.touchDown(screenX, screenY, pointer);
        roverSelectButton.touchDown(screenX, screenY, pointer);

        screenController.stickMoved(0, new JoystickState(leftjoystick.getXValue(), leftjoystick.getYValue()));
        screenController.stickMoved(1, new JoystickState(rightjoystick.getXValue(), rightjoystick.getYValue()));

        mouseDown = true;
        return false;
    }

    @Override
    public boolean touchUp(int screenX, int screenY, int pointer, int button) {
        leftjoystick.touchUp(screenX, screenY, pointer);
        rightjoystick.touchUp(screenX, screenY, pointer);
        button1.touchUp(screenX, screenY, pointer);
        roverSelectButton.touchUp(screenX, screenY, pointer);
        mouseDown = false;
        screenController.stickMoved(0, new JoystickState(leftjoystick.getXValue(), leftjoystick.getYValue()));
        screenController.stickMoved(1, new JoystickState(rightjoystick.getXValue(), rightjoystick.getYValue()));
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
