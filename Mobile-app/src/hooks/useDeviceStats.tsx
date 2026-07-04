import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { NativeModules, AppState } from 'react-native';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { DeviceStats, BatteryInfo } from '../types/monitor';

const { DeviceMonitor } = NativeModules;

interface DeviceStatsContextType {
  isScanning: boolean;
  stats: DeviceStats | null;
  wanIp: string;
  pingGateway: string;
  ping8888: string;
  savedServerIp: string;
  saveServerIp: (ip: string) => void;
  serverPing: string;
  cpuLoad: number;
  loading: boolean;
  isFallbackMode: boolean;
  scanTime: number;
  deviceName: string;
  batteryInfo: BatteryInfo;
  networkType: string;
  fps: number;
  packetLoss: number;
  startScanning: () => Promise<void>;
  stopScanning: () => void;
  nameDevice: string;
  saveNameDevice: (name: string) => void;
}

const DeviceStatsContext = createContext<DeviceStatsContextType | undefined>(undefined);

export function DeviceStatsProvider({ children }: { children: React.ReactNode }) {
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [stats, setStats] = useState<DeviceStats | null>(null);
  const [wanIp, setWanIp] = useState<string>('-');
  const [pingGateway, setPingGateway] = useState<string>('-');
  const [ping8888, setPing8888] = useState<string>('-');
  const [savedServerIp, setSavedServerIp] = useState<string>('');
  const savedServerIpRef = useRef<string>('');
  const [nameDevice, setNameDevice] = useState<string>('');
  const nameDeviceRef = useRef<string>('');
  const [serverPing, setServerPing] = useState<string>('-');
  const [cpuLoad, setCpuLoad] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [isFallbackMode, setIsFallbackMode] = useState<boolean>(false);
  const [scanTime, setScanTime] = useState<number>(0);
  const [deviceName, setDeviceName] = useState<string>('Detecting...');
  const [batteryInfo, setBatteryInfo] = useState<BatteryInfo>({
    batteryLevel: -1,
    isCharging: false,
    chargeSource: '-',
    chargingMode: 'None',
    temperature: 0,
  });
  const [networkType, setNetworkType] = useState<string>('-');
  const [fps, setFps] = useState<number>(0);
  const [packetLoss, setPacketLoss] = useState<number>(-1);

  const metricsIntervalRef = useRef<any>(null);
  const timerIntervalRef = useRef<any>(null);
  const isScanningRef = useRef<boolean>(false);

  const getDeviceModel = () => {
    const brand = Device.brand ? Device.brand.toUpperCase() : '';
    const model = Device.modelName || 'Device';
    if (brand && !model.toUpperCase().startsWith(brand)) {
      return `${brand} ${model}`;
    }
    return model;
  };

  const getSimulatedDeviceId = () => {
    const brand = (Device.brand || 'expo').toLowerCase();
    const model = (Device.modelName || 'simulator').toLowerCase().replace(/\s+/g, '_');
    return `sim_device_${brand}_${model}`;
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
    if (DeviceMonitor) {
      try {
        DeviceMonitor.stopBackgroundLoop();
      } catch (err) {
        console.error('Failed to stop native background loop:', err);
      }
    }
    isScanningRef.current = false;
    setIsScanning(false);
  };

  const updateMetrics = async (currentWanIp?: string) => {
    let currentStats: DeviceStats | null = null;
    let currentCpuLoad = 0;
    let currentPingGateway = '-';
    let currentPing8888 = '-';
    let currentServerPing = '-';
    let currentBattery: BatteryInfo = { batteryLevel: -1, isCharging: false, chargeSource: '-', chargingMode: 'None', temperature: 0 };
    let currentNetworkType = '-';
    let currentFps = 0;
    let currentPacketLoss = -1;

    if (DeviceMonitor) {
      setIsFallbackMode(false);
      try {
        const data: DeviceStats = await DeviceMonitor.getDeviceStats();
        currentStats = data;
        setStats(data);

        const cpuUsage: number = await DeviceMonitor.getCpuUsage();
        currentCpuLoad = Math.round(cpuUsage);
        setCpuLoad(currentCpuLoad);

        // Ping gateway
        if (data.gatewayIp) {
          try {
            const pingTimeStr: string = await DeviceMonitor.pingGateway(data.gatewayIp);
            currentPingGateway = pingTimeStr === 'Timeout' ? 'Timeout' : `${pingTimeStr} ms`;
          } catch {
            currentPingGateway = 'Error';
          }
          setPingGateway(currentPingGateway);
        }

        // Ping 8.8.8.8
        try {
          const ping8Result: string = await DeviceMonitor.pingGateway('8.8.8.8');
          currentPing8888 = ping8Result === 'Timeout' ? 'Timeout' : `${ping8Result} ms`;
        } catch {
          currentPing8888 = 'Error';
        }
        setPing8888(currentPing8888);

        // Ping custom server IP
        if (savedServerIpRef.current && savedServerIpRef.current.trim().length > 0) {
          try {
            const serverPingResult: string = await DeviceMonitor.pingGateway(savedServerIpRef.current.trim());
            currentServerPing = serverPingResult === 'Timeout' ? 'Timeout' : `${serverPingResult} ms`;
          } catch {
            currentServerPing = 'Error';
          }
          setServerPing(currentServerPing);
        }

        // Battery info
        try {
          const battery = await DeviceMonitor.getBatteryInfo();
          currentBattery = {
            batteryLevel: battery.batteryLevel,
            isCharging: battery.isCharging,
            chargeSource: battery.chargeSource,
            chargingMode: battery.chargingMode,
            temperature: battery.temperature,
          };
        } catch {
          // keep defaults
        }
        setBatteryInfo(currentBattery);

        // Network type
        try {
          const netType: string = await DeviceMonitor.getNetworkType();
          currentNetworkType = netType;
        } catch {
          currentNetworkType = 'Unknown';
        }
        setNetworkType(currentNetworkType);

        // FPS
        try {
          const fpsVal: number = await DeviceMonitor.getFps();
          currentFps = fpsVal;
        } catch {
          currentFps = 0;
        }
        setFps(currentFps);

        // Packet loss (runs in background, non-blocking via native thread)
        try {
          const loss: number = await DeviceMonitor.getPacketLoss('8.8.8.8');
          currentPacketLoss = loss;
        } catch {
          currentPacketLoss = -1;
        }
        setPacketLoss(currentPacketLoss);

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
        deviceId: getSimulatedDeviceId(),
        localIp: '192.168.1.15',
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
      currentStats = mockStats;
      setStats(mockStats);

      currentCpuLoad = 12 + Math.floor(Math.random() * 25);
      setCpuLoad(currentCpuLoad);

      const simulatedPingGw = 1 + Math.floor(Math.random() * 6);
      currentPingGateway = `${simulatedPingGw} ms`;
      setPingGateway(currentPingGateway);

      const simulatedPing8 = 10 + Math.floor(Math.random() * 30);
      currentPing8888 = `${simulatedPing8} ms`;
      setPing8888(currentPing8888);

      if (savedServerIpRef.current && savedServerIpRef.current.trim().length > 0) {
        const simulatedServerPing = 15 + Math.floor(Math.random() * 50);
        currentServerPing = `${simulatedServerPing} ms`;
        setServerPing(currentServerPing);
      }

      const isSimCharging = Math.random() > 0.5;
      currentBattery = {
        batteryLevel: 60 + Math.floor(Math.random() * 30),
        isCharging: isSimCharging,
        chargeSource: isSimCharging ? (Math.random() > 0.5 ? 'USB' : 'AC') : '-',
        chargingMode: isSimCharging ? (Math.random() > 0.8 ? 'Bypass' : 'Normal') : 'None',
        temperature: 28 + Math.random() * 10,
      };
      setBatteryInfo(currentBattery);

      currentNetworkType = 'WiFi';
      setNetworkType(currentNetworkType);

      currentFps = 55 + Math.floor(Math.random() * 6);
      setFps(currentFps);

      currentPacketLoss = Math.random() > 0.8 ? Math.floor(Math.random() * 5) : 0;
      setPacketLoss(currentPacketLoss);
    }

    // Post metrics to backend (only via JS fetch if DeviceMonitor is not present, i.e., fallback/Expo Go mode)
    if (currentStats && !DeviceMonitor) {
      try {
        const payload = {
          deviceId: currentStats.deviceId || getSimulatedDeviceId(),
          deviceName: getDeviceModel(),
          name_device: nameDeviceRef.current || '',
          wanIp: currentWanIp || wanIp,
          pingGateway: currentPingGateway,
          ping8888: currentPing8888,
          serverIp: savedServerIpRef.current || '',
          serverPing: currentServerPing,
          cpuLoad: currentCpuLoad,
          localIp: currentStats.localIp || '-',
          gatewayIp: currentStats.gatewayIp || '-',
          cpuModel: currentStats.cpuModel || '-',
          cpuCores: currentStats.cpuCores || 0,
          ramTotal: currentStats.ramTotal || 0,
          ramFree: currentStats.ramFree || 0,
          ramUsed: currentStats.ramUsed || 0,
          ramUsagePercent: currentStats.ramUsagePercent || 0,
          txSpeedMbps: currentStats.txSpeedMbps || 0,
          rxSpeedMbps: currentStats.rxSpeedMbps || 0,
          batteryLevel: currentBattery.batteryLevel,
          isCharging: currentBattery.isCharging,
          chargeSource: currentBattery.chargeSource,
          chargingMode: currentBattery.chargingMode,
          temperature: currentBattery.temperature,
          networkType: currentNetworkType,
          fps: currentFps,
          packetLoss: currentPacketLoss,
          timestamp: new Date().toISOString(),
        };

        // API URL for Mobile Logs (using Render production server)
        const apiUrl = 'https://mobile-monitor.onrender.com/api/mobile-logs';

        fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }).catch(err => {
          console.log(`Error posting mobile stats (silent) to ${apiUrl}:`, err.message);
        });
      } catch (postErr) {
        console.error('Failed to construct or send mobile log post:', postErr);
      }
    }
  };

  const startScanning = async () => {
    setLoading(true);
    stopScanning();
    setScanTime(0);

    try {
      let activeWanIp = '-';
      try {
        const res = await fetch('https://api.ipify.org?format=json');
        const data = await res.json();
        activeWanIp = data.ip || '-';
        setWanIp(activeWanIp);
      } catch (err) {
        setWanIp('-');
      }

      await updateMetrics(activeWanIp);
      isScanningRef.current = true;
      setIsScanning(true);

      // Start native background loop if running as built APK (DeviceMonitor available)
      if (DeviceMonitor) {
        try {
          // API URL for Mobile Logs (using Render production server)
          const apiUrl = 'https://mobile-monitor.onrender.com/api/mobile-logs';
          DeviceMonitor.startBackgroundLoop(apiUrl, savedServerIpRef.current || '', activeWanIp, nameDeviceRef.current || '');
        } catch (err) {
          console.error('Failed to start native background loop:', err);
        }
      }

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

  // Detect device model name on mount & load cached data
  useEffect(() => {
    setDeviceName(getDeviceModel());
    const loadCachedData = async () => {
      try {
        const cachedName = await AsyncStorage.getItem('saved_name_device');
        if (cachedName) {
          nameDeviceRef.current = cachedName;
          setNameDevice(cachedName);
        }
      } catch (err) {
        console.log('Failed to load cached name_device:', err);
      }
    };
    loadCachedData();
  }, []);

  // Listen for app state changes - keep scanning in background
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextAppState) => {
      // Scanning continues regardless of app state (foreground/background)
      // The intervals remain active on Android
    });
    return () => {
      subscription.remove();
    };
  }, []);

  const saveServerIp = (ip: string) => {
    savedServerIpRef.current = ip;
    setSavedServerIp(ip);
    setServerPing('-');
    if (isScanning && DeviceMonitor) {
      try {
        const apiUrl = 'https://mobile-monitor.onrender.com/api/mobile-logs';
        DeviceMonitor.startBackgroundLoop(apiUrl, ip, wanIp, nameDeviceRef.current || '');
      } catch (err) {
        console.error('Failed to update native background loop Server IP:', err);
      }
    }
  };

  const saveNameDevice = async (name: string) => {
    nameDeviceRef.current = name;
    setNameDevice(name);
    try {
      await AsyncStorage.setItem('saved_name_device', name);
      if (isScanning && DeviceMonitor) {
        try {
          const apiUrl = 'https://mobile-monitor.onrender.com/api/mobile-logs';
          DeviceMonitor.startBackgroundLoop(apiUrl, savedServerIpRef.current || '', wanIp, name);
        } catch (err) {
          console.error('Failed to update native background loop device name:', err);
        }
      }
    } catch (err) {
      console.log('Failed to cache device name:', err);
    }
  };

  return (
    <DeviceStatsContext.Provider value={{
      isScanning,
      stats,
      wanIp,
      pingGateway,
      ping8888,
      savedServerIp,
      saveServerIp,
      serverPing,
      cpuLoad,
      loading,
      isFallbackMode,
      scanTime,
      deviceName,
      batteryInfo,
      networkType,
      fps,
      packetLoss,
      startScanning,
      stopScanning,
      nameDevice,
      saveNameDevice,
    }}>
      {children}
    </DeviceStatsContext.Provider>
  );
}

export function useDeviceStats() {
  const context = useContext(DeviceStatsContext);
  if (context === undefined) {
    throw new Error('useDeviceStats must be used within a DeviceStatsProvider');
  }
  return context;
}
