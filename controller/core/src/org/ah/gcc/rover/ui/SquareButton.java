package org.ah.gcc.rover.ui;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class SquareButton extends ScreenButton{
    private int x;
    private int y;

    private boolean pressed = false;
    private int pointer;
    private int height;
    private int width;

    public SquareButton(int x, int y, int width, int height) {

        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
    }

    public void draw(ShapeRenderer shapeRenderer) {

        if (pressed) {
            shapeRenderer.setColor(Color.DARK_GRAY);
        } else {
            shapeRenderer.setColor(Color.GRAY);
        }

        shapeRenderer.set(ShapeType.Filled);
        shapeRenderer.rect(x, y, width, height);
        shapeRenderer.set(ShapeType.Line);
        shapeRenderer.setColor(Color.BLACK);
        shapeRenderer.rect(x, y, width, height);

    }

    public void touchDown(int screenX, int screenY, int pointer) {
        this.pointer = pointer;
        if (screenX > x && screenX < x + width
                && screenY > y && screenY < y + height) {
            pressed = true;
        }
        if (getListener() != null) {
            getListener().changed(pressed);
        }
    }

    public void touchDragged(int screenX, int screenY, int pointer) {
        this.pointer = pointer;
        if (screenX > x && screenX < x + width
                && screenY > y && screenY < y + height) {
            pressed = true;
        } else {
            pressed = false;
        }
        if (getListener() != null) {
            getListener().changed(pressed);
        }
    }

    public void touchUp(int screenX, int screenY, int pointer) {
        this.pointer = pointer;
        if (screenX > x && screenX < x + width
                && screenY > y && screenY < y + height) {
            pressed = false;
        }
        if (getListener() != null) {
            getListener().changed(pressed);
        }
    }

    public boolean isOn() {
        return pressed;
    }

    public void setState(boolean state) {
        this.pressed = state;
    }
}
