package org.ah.gcc.rover.ui;

public abstract class ScreenButton extends AbstractCompontent{
    private ButtonComponentListener listener;

    public void setListener(ButtonComponentListener listener) {
        this.listener = listener;
    }

    public ButtonComponentListener getListener() {
        return listener;
    }
}
