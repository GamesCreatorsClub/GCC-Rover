package org.ah.gcc.rover;

public interface RoverHandler {

    void connect(String url);

    void publish(String topic, String msg);

    boolean isConnected();

    void disconnect();
}
