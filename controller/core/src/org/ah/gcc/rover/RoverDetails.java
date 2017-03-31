/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

public class RoverDetails {

    private String name;
    private String address;
    private int port;

    public
    RoverDetails(String name, String address, int port) {
        this.name = name;
        this.address = address;
        this.port = port;
    }

    public String getName() {
        return name;
    }

    public String getAddress() {
        return address;
    }

    public int getPort() {
        return port;
    }

    public String getFullAddress() {
        return "tcp://" + address + ":" + port;
    }

}
