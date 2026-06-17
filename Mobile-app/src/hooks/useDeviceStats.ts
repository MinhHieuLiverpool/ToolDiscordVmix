import { useState, useEffect, useRef } from 'react';
import { NativeModules } from 'react-native';
import * as Device from 'expo-device';
import { DeviceStats } from '../types/monitor';

const { DeviceMonitor } = NativeModules;

export function useDeviceStats() {
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [stats, setStats] = useState<DeviceStats | null>(null);
  const [wanIp, setWanIp] = useState<string>('-');
  const [pingStatus, setPingStatus] = useState<string>('-');
  const [cpuLoad, setCpuLoad] = useState<number>(0);
  const [pingHistory, setPingHistory] = useState<number[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isFallbackMode, setIsFallbackMode] = useState<boolean>(false);
  const [scanTime, setScanTime] = useState<number>(0);
  const [deviceName, setDeviceName] = useState<string>('Detecting...');

  const metricsIntervalRef = useRef<any>(null);
  const timerIntervalRef = useRef<any>(null);

  const getDeviceModel = () => {
    const brand = Device.brand ? Device.brand.toUpperCase() : '';
    const model = Device.modelName || 'Device';
    if (brand && !model.toUpperCase().startsWith(brand)) {
      return `${brand} ${model}`;
    }
    return model;
  };

  const stopScanning = () => {
    if (metricsIntervalRef.current) {
      clearInterval(metricsIntervalRef.current);
      metricsIntervalRef.current = null;
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setIsScanning(false);
  };

  const updateMetrics = async () => {
    if (DeviceMonitor) {
      setIsFallbackMode(false);
      try {
        const data: DeviceStats = await DeviceMonitor.getDeviceStats();
        setStats(data);

        const cpuUsage: number = await DeviceMonitor.getCpuUsage();
        setCpuLoad(Math.round(cpuUsage));

        if (data.gatewayIp) {
          const pingTimeStr: string = await DeviceMonitor.pingGateway(data.gatewayIp);
          setPingStatus(pingTimeStr === 'Timeout' ? 'Timeout' : `${pingTimeStr} ms`);
          
          if (pingTimeStr !== 'Timeout') {
            const numValue = parseFloat(pingTimeStr);
            if (!isNaN(numValue)) {
              setPingHistory(prev => {
                const updated = [...prev, numValue];
                return updated.slice(-10);
              });
            }
          }
        }
      } catch (err) {
        console.error('Error fetching native metrics:', err);
      }
    } else {
      setIsFallbackMode(true);
      
      const totalRam = Device.totalMemory || (8 * 1024 * 1024 * 1024);
      const randomUsagePercent = 40 + Math.floor(Math.random() * 20);
      const usedRam = (totalRam * randomUsagePercent) / 100;
      const freeRam = totalRam - usedRam;

      const mockStats: DeviceStats = {
        localIp: '192.168.1.15',
        macAddress: '02:00:00:00:00:00 (Expo Go)',
        gatewayIp: '192.168.1.1',
        cpuModel: Device.modelName || 'Simulated Processor',
        cpuCores: Device.supportedCpuArchitectures?.length || 8,
        ramTotal: totalRam,
        ramFree: freeRam,
        ramUsed: usedRam,
        ramUsagePercent: randomUsagePercent,
        txSpeedMbps: parseFloat((0.5 + Math.random() * 4.5).toFixed(2)),
        rxSpeedMbps: parseFloat((1.0 + Math.random() * 24.0).toFixed(2)),
      };
      setStats(mockStats);

      const simulatedCpu = 12 + Math.floor(Math.random() * 25);
      setCpuLoad(simulatedCpu);

      const simulatedPing = 1 + Math.floor(Math.random() * 6);
      setPingStatus(`${simulatedPing} ms`);
      
      setPingHistory(prev => {
        const updated = [...prev, simulatedPing];
        return updated.slice(-10);
      });
    }
  };

  const startScanning = async () => {
    setLoading(true);
    stopScanning();
    setScanTime(0);

    try {
      fetch('https://api.ipify.org?format=json')
        .then(res => res.json())
        .then(data => setWanIp(data.ip || '-'))
        .catch(() => setWanIp('-'));

      await updateMetrics();
      setIsScanning(true);

      // 1s timer stopwatch
      timerIntervalRef.current = setInterval(() => {
        setScanTime(prev => prev + 1);
      }, 1000);

      // 2s metrics updater
      metricsIntervalRef.current = setInterval(() => {
        updateMetrics();
      }, 2000);

    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Detect device model name on mount
  useEffect(() => {
    setDeviceName(getDeviceModel());
    return () => {
      stopScanning();
    };
  }, []);

  return {
    isScanning,
    stats,
    wanIp,
    pingStatus,
    cpuLoad,
    pingHistory,
    loading,
    isFallbackMode,
    scanTime,
    deviceName,
    startScanning,
    stopScanning,
  };
}
