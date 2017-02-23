package org.ah.gcc.rover.desktop;

import org.ah.gcc.rover.RoverControl;
import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.MqttPersistenceException;

public class DesktopRoverControl implements RoverControl {

    private MqttAsyncClient client;
    private boolean connected = false;
    
    @Override
    public void connect(String url) {
        try {
//            disconnect();
            client = new MqttAsyncClient("tcp://172.24.1.184:1883", MqttAsyncClient.generateClientId());
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

    public void disconnect() {
        if (client != null) {
            try {
                client.disconnect();
            } catch (MqttException ignore) {

            }
            try {
                client.close();
            } catch (MqttException ignore) {

            }
        }
    }

}
