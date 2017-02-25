package org.ah.gcc.rover;

public class MathUtil {

    private MathUtil() {
    }

    public static float calcDistance(float x1, float y1, float x2, float y2) {
        return (float) Math.sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
    }

    public static float calculateExpo(float input, float expoPercentage) {
        if (input >= 0) {
            return input * input * expoPercentage + input * (1.0f - expoPercentage);
        } else {
            return - input * input * expoPercentage + input * (1.0f - expoPercentage);
        }
    }
}
