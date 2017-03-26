package org.ah.gcc.rover.desktop;

import java.util.HashMap;
import java.util.Map;

import org.ah.gcc.rover.RoverHandler;
import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
import org.eclipse.paho.client.mqttv3.MqttCallback;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.MqttPersistenceException;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

public class DesktopRoverControl implements RoverHandler, MqttCallback {

    private MqttAsyncClient client;
    private boolean connected = false;
    private Map<String, RoverHandler.RoverMessageListener[]> listeners = new HashMap<String, RoverHandler.RoverMessageListener[]>();

    @Override
    public void connect(String url) {
        try {
            client = new MqttAsyncClient(url, MqttAsyncClient.generateClientId(), new MemoryPersistence());
            client.connect(
                null,
                new IMqttActionListener() {
                    @Override public void onSuccess(IMqttToken asyncActionToken) {
                        System.out.println("CONNECTED! WOW! YEAH!");
                        connected = true;
                        client.setCallback(DesktopRoverControl.this);
                        for (String topics : listeners.keySet()) {
                            try {
                                client.subscribe(topics, 0);
                            } catch (MqttException e) {
                                e.printStackTrace();
                            }
                        }
                    }

                    @Override public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
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

    @Override
    public void subscribe(String topic, RoverMessageListener listener) {
        RoverMessageListener[] concreteListeners;
        if (listeners.containsKey(topic)) {
            RoverMessageListener[] oldConcreteListeners = listeners.get(topic);
            concreteListeners = new RoverMessageListener[oldConcreteListeners.length + 1];
            System.arraycopy(oldConcreteListeners, 0, concreteListeners, 0, oldConcreteListeners.length);
        } else {
            concreteListeners = new RoverMessageListener[1];
        }
        concreteListeners[concreteListeners.length - 1] = listener;
        listeners.put(topic, concreteListeners);
    }

    @Override
    public void connectionLost(Throwable cause) {
    }

    @Override
    public void messageArrived(String topic, MqttMessage message) throws Exception {
        if (listeners.containsKey(topic)) {
            RoverMessageListener[] concreteListeners = listeners.get(topic);
            for (RoverMessageListener listener : concreteListeners) {
                listener.onMessage(topic, new String(message.getPayload()));
            }
        }
    }

    @Override
    public void deliveryComplete(IMqttDeliveryToken token) {
    }
}
