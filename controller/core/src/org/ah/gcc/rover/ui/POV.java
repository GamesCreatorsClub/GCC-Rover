package org.ah.gcc.rover.ui;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class POV extends AbstractCompontent {

    private int x;
    private int y;
    private int x2;
    private int y2;
    private int size;
    public POV() {
        // TODO Auto-generated constructor stub
    }

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
        shapeRenderer.rect(x, y, size, size);
        shapeRenderer.rect(x - size, y, size, size);
        shapeRenderer.rect(x + size, y, size, size);
        shapeRenderer.rect(x, y + size, size, size);
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
        if (screenX > x && screenX < x + size && screenY > y + size && screenY < y+size+size) {

        } else if (screenX > x && screenX < x + size && screenY > y - size && screenY < y) {

        } else if (screenX > x + size && screenX < x+size+size && screenY > y && screenY < y + size) {

        } else if (screenX > x - size && screenX < x && screenY > y && screenY < y + size) {

        }

    }


    @Override
    public void touchUp(int screenX, int screenY, int pointer) {
    }

}
