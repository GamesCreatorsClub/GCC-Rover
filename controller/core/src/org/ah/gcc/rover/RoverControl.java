package org.ah.gcc.rover;

public interface RoverControl {

    void connect(String url);
    
    void publish(String topic, String msg);
    
    boolean isConnected();
}
