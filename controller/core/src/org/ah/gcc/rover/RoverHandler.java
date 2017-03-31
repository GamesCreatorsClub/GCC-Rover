/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

public interface RoverHandler {

    RoverDetails[] ROVERS = new RoverDetails[] {
            new RoverDetails("Rover 2", "172.24.1.184", 1883),
            new RoverDetails("Rover 3", "172.24.1.185", 1883),
            new RoverDetails("Rover 4", "172.24.1.186", 1883),
            new RoverDetails("Rover 2p", "gcc-wifi-ap", 1884),
            new RoverDetails("Rover 3p", "gcc-wifi-ap", 1885),
            new RoverDetails("Rover 4p", "gcc-wifi-ap", 1886)
    };

    void connect(String url);

    void publish(String topic, String msg);

    void subscribe(String topic, RoverMessageListener listener);

    boolean isConnected();

    void disconnect();

    interface RoverMessageListener {
        void onMessage(String topic, String message);
    }
}
