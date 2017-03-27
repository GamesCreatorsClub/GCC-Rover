package org.ah.gcc.rover.ui;

import org.ah.gcc.rover.HatComponentListener;
import org.ah.gcc.rover.controllers.JoystickState;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class POV extends AbstractCompontent {

    private int x;
    private int y;
    private int x2;
    private int y2;
    private int size;
    private int wherePressed = 0;
    private HatComponentListener listener;

    public POV(int x, int y, int size) {
        x2 = x;
        this.x = x;
        y2 = y;
        this.y = y;
        this.size = size;

    }

    @Override
    public void draw(ShapeRenderer shapeRenderer) {
        shapeRenderer.set(ShapeType.Line);
        shapeRenderer.setColor(Color.BLACK);
        if (wherePressed == 0) {
            shapeRenderer.set(ShapeType.Filled);
        } else {
            shapeRenderer.set(ShapeType.Line);
        }
        shapeRenderer.rect(x, y, size, size);

        //left
        if (wherePressed == 1) {
            shapeRenderer.set(ShapeType.Filled);
        } else {
            shapeRenderer.set(ShapeType.Line);
        }
        shapeRenderer.rect(x - size, y, size, size);

        //right
        if (wherePressed == 2) {
            shapeRenderer.set(ShapeType.Filled);
        } else {
            shapeRenderer.set(ShapeType.Line);
        }
        shapeRenderer.rect(x + size, y, size, size);

        //up
        if (wherePressed == 3) {
            shapeRenderer.set(ShapeType.Filled);
        } else {
            shapeRenderer.set(ShapeType.Line);
        }
        shapeRenderer.rect(x, y + size, size, size);

        //down
        if (wherePressed == 4) {
            shapeRenderer.set(ShapeType.Filled);
        } else {
            shapeRenderer.set(ShapeType.Line);
        }
        shapeRenderer.rect(x, y - size, size, size);
    }

    public int getY() {
        return y;
    }

    public void setY(int y) {
        this.y = y;
    }

    public int getX() {
        return x;
    }

    public void setX(int x) {
        this.x = x;
    }

    public int getSize() {
        return size;
    }

    public void setSize(int size) {
        this.size = size;
    }

    @Override
    public void touchDown(int screenX, int screenY, int pointer) {
        processClick(screenX, screenY);

    }

    private void processClick(int screenX, int screenY) {
        if (screenX > x && screenX < x + size && screenY > y + size && screenY < y+size+size) {
            wherePressed = 3;
            listener.changed(new JoystickState(0, 1));
        } else if (screenX > x && screenX < x + size && screenY > y - size && screenY < y) {
            wherePressed = 4;
            listener.changed(new JoystickState(0, -1));
        } else if (screenX > x + size && screenX < x+size+size && screenY > y && screenY < y + size) {
            wherePressed = 2;
            listener.changed(new JoystickState(1, 0));
        } else if (screenX > x - size && screenX < x && screenY > y && screenY < y + size) {
            wherePressed = 1;
            listener.changed(new JoystickState(-1, 0));
        }

    }


    @Override
    public void touchUp(int screenX, int screenY, int pointer) {
        wherePressed = 0;
    }

    public void touchDragged(int screenX, int screenY, int pointer) {
        processClick(screenX, screenY);
    }

    public void setListener(HatComponentListener listener) {
        this.listener = listener;

    }

}
