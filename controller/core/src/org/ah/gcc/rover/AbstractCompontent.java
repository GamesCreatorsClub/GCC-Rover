package org.ah.gcc.rover;

import com.badlogic.gdx.graphics.glutils.ShapeRenderer;

public abstract class AbstractCompontent {

    public abstract void draw(ShapeRenderer shapeRenderer);

    public void dragged(int screenX, int screenY, int pointer) {
    }

    public void touchDown(int screenX, int screenY, int pointer) {
    }

    public void touchUp(int screenX, int screenY, int pointer) {
    }
}
