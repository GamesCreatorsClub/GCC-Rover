package org.ah.gcc.rover;

import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;
import com.badlogic.gdx.math.Vector2;

public class JoyStick {
    private int centreX;
    private int centreY;
    
    private int pointer = -1;
    
    private int x;
    private int y;
    
    public JoyStick(int x, int y) {
        centreX = x;
        centreY = y;
        
        this.x = x;
        this.y = y;
    }
    
    public void draw(ShapeRenderer shapeRenderer) {
        shapeRenderer.setColor(0.5f, 0.5f, 0.5f, 1f);
        
        shapeRenderer.set(ShapeType.Line);
        
        shapeRenderer.circle(centreX, centreY, 64f);
        shapeRenderer.circle(centreX, centreY, 32f);
        
        shapeRenderer.set(ShapeType.Filled);
        shapeRenderer.circle(x, y, 24f);
    }
    
    public float getDistanceFromCentre() {
        return RoverController.getDistance(x, y, centreX, centreY);
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
        if (RoverController.getDistance(screenX, screenY, x, y) < 32) {
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
