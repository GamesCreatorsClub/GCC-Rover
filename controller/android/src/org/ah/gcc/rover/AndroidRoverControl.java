package org.ah.gcc.rover;

import org.eclipse.paho.android.service.MqttAndroidClient;
import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.MqttPersistenceException;

import android.content.Context;

public class AndroidRoverControl implements RoverControl {

    private Context applicationContext;
    private MqttAndroidClient client;
    private boolean connected;
    
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
}
