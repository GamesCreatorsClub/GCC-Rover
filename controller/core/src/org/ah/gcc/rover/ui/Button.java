package org.ah.gcc.rover.ui;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class Button extends ScreenButton {
    private int x;
    private int y;
    private int width;
    private int height;
    private ButtonCallback callback;

    private boolean pressed = false;
    private int pointer;

    public Button(int x, int y, int width, int height, ButtonCallback callback) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.callback = callback;
    }

    public void draw(ShapeRenderer shapeRenderer) {
        shapeRenderer.set(ShapeType.Filled);

        if (pressed) {
            shapeRenderer.setColor(Color.DARK_GRAY);
        } else {
            shapeRenderer.setColor(Color.GRAY);
        }

        shapeRenderer.rect(x, y, width, height);

    }

    public void touchDown(int screenX, int screenY, int pointer) {
        this.pointer = pointer;
        if (screenX >= x && screenX <= x + width && screenY >= y && screenY < y + height) {
            boolean previousState = pressed;
            pressed = true;
            if (previousState != pressed) {
                callback.invoke(pressed);
            }
        }
    }

    public void touchDragged(int screenX, int screenY, int pointer) {
    }

    public void touchUp(int screenX, int screenY, int pointer) {
        if (pointer == this.pointer) {
            boolean previousState = pressed;
            pressed = false;
            if (previousState != pressed) {
                callback.invoke(pressed);
            }
        }
    }

    public boolean isOn() {
        return pressed;
    }

    public void setState(boolean state) {
        this.pressed = state;
    }

    public static interface ButtonCallback {
        void invoke(boolean state);
    }
}
