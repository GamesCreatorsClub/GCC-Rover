package org.ah.gcc.rover;

public interface RoverHandler {

    void connect(String url);

    void publish(String topic, String msg);

    void subscribe(String topic, RoverMessageListener listener);

    boolean isConnected();

    void disconnect();

    interface RoverMessageListener {
        void onMessage(String topic, String message);
    }
}
