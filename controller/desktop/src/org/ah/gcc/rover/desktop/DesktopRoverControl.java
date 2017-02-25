package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.RoverControl;
import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.MqttPersistenceException;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

public class DesktopRoverControl implements RoverControl {

    private MqttAsyncClient client;
    private boolean connected = false;
    
    @Override
    public void connect(String url) {
        try {
            client = new MqttAsyncClient(url, MqttAsyncClient.generateClientId(), new MemoryPersistence());
            client.connect(
                null,
                new IMqttActionListener() {
                    @Override
                    public void onSuccess(IMqttToken asyncActionToken) {
                        System.out.println("CONNECTED! WOW! YEAH!");
                        connected = true;
                    }

                    @Override
                    public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
                        System.out.println("Failed to connect... " + exception);
                        exception.printStackTrace();
                    }
                });
        } catch (MqttException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void publish(String topic, String message) {
        if (isConnected()) {
            try {
                client.publish(topic, new MqttMessage(message.getBytes()));
            } catch (MqttPersistenceException e) {
                e.printStackTrace();
                disconnect();
            } catch (MqttException e) {
                e.printStackTrace();
                disconnect();
            }
        }
    }
    
    @Override
    public boolean isConnected() {
        return client != null && connected;
    }

    @Override
    public void disconnect() {
        if (client != null) {
            try {
                client.disconnect();
            } catch (Throwable ignore) { }
            try {
                client.close();
            } catch (Throwable ignore) { }
            connected = false;
            client = null;
        }
    }

}
