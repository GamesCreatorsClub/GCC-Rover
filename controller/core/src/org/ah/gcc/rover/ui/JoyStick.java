package org.ah.gcc.rover.ui;

import static org.ah.gcc.rover.MathUtil.calcDistance;

import org.ah.gcc.rover.JoystickComponentListener;
import org.ah.gcc.rover.controllers.JoystickState;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class JoyStick {
    private int centreX;
    private int centreY;

    private int pointer = -1;

    private int x;
    private int y;
    private int spaceSize;
    private int inactiveSize;
    private int padSize;

    private JoystickComponentListener listener;

    public JoyStick(int spaceSize, int inactiveSize, int padSize, int x, int y) {
        this.spaceSize = spaceSize;
        this.inactiveSize = inactiveSize;
        this.padSize = padSize;
        centreX =  x;
        centreY =  Gdx.graphics.getHeight() - y;

        this.x = x;
        this.y = Gdx.graphics.getHeight() - y;
    }

    public JoyStick(int spaceSize, int x, int y) {
        this(spaceSize, (int)((spaceSize / 2) * 0.65), (int)((spaceSize / 2) * 0.50), x, y);
    }

    public void draw(ShapeRenderer shapeRenderer) {
        shapeRenderer.setColor(0.5f, 0.5f, 0.5f, 1f);

        shapeRenderer.set(ShapeType.Line);

        shapeRenderer.circle(centreX, centreY, spaceSize / 2);

        shapeRenderer.setColor(0.25f, 0.25f, 0.25f, 1f);
        shapeRenderer.circle(centreX, centreY, spaceSize / 2 - padSize / 2);
        shapeRenderer.circle(centreX, centreY, inactiveSize / 2);

        shapeRenderer.set(ShapeType.Filled);
        shapeRenderer.circle(x, y, padSize / 2);
    }

    public float getXValue() {
        float min = inactiveSize / 2;
        float max = (spaceSize - padSize) / 2 - min;
        float x = this.x - centreX;

        if (Math.abs(x) <= min) {
            return 0f;
        }

        if (x >= 0) {
            return (x - min) / max;
        } else {
            return (x + min) / max;
        }
    }

    public float getYValue() {
        float min = inactiveSize / 2;
        float max = (spaceSize - padSize) / 2 - min;
        float y = this.y - centreY;

        if (Math.abs(y) <= min) {
            return 0f;
        }

        if (y >= 0) {
            return (y - min) / max;
        } else {
            return (y + min) / max;
        }
    }

    public float getDistanceFromCentre() {
        float d1 = calcDistanceFromTheCentre(x, y);
        float min = inactiveSize / 2;
        float max = (spaceSize - padSize) / 2 - min;

        if (Math.abs(d1) <= min) {
            return 0f;
        }

        return (d1 - min) / max;
    }

    public double getAngleFromCentre() {
        return calcAngleAtPointFromCentre(x, y) * 180 / Math.PI;
    }

    public void setValues(float nx, float ny) {
        if (Math.abs(nx) > 0.02f || Math.abs(ny) > 0.02f) {
            updateCoordinates(
                    (int) (centreX + (nx * (spaceSize - inactiveSize) / 2 + Math.signum(nx) * padSize / 2)),
                    (int) (centreY + (ny * (spaceSize - inactiveSize) / 2 + Math.signum(ny) * padSize / 2)));
        } else {
            this.x = centreX;
            this.y = centreY;
        }
    }

    public void dragged(int screenX, int screenY, int pointer) {
        if (this.pointer == pointer) {
            updateCoordinates(screenX, screenY);
            fireChanged();
        }
    }

    public void touchDown(int screenX, int screenY, int pointer) {
        if (calcDistance(screenX, screenY, x, y) <= spaceSize / 2) {
            this.pointer = pointer;
        }
    }

    public void touchUp(int screenX, int screenY, int pointer) {
        if (this.pointer == pointer) {
            x = centreX;
            y = centreY;
            this.pointer = -1;
        }
    }

    private void updateCoordinates(int nx, int ny) {
        float distance = calcDistanceFromTheCentre(nx, ny);
        if (distance < spaceSize / 2 - padSize / 2) {
            x = nx;
            y = ny;
        } else {
            double angle = calcAngleAtPointFromCentre(nx, ny);
            distance = spaceSize / 2 - padSize / 2;
            x = (int)(-distance * Math.sin(-angle)) + centreX;
            y = (int)(-distance * Math.cos(-angle)) + centreY;
        }
    }

    private double calcAngleAtPointFromCentre(int x, int y) {
        return Math.atan2((x - centreX), -(y - centreY));
    }

    private float calcDistanceFromTheCentre(float x, float y) {
        return calcDistance(centreX, centreY, x, y);
    }

    public void setListener(JoystickComponentListener listener) {
        this.listener = listener;
    }

    private void fireChanged() {
        if (listener != null) {
            listener.changed(new JoystickState(getXValue(), getYValue()));
        }
    }
}
