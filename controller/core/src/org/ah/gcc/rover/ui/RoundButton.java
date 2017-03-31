/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.ui;

import static org.ah.gcc.rover.MathUtil.calcDistance;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class RoundButton {
    private int x;
    private int y;

    private boolean pressed = false;
    private float radius;
    private int pointer;

    public RoundButton(int x, int y, int radius) {

        this.x = x - radius / 2;
        this.y = Gdx.graphics.getHeight() - y - radius / 2;
    }

    public void draw(ShapeRenderer shapeRenderer) {
        shapeRenderer.set(ShapeType.Filled);

        if (pressed) {
            shapeRenderer.setColor(Color.DARK_GRAY);
        } else {
            shapeRenderer.setColor(Color.GRAY);
        }

        shapeRenderer.circle(x, y, radius);

    }

    public void touchDown(int screenX, int screenY, int pointer) {
        this.pointer = pointer;
        if (calcDistance(screenX, screenY, x, y) < radius) {
            pressed = true;
        }
    }

    public void touchDragged(int screenX, int screenY, int pointer) {
        if (pointer == this.pointer && calcDistance(screenX, screenY, x, y) > radius) {
            pressed = false;
        }

        if (pointer == this.pointer && calcDistance(screenX, screenY, x, y) < radius) {
            pressed = true;
        }
    }

    public void touchUp(int screenX, int screenY, int pointer) {
        if (pointer == this.pointer) {
            pressed = false;
        }
    }

    public boolean isOn() {
        return pressed;
    }

    public void setState(boolean state) {
        this.pressed = state;
    }
}
