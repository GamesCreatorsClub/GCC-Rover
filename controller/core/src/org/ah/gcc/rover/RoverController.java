package org.ah.gcc.rover;

import com.badlogic.gdx.ApplicationAdapter;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.InputMultiplexer;
import com.badlogic.gdx.InputProcessor;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.input.GestureDetector;
import com.badlogic.gdx.input.GestureDetector.GestureListener;
import com.badlogic.gdx.math.Vector2;

public class RoverController extends ApplicationAdapter implements InputProcessor, GestureListener {
    
    private RoverControl roverControl;

    private SpriteBatch batch;
    private Texture img;

    private ShapeRenderer shapeRenderer;
    
    private OrthographicCamera camera;
    
    private InputMultiplexer inputMultiplexer;
    
    private BitmapFont font;
    
    private JoyStick leftjoystick;
    private JoyStick rightjoystick;

    private int retryCounter = 0;
    private int messageCounter = 10;
    
    private int roverSpeed = 0;
    private int roverTurningDistance = 0;

    private double cellSize;

    private Switch switch1;

    private Switch switch2;

    private Button button1;

    public RoverController(RoverControl roverControl) {
        this.roverControl = roverControl;
    }

    @Override
    public void create() {
        font = new BitmapFont(true);
        font.setColor(Color.BLACK);
        batch = new SpriteBatch();
        img = new Texture("badlogic.jpg");
        camera = new OrthographicCamera(Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
        
        cellSize = Gdx.graphics.getWidth() / 20;

        shapeRenderer = new ShapeRenderer();
        
        leftjoystick = new JoyStick((int)cellSize * 8, (int)cellSize * 4, (int)cellSize * 4);
        rightjoystick = new JoyStick((int)cellSize * 8, (int)cellSize * 16, (int)cellSize * 4);
        
        button1 = new Button((int) cellSize, 12, 3, 0.5f);

        
        switch1 = new Switch((int) cellSize, 3, 10, Orientation.HORIZONTAL);
        switch1.setState(true);
        switch2 = new Switch((int) cellSize, 17, 10, Orientation.VERTICAL);

        
        inputMultiplexer = new InputMultiplexer();
        inputMultiplexer.addProcessor(this);
        inputMultiplexer.addProcessor(new GestureDetector(this));
        Gdx.input.setInputProcessor(inputMultiplexer);
    }

    public void processJoysticks() {
        if (leftjoystick.getDistanceFromCentre() < 0.1f && rightjoystick.getDistanceFromCentre() > 0.1f) {
            if (switch1.isOn()) {
                roverSpeed = calcRoverSpeed(rightjoystick.getDistanceFromCentre());
                roverControl.publish("move/drive", String.format("%.2f %.0f", rightjoystick.getAngleFromCentre(), (float)(roverSpeed)));
            } else {
                roverSpeed = calcRoverSpeed(rightjoystick.getDistanceFromCentre());
                roverControl.publish("move/orbit", roverSpeed + "");
            }
        } else if (leftjoystick.getDistanceFromCentre() > 0.1f && rightjoystick.getDistanceFromCentre() > 0.1f) {
            roverSpeed = -calcRoverSpeed(rightjoystick.getYValue());
            roverTurningDistance = calcRoverDistance(leftjoystick.getXValue());
            roverControl.publish("move/steer", roverTurningDistance + " " + roverSpeed);
        } else if (leftjoystick.getDistanceFromCentre() > 0.1f) {
            roverSpeed = calcRoverSpeed(leftjoystick.getXValue()) / 4;
            roverControl.publish("move/rotate", Integer.toString(roverSpeed));
            //            if (leftjoystick.getAngleFromCentre() < 180) {
            //                roverSpeed = calcRoverSpeed(leftjoystick.getDistanceFromCentre()) / 4;
            //                roverControl.publish("move/rotate", roverSpeed + "");
            //            } else {
            //                roverSpeed = calcRoverSpeed(-leftjoystick.getDistanceFromCentre()) / 4;
            //                roverControl.publish("move/rotate", roverSpeed + "");
            //            }
        } else {
            roverControl.publish("move/drive", rightjoystick.getAngleFromCentre() + " 0");
            roverSpeed = 0;
            roverControl.publish("move/stop", "0");
        }
    }

    @Override
    public void render() {
        loop();
        testConnection();
        
        String connectedStr = "Not connected";
        if (roverControl.isConnected()) {
            connectedStr = "Connected";
        }

        messageCounter--;
        if (messageCounter < 0) {
            messageCounter = 5;
            processJoysticks();
        }

        camera.setToOrtho(true);
        
        Gdx.gl.glClearColor(1, 1, 1, 1);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        batch.setProjectionMatrix(camera.combined);
        shapeRenderer.setProjectionMatrix(camera.combined);
        shapeRenderer.setAutoShapeType(true);

        batch.begin();
        font.draw(batch, connectedStr, 50, 50);
        font.draw(batch, "Speed: " + roverSpeed + " : " + rightjoystick.getYValue(), 300, 50);
        font.draw(batch, "Distance: " + roverTurningDistance + " : " + leftjoystick.getXValue(), 500, 50);
        batch.end();

        shapeRenderer.begin();
        shapeRenderer.setColor(Color.FIREBRICK);
        for (int x = 0; x < Gdx.graphics.getWidth(); x = (int) (x + cellSize)) {
            shapeRenderer.line(x, 0, x, Gdx.graphics.getHeight());
        }
        for (int y = Gdx.graphics.getHeight(); y > 0 ; y = (int) (y - cellSize)) {
            shapeRenderer.line(0, y, Gdx.graphics.getWidth(), y);
        }
        
        shapeRenderer.setColor(Color.BLACK);
        
        leftjoystick.draw(shapeRenderer);
        rightjoystick.draw(shapeRenderer);
        button1.draw(shapeRenderer);
        switch1.draw(shapeRenderer);
        switch2.draw(shapeRenderer);
        
        shapeRenderer.end();
    }
    
    private int calcRoverSpeed(float speed) {
        return (int)(speed * 150);
        //        return (int)(speed * speed * 300);
    }
    
    private int calcRoverDistance(float distance) {
        if (distance >= 0) {
            // distance = distance * distance;
            distance = Math.abs(distance);
            distance = 1.0f - distance;
            distance = distance + 0.1f;
            distance = distance * 500f;
        } else {
            // distance = distance * distance;
            distance = Math.abs(distance);
            distance = 1.0f - distance;
            distance = distance + 0.1f;
            distance = - distance * 500f;
        }
        
        return (int)distance;
    }    
    
    private void connectToRover() {
        System.out.println("Connecting to rover");
        roverControl.connect("tcp://172.24.1.184:1883");
    }
    
    private void loop() {
        
    }
    
    private void testConnection() {
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
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean keyUp(int keycode) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean keyTyped(char character) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean touchDown(int screenX, int screenY, int pointer, int button) {
        leftjoystick.touchDown(screenX, screenY, pointer);
        rightjoystick.touchDown(screenX, screenY, pointer);
        switch1.touchDown(screenX, screenY, pointer);
        switch2.touchDown(screenX, screenY, pointer);
        button1.touchDown(screenX, screenY, pointer);
        return false;
    }

    @Override
    public boolean touchUp(int screenX, int screenY, int pointer, int button) {
        leftjoystick.touchUp(screenX, screenY, pointer);
        rightjoystick.touchUp(screenX, screenY, pointer);
        button1.touchUp(screenX, screenY, pointer);
        return false;
    }

    @Override
    public boolean touchDragged(int screenX, int screenY, int pointer) {
        leftjoystick.dragged(screenX, screenY, pointer);
        rightjoystick.dragged(screenX, screenY, pointer);
        button1.touchDragged(screenX, screenY, pointer);
        return false;
    }

    @Override
    public boolean mouseMoved(int screenX, int screenY) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean scrolled(int amount) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean touchDown(float x, float y, int pointer, int button) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean tap(float x, float y, int count, int button) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean longPress(float x, float y) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean fling(float velocityX, float velocityY, int button) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean pan(float x, float y, float deltaX, float deltaY) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean panStop(float x, float y, int pointer, int button) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean zoom(float initialDistance, float distance) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public boolean pinch(Vector2 initialPointer1, Vector2 initialPointer2, Vector2 pointer1, Vector2 pointer2) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public void pinchStop() {
        // TODO Auto-generated method stub
        
    }
}
