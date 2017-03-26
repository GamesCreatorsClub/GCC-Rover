package org.ah.gcc.rover.ui;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class Switch {
    private int width;
    private int x;
    private int y;
    private Orientation orientation;

    private boolean on = false;
    private SwitchComponentListener listener;

    public Switch(int x, int y, int width, Orientation orientation) {
        this.width = width * 2;
        this.orientation = orientation;

        this.x = x;
        this.y = y;
        // this.y = Gdx.graphics.getHeight() - y;
    }

    public void draw(ShapeRenderer shapeRenderer) {
        if (orientation == Orientation.HORIZONTAL) {
            if (on) {
                shapeRenderer.set(ShapeType.Filled);
                shapeRenderer.setColor(Color.GREEN);
                shapeRenderer.rect(x, y, width / 2, width / 2);

                shapeRenderer.set(ShapeType.Line);

                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x + width / 2, y, width / 2, width / 2);
            } else {
                shapeRenderer.set(ShapeType.Line);
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y, width / 2, width / 2);

                shapeRenderer.set(ShapeType.Filled);
                shapeRenderer.setColor(Color.RED);
                shapeRenderer.rect(x + width / 2, y, width / 2, width / 2);
            }
        } else if (orientation == Orientation.VERTICAL) {
            if (on) {
                shapeRenderer.setColor(Color.GREEN);
                shapeRenderer.rect(x, y, width, width / 2);
                shapeRenderer.rect(x, y, width / 2, width / 2);

                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y + width / 2, width, width / 2);
            } else {
                shapeRenderer.setColor(Color.DARK_GRAY);
                shapeRenderer.rect(x, y, width, width / 2);
                shapeRenderer.rect(x, y, width / 2, width / 2);

                shapeRenderer.setColor(Color.RED);
                shapeRenderer.rect(x, y + width / 2, width, width / 2);
            }
        }

    }

    public void touchDown(int screenX, int screenY, int pointer) {
           if (orientation == Orientation.VERTICAL) {
               if (screenX > x && screenX < x + width
                       && screenY > y && screenY < y + width / 2) {
                   on = !on;
               }
           }

           if (orientation == Orientation.HORIZONTAL) {
               if (screenX > x && screenX < x + width
                       && screenY > y && screenY < y + width / 2) {
                   on = !on;
               }
           }

           if (listener != null) {
               listener.changed(on);
           }
    }


    public boolean isOn() {
        return on;
    }

    public void setState(boolean state) {
        this.on = state;
    }

    public void setListener(SwitchComponentListener listener) {
        this.listener = listener;
    }
}
