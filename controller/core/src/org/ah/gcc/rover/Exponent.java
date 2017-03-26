package org.ah.gcc.rover;

public class Exponent {
    private float percentage;
    private float value;

    public Exponent() {
        // TODO Auto-generated constructor stub
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
