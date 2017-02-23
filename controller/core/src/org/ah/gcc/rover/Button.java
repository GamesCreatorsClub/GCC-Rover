package org.ah.gcc.rover;

import static org.ah.gcc.rover.MathUtil.calcDistance;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;

public class Button {
    private int spaceSize;
    private int x;
    private int y;

    private boolean pressed = false;
    private float size;
    private int pointer;

    public Button(int cellsize, int x, int y, float radius) {
        this.spaceSize = cellsize;
        this.size = radius * cellsize;

        this.x = x * cellsize;
        this.y = Gdx.graphics.getHeight() - y * cellsize;

        this.x -= cellsize / 2;
        this.y -= cellsize / 2;
    }

    public void draw(ShapeRenderer shapeRenderer) {
        if (pressed) {
            shapeRenderer.setColor(Color.DARK_GRAY);
        } else {
            shapeRenderer.setColor(Color.GRAY);
        }

        shapeRenderer.circle(x, y, size);

    }

    public void touchDown(int screenX, int screenY, int pointer) {
        this.pointer = pointer;
        if (calcDistance(screenX, screenY, x, y) < size) {
            pressed = true;
        }
    }

    public void touchDragged(int screenX, int screenY, int pointer) {
        if (pointer == this.pointer && calcDistance(screenX, screenY, x, y) > size) {
            pressed = false;
        }

        if (pointer == this.pointer && calcDistance(screenX, screenY, x, y) < size) {
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
