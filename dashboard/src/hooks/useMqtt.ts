import { useEffect, useRef, useCallback, useState } from 'react';
import mqtt, { MqttClient } from 'mqtt';
import { useDispatch } from 'react-redux';
import { updateHealth } from '../store/assetsSlice';

const ENV_BROKER = import.meta.env.VITE_MQTT_BROKER_URL;
if (import.meta.env.PROD && !ENV_BROKER) {
    throw new Error('VITE_MQTT_BROKER_URL must be set for production builds');
}
const MQTT_BROKER = ENV_BROKER ?? 'ws://localhost:9883';

export function useMqtt() {
    const clientRef = useRef<MqttClient | null>(null);
    const dispatch = useDispatch();
    const [isConnected, setIsConnected] = useState(false);

    const connect = useCallback(() => {
        if (clientRef.current) return;

        const client = mqtt.connect(MQTT_BROKER, {
            clientId: `adaptivx-dashboard-${Date.now()}`,
            reconnectPeriod: 5000,
        });

        client.on('connect', () => {
            console.log('MQTT connected');
            setIsConnected(true);
            client.subscribe('adaptivx/health/#');
            client.subscribe('adaptivx/capability/#');
        });

        client.on('message', (topic, payload) => {
            try {
                const data = JSON.parse(payload.toString());

                if (topic.startsWith('adaptivx/health/')) {
                    dispatch(updateHealth({
                        assetId: data.asset_id,
                        healthIndex: data.health_index,
                        healthConfidence: data.health_confidence ?? 1.0,
                        anomalyScore: data.anomaly_score ?? 0,
                        physicsResidual: data.physics_residual ?? 0,
                        lastUpdate: data.timestamp ?? new Date().toISOString(),
                    }));
                }
            } catch (e) {
                console.error('Failed to parse MQTT message:', e);
            }
        });

        client.on('error', (err) => {
            console.error('MQTT error:', err);
        });

        client.on('close', () => {
            setIsConnected(false);
        });

        clientRef.current = client;
    }, [dispatch]);

    const disconnect = useCallback(() => {
        if (clientRef.current) {
            clientRef.current.end();
            clientRef.current = null;
            setIsConnected(false);
        }
    }, []);

    useEffect(() => {
        connect();
        return disconnect;
    }, [connect, disconnect]);

    return { connect, disconnect, isConnected };
}
