package org.ah.gcc.rover;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;
import com.badlogic.gdx.math.Vector2;

public class JoyStick {
    private int centreX;
    private int centreY;
    
    private int pointer = -1;
    
    private int x;
    private int y;
    private int spaceSize;
    
    public JoyStick(int size, int x, int y) {
        this.spaceSize = size;
        centreX =  x * size;
        centreY =  Gdx.graphics.getHeight() - y * size;
        
        this.x = x * size;
        this.y = Gdx.graphics.getHeight() - y * size;
    }
    
    public void draw(ShapeRenderer shapeRenderer) {
        shapeRenderer.setColor(0.5f, 0.5f, 0.5f, 1f);
        
        shapeRenderer.set(ShapeType.Line);
        
        shapeRenderer.circle(centreX, centreY, spaceSize * 2);
        shapeRenderer.circle(centreX, centreY, spaceSize);
        
        shapeRenderer.set(ShapeType.Filled);
        shapeRenderer.circle(x, y, spaceSize * 0.75f);
    }
    
    public float getDistanceFromCentre() {
        float distance = RoverController.getDistance(x, y, centreX, centreY);
        distance -= spaceSize;
        
        distance =  distance / (spaceSize * 2);
        
        if (distance < 0) {
            return 0;
        } else {
            return distance;
        }
    }
    
    public double getAngleFromCentre() {
        return Math.atan2((x - centreX), -(y - centreY)) * 180 / Math.PI;
    }
    
    public void dragged(int screenX, int screenY, int pointer) {
        if (this.pointer == pointer) {
            x = screenX;
            y = screenY;
        }
    }
    
    public void touchDown(int screenX, int screenY, int pointer) {
        if (RoverController.getDistance(screenX, screenY, x, y) < spaceSize) {
            this.pointer = pointer;
            
        }
    }
    
    public void touchUp(int screenX, int screenY, int pointer) {
        if (this.pointer == pointer) {
            x = centreX;
            y = centreY;
            this.pointer = -1;
        }
    }
}
