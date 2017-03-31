/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover.ui;

import org.ah.gcc.rover.MathUtil;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType;

public class ExpoGraph {

    private int x;
    private int y;
    private int width;
    private int height;
    private float percentage;
    private float value;
    private Color color = Color.GREEN;

    public ExpoGraph(int x, int y, int width, int height) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
    }

    public void draw(ShapeRenderer shapeRenderer) {

        shapeRenderer.set(ShapeType.Filled);
        shapeRenderer.setColor(1.0f, 1.0f, 1.0f, 1f);
        shapeRenderer.rect(x, y, width - 1, height - 1);

        shapeRenderer.set(ShapeType.Line);
        shapeRenderer.setColor(0.5f, 0.5f, 0.5f, 1f);
        shapeRenderer.rect(x, y, width - 1, height - 1);

        shapeRenderer.setColor(0f, 0f, 0f, 1f);
        // shapeRenderer.line(x,  y, x +width, y+height);

        int py = -1;
        for (int i = 0; i < width; i++) {
            float in = (float)i / (float)(width - 1);
            in = calculate(in);

            int ny = (int)((float)y + height - in * height);
            int nx = i + x;
            if (py >= 0) {
                int px = nx - 1;
                shapeRenderer.line(px, py, nx, ny);
            }
            py = ny;
        }

        int pos = (int)((width - 1) * value) + x;
        shapeRenderer.setColor(color);
        shapeRenderer.line(pos, y, pos, y + height - 1);
    }

    public float getPercentage() {
        return percentage;
    }

    public void setPercentage(float percentage) {
        this.percentage = percentage;
    }

    public float getValue() {
        return value;
    }

    public void setValue(float value) {
        this.value = Math.abs(value);
    }

    public float calculate(float input) {
        return MathUtil.calculateExpo(input, percentage);
    }
}
