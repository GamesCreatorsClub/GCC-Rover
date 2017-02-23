package org.ah.gcc.rover;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;

import sun.print.resources.serviceui;

public class Switch {
    private int spaceSize;
    private int x;
    private int y;
    private Orientation orientation;
    
    private boolean on = false;

    public Switch(int cellsize, int x, int y, Orientation orientation) {
        this.spaceSize = cellsize;
        this.orientation = orientation;
        
        this.x = x * cellsize;
        this.y = Gdx.graphics.getHeight() - y * cellsize;
    }
    
    public void draw(ShapeRenderer shapeRenderer) {
        if (orientation == Orientation.HORIZONTAL) {
            if (on) {
                shapeRenderer.setColor(Color.GREEN);
                shapeRenderer.rect(x, y, spaceSize, spaceSize);
                
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x + spaceSize, y, spaceSize, spaceSize);
            } else {
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y, spaceSize, spaceSize);
                
                shapeRenderer.setColor(Color.RED);
                shapeRenderer.rect(x + spaceSize, y, spaceSize, spaceSize);
            }
        } else if (orientation == Orientation.VERTICAL) {
            if (on) {
                shapeRenderer.setColor(Color.GREEN);
                shapeRenderer.rect(x, y, spaceSize, spaceSize);
                
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, spaceSize + y, spaceSize, spaceSize);
            } else {
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y, spaceSize, spaceSize);
                
                shapeRenderer.setColor(Color.RED);
                shapeRenderer.rect(x, y + spaceSize, spaceSize, spaceSize);
            }
        }
        
    }
    
    public void touchDown(int screenX, int screenY, int pointer) {
           if (orientation == Orientation.VERTICAL) {
               if (screenX > x && screenX < x + spaceSize 
                       && screenY > y && screenY < y + spaceSize * 2) {
                   on = !on;
               }
           }
           
           if (orientation == Orientation.HORIZONTAL) {
               if (screenX > x && screenX < x + spaceSize * 2
                       && screenY > y && screenY < y + spaceSize) {
                   on = !on;
               }
           }
    }
    
    
    public boolean isOn() {
        return on;
    }

    public void setState(boolean state) {
        this.on = state;
    }
}
