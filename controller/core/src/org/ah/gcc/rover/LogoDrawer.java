package org.ah.gcc.rover;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.Batch;

public class LogoDrawer {
    private OrthographicCamera camera;
    private Batch batch;
    private int alpha;

    private Texture gccimg;

    private Texture creativesphereimg;

    private Texture bobimg;
    private boolean done = false;

    public LogoDrawer(Batch batch, OrthographicCamera camera) {
        this.batch = batch;
        this.camera = camera;

        gccimg = new Texture("GCCLogo.png");
        creativesphereimg = new Texture("creative-sphere.png");
        bobimg = new Texture("bobclub.png");

    }

    private float calculateScale(Texture texture) {
        float scaleX = Gdx.graphics.getWidth() / texture.getWidth();
        float scaleY = Gdx.graphics.getHeight() / texture.getHeight();
        if (scaleX > scaleY) {
            return scaleY;
        }
        return scaleX;
    }

    public void draw() {
        camera.setToOrtho(false);
        alpha++;

        Gdx.gl.glClearColor(1, 1, 1, 1);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        batch.setProjectionMatrix(camera.combined);
        batch.begin();

        if (alpha < 30) {
            float scale = calculateScale(gccimg);
            int y = (int) ((Gdx.graphics.getHeight() - (gccimg.getHeight() * scale)) / 2);
            int x = (int) ((Gdx.graphics.getWidth() - (gccimg.getWidth() * scale)) / 2);
            batch.draw(gccimg, x, y, gccimg.getWidth() * scale, gccimg.getHeight() * scale);
        } else if (alpha < 60) {
            float scale = Gdx.graphics.getHeight() / creativesphereimg.getHeight();
            int y = (int) ((Gdx.graphics.getHeight() - (creativesphereimg.getHeight() * scale)) / 2);
            int x = (int) ((Gdx.graphics.getWidth() - (creativesphereimg.getWidth() * scale)) / 2);
            batch.draw(creativesphereimg, x, y, creativesphereimg.getWidth() * scale, creativesphereimg.getHeight() * scale);
        } else if (alpha < 90) {
            float scale = Gdx.graphics.getHeight() / bobimg.getHeight();
            int y = (int) ((Gdx.graphics.getHeight() - (bobimg.getHeight() * scale)) / 2);
            int x = (int) ((Gdx.graphics.getWidth() - (bobimg.getWidth() * scale)) / 2);
            batch.draw(bobimg, x, y, bobimg.getWidth() * scale, bobimg.getHeight() * scale);
        } else if (alpha > 120) {
            done = true;
        }

        batch.end();
    }

    public boolean done() {
        return done;
    }
}
