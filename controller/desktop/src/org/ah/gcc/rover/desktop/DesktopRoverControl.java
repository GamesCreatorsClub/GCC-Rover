package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.RoverControl;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.MqttPersistenceException;

public class DesktopRoverControl implements RoverControl {

    private MqttClient client;
    
    @Override
    public void connect(String url) {
        try {
            client = new MqttClient("tcp://172.24.1.184:1883", "client");
            client.connect();
            System.out.print("client.isConnected=" + client.isConnected());
        } catch (MqttException e) {
            e.printStackTrace();
//            throw new RuntimeException(e);
        }
    }

    @Override
    public void publish(String topic, String message) {
        if (client != null) {
            try {
                client.publish(topic, new MqttMessage(message.getBytes()));
            } catch (MqttPersistenceException e) {
                e.printStackTrace();
//                throw new RuntimeException(e);
            } catch (MqttException e) {
                e.printStackTrace();
//                throw new RuntimeException(e);
            }
        }
    }
    
    @Override
    public boolean isConnected() {
        return client != null && client.isConnected();
    }


}
