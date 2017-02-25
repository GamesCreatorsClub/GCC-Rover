package org.ah.gcc.rover;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class Switch {
    private int width;
    private int x;
    private int y;
    private Orientation orientation;
    
    private boolean on = false;

    public Switch(int x, int y, int width, Orientation orientation) {
        this.width = width;
        this.orientation = orientation;
        
        this.x = x;
        this.y = Gdx.graphics.getHeight() - y;
    }
    
    public void draw(ShapeRenderer shapeRenderer) {
        shapeRenderer.set(ShapeType.Filled);
        if (orientation == Orientation.HORIZONTAL) {
            if (on) {
                shapeRenderer.setColor(Color.GREEN);
                shapeRenderer.rect(x, y, width / 2, width / 2);
                
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x + width / 2, y, width / 2, width / 2);
            } else {
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y, width / 2, width / 2);
                
                shapeRenderer.setColor(Color.RED);
                shapeRenderer.rect(x + width / 2, y, width / 2, width / 2);
            }
        } else if (orientation == Orientation.VERTICAL) {
            if (on) {
                shapeRenderer.setColor(Color.GREEN);
                shapeRenderer.rect(x, y, width / 2, width / 2);
                
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y + width / 2, width / 2, width / 2);
            } else {
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y, width / 2, width / 2);
                
                shapeRenderer.setColor(Color.RED);
                shapeRenderer.rect(x, y + width / 2, width / 2, width / 2);
            }
        }
        
    }
    
    public void touchDown(int screenX, int screenY, int pointer) {
           if (orientation == Orientation.VERTICAL) {
               if (screenX > x && screenX < x + width / 2
                       && screenY > y && screenY < y + width) {
                   on = !on;
               }
           }
           
           if (orientation == Orientation.HORIZONTAL) {
               if (screenX > x && screenX < x + width
                       && screenY > y && screenY < y + width / 2) {
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
