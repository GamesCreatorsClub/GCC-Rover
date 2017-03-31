/*
 * Copyright 2016-2017 Games Creators Club
 *
 * MIT License
 *
 */
package org.ah.gcc.rover;

import java.util.HashMap;
import java.util.Map;

import org.eclipse.paho.android.service.MqttAndroidClient;
import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttCallback;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.MqttPersistenceException;

import android.content.Context;

public class AndroidRoverControl implements RoverHandler, MqttCallback {

    private Context applicationContext;
    private MqttAndroidClient client;
    private boolean connected;
    private Map<String, RoverHandler.RoverMessageListener[]> listeners = new HashMap<String, RoverHandler.RoverMessageListener[]>();

    public AndroidRoverControl(Context applicationContext) {
        this.applicationContext = applicationContext;
    }

    @Override
    public void connect(String url) {
        connected = false;
        String clientId = MqttClient.generateClientId();
        client = new MqttAndroidClient(applicationContext, url, clientId);

        try {
            MqttConnectOptions options = new MqttConnectOptions();
            options.setMqttVersion(MqttConnectOptions.MQTT_VERSION_3_1);
            IMqttToken token = client.connect(options);
            token.setActionCallback(new IMqttActionListener() {
                @Override
                public void onSuccess(IMqttToken asyncActionToken) {
                    System.out.println("CONNECTED! WOW! YEAH!");
                    connected = true;
                    client.setCallback(AndroidRoverControl.this);
                    for (String topics : listeners.keySet()) {
                        try {
                            client.subscribe(topics, 0);
                        } catch (MqttException e) {
                            e.printStackTrace();
                        }
                    }
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
                // throw new RuntimeException(e);
            } catch (MqttException e) {
                e.printStackTrace();
                // throw new RuntimeException(e);
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
