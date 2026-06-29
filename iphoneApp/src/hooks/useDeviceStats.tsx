import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { NativeModules, AppState } from 'react-native';
import * as Device from 'expo-device';
import * as Network from 'expo-network';
import * as Battery from 'expo-battery';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { DeviceStats, BatteryInfo } from '../types/monitor';

const { DeviceMonitor } = NativeModules;

const isValidIp = (ip: string): boolean => {
  if (!ip || ip === '-' || ip === '0.0.0.0' || ip === '127.0.0.1') return false;
  const parts = ip.split('.');
  if (parts.length !== 4) return false;
  return parts.every(p => {
    const n = parseInt(p, 10);
    return !isNaN(n) && n >= 0 && n <= 255;
  });
};

const getEstimatedGateway = (ip: string) => {
  if (!isValidIp(ip)) return '-';
  const parts = ip.split('.');
  return `${parts[0]}.${parts[1]}.${parts[2]}.1`;
};

// Check if an IP is a private/LAN address
const isPrivateIp = (ip: string): boolean => {
  if (!ip) return false;
  const parts = ip.split('.');
  if (parts.length !== 4) return false;
  const first = parseInt(parts[0], 10);
  const second = parseInt(parts[1], 10);
  if (first === 10) return true; // 10.0.0.0/8
  if (first === 192 && second === 168) return true; // 192.168.0.0/16
  if (first === 172 && second >= 16 && second <= 31) return true; // 172.16.0.0/12
  if (first === 169 && second === 254) return true; // 169.254.0.0/16 (link-local)
  return false;
};

// HTTP-based ping: measures network round-trip time
// For 8.8.8.8: uses Google's fast 204 endpoint (zero-body response, minimal overhead)
// For gateway/LAN: measures connection attempt time (even errors reveal RTT)
const httpPing = async (target: string): Promise<string> => {
  const controller = new AbortController();
  const abortTimeout = setTimeout(() => controller.abort(), 3000);
  const start = Date.now();

  try {
    let url: string;
    if (target === '8.8.8.8') {
      // Google DNS 204 endpoint — returns empty 204, fastest possible HTTPS response
      url = `https://dns.google/generate_204?_t=${Date.now()}`;
    } else if (isPrivateIp(target)) {
      // LAN gateway — try direct HTTP (iOS allows local network HTTP)
      url = `http://${target}/?_t=${Date.now()}`;
    } else {
      // Other public hosts
      url = `https://${target}/?_t=${Date.now()}`;
    }

    await fetch(url, {
      method: 'HEAD',
      signal: controller.signal,
      cache: 'no-cache',
    });
    clearTimeout(abortTimeout);
    const elapsed = Date.now() - start;
    return `${elapsed} ms`;
  } catch (err: any) {
    clearTimeout(abortTimeout);
    const elapsed = Date.now() - start;

    // AbortError = our timeout triggered (> 3s) → real timeout
    if (err?.name === 'AbortError') return 'Timeout';

    // For LAN/private IPs: connection error time approximates the RTT
    // Even if the router rejects HTTP, the TCP handshake time reveals latency
    // Quick error (< 1000ms) means we reached the device on the local network
    if (isPrivateIp(target) && elapsed < 1000) {
      return `${elapsed} ms`;
    }

    // For public IPs: if error was fast, it's still a connectivity indicator
    if (!isPrivateIp(target) && elapsed < 2000) {
      return `${elapsed} ms`;
    }

    return 'Timeout';
  }
};

// Get valid local IP, retrying once if 0.0.0.0 is returned
const getValidLocalIp = async (): Promise<string> => {
  try {
    let ip = await Network.getIpAddressAsync();
    if (isValidIp(ip)) return ip;
    // Retry after short delay (network might be transitioning)
    await new Promise(resolve => setTimeout(resolve, 500));
    ip = await Network.getIpAddressAsync();
    if (isValidIp(ip)) return ip;
    return '-';
  } catch {
    return '-';
  }
};

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
    temperature: 0,
  });
  const [networkType, setNetworkType] = useState<string>('-');
  const [fps, setFps] = useState<number>(0);
  const [packetLoss, setPacketLoss] = useState<number>(-1);

  const metricsIntervalRef = useRef<any>(null);
  const timerIntervalRef = useRef<any>(null);
  const isScanningRef = useRef<boolean>(false);
  const lastSpeedTestRef = useRef<{ time: number; rx: number; tx: number }>({ time: 0, rx: 0, tx: 0 });

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
    // Get valid local IP (filters out 0.0.0.0)
    const realLocalIp = await getValidLocalIp();

    // Refresh WAN IP periodically (not just on start)
    if (!currentWanIp) {
      try {
        const res = await fetch('https://api.ipify.org?format=json');
        const data = await res.json();
        const newWanIp = data.ip || '-';
        setWanIp(newWanIp);
        currentWanIp = newWanIp;
      } catch {
        // keep existing wanIp
      }
    }

    let currentStats: DeviceStats | null = null;
    let currentCpuLoad = 0;
    let currentPingGateway = '-';
    let currentPing8888 = '-';
    let currentServerPing = '-';
    let currentBattery: BatteryInfo = { batteryLevel: -1, isCharging: false, chargeSource: '-', temperature: 0 };
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

      // Get real network state from expo-network
      let detectedNetworkType = '-';
      try {
        const networkState = await Network.getNetworkStateAsync();
        if (networkState.isConnected) {
          switch (networkState.type) {
            case Network.NetworkStateType.WIFI:
              detectedNetworkType = 'WiFi';
              break;
            case Network.NetworkStateType.CELLULAR:
              detectedNetworkType = 'Cellular';
              break;
            case Network.NetworkStateType.ETHERNET:
              detectedNetworkType = 'Ethernet';
              break;
            case Network.NetworkStateType.BLUETOOTH:
              detectedNetworkType = 'Bluetooth';
              break;
            case Network.NetworkStateType.VPN:
              detectedNetworkType = 'VPN';
              break;
            default:
              detectedNetworkType = 'Other';
              break;
          }
        } else {
          detectedNetworkType = 'Disconnected';
        }
      } catch {
        detectedNetworkType = 'Unknown';
      }

      // Calculate gateway from valid local IP
      const gatewayIp = isValidIp(realLocalIp) ? getEstimatedGateway(realLocalIp) : '-';

      // Download speed estimation (run every ~10s, not every 2s cycle)
      const now = Date.now();
      let measuredRx = lastSpeedTestRef.current.rx;
      let measuredTx = lastSpeedTestRef.current.tx;
      if (now - lastSpeedTestRef.current.time > 10000) {
        try {
          const testUrl = `https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.core.min.js?_t=${now}`;
          const startDl = Date.now();
          const dlRes = await fetch(testUrl, { cache: 'no-cache' });
          const dlBlob = await dlRes.blob();
          const dlElapsed = (Date.now() - startDl) / 1000;
          if (dlElapsed > 0 && dlBlob.size > 0) {
            measuredRx = parseFloat(((dlBlob.size * 8) / (dlElapsed * 1_000_000)).toFixed(2));
          }
          // Estimate TX from the POST we send to the backend (rough)
          measuredTx = parseFloat((measuredRx * 0.1).toFixed(2)); // rough upload estimate
        } catch {
          measuredRx = 0;
          measuredTx = 0;
        }
        lastSpeedTestRef.current = { time: now, rx: measuredRx, tx: measuredTx };
      }

      const mockStats: DeviceStats = {
        deviceId: getSimulatedDeviceId(),
        localIp: isValidIp(realLocalIp) ? realLocalIp : '-',
        gatewayIp: gatewayIp,
        cpuModel: Device.modelName || 'Simulated Processor',
        cpuCores: Device.supportedCpuArchitectures?.length || 8,
        ramTotal: totalRam,
        ramFree: freeRam,
        ramUsed: usedRam,
        ramUsagePercent: randomUsagePercent,
        txSpeedMbps: measuredTx,
        rxSpeedMbps: measuredRx,
      };
      currentStats = mockStats;
      setStats(mockStats);

      currentCpuLoad = 12 + Math.floor(Math.random() * 25);
      setCpuLoad(currentCpuLoad);

      // HTTP-based ping for gateway
      if (isValidIp(gatewayIp)) {
        try {
          currentPingGateway = await httpPing(gatewayIp);
        } catch {
          currentPingGateway = 'Timeout';
        }
      } else {
        currentPingGateway = '-';
      }
      setPingGateway(currentPingGateway);

      // HTTP-based ping for 8.8.8.8
      try {
        currentPing8888 = await httpPing('8.8.8.8');
      } catch {
        currentPing8888 = 'Timeout';
      }
      setPing8888(currentPing8888);

      // HTTP-based ping for custom server
      if (savedServerIpRef.current && savedServerIpRef.current.trim().length > 0) {
        try {
          currentServerPing = await httpPing(savedServerIpRef.current.trim());
        } catch {
          currentServerPing = 'Timeout';
        }
        setServerPing(currentServerPing);
      }

      // Get REAL battery info from expo-battery
      try {
        const batteryLevel = await Battery.getBatteryLevelAsync();
        const batteryState = await Battery.getBatteryStateAsync();
        const isChargingState = batteryState === Battery.BatteryState.CHARGING;
        const isFullState = batteryState === Battery.BatteryState.FULL;
        
        let chargeSource = '-';
        if (isChargingState) {
          chargeSource = 'Charging';
        } else if (isFullState) {
          chargeSource = 'Full';
        } else {
          chargeSource = 'Not Charging';
        }

        currentBattery = {
          batteryLevel: batteryLevel >= 0 ? Math.round(batteryLevel * 100) : -1,
          isCharging: isChargingState || isFullState,
          chargeSource: chargeSource,
          temperature: 0, // Not available via expo-battery
        };
      } catch {
        currentBattery = {
          batteryLevel: -1,
          isCharging: false,
          chargeSource: '-',
          temperature: 0,
        };
      }
      setBatteryInfo(currentBattery);

      currentNetworkType = detectedNetworkType;
      setNetworkType(currentNetworkType);

      currentFps = 55 + Math.floor(Math.random() * 6);
      setFps(currentFps);

      // Derive packet loss from existing ping results (avoid extra HTTP requests)
      if (currentPing8888 !== 'Timeout' && currentPing8888 !== '-') {
        currentPacketLoss = 0; // Ping succeeded = no loss detected
      } else if (currentPing8888 === 'Timeout') {
        currentPacketLoss = 100; // Ping failed = total loss
      } else {
        currentPacketLoss = -1; // Unknown
      }
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

  // Detect device model name on mount
  useEffect(() => {
    setDeviceName(getDeviceModel());
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

  // Load cached values on mount
  useEffect(() => {
    const loadCachedData = async () => {
      try {
        const cachedIp = await AsyncStorage.getItem('saved_server_ip');
        if (cachedIp) {
          savedServerIpRef.current = cachedIp;
          setSavedServerIp(cachedIp);
        }
        const cachedName = await AsyncStorage.getItem('saved_name_device');
        if (cachedName) {
          nameDeviceRef.current = cachedName;
          setNameDevice(cachedName);
        }
      } catch (err) {
        console.log('Failed to load cached config:', err);
      }
    };
    loadCachedData();
  }, []);

  const saveServerIp = async (ip: string) => {
    savedServerIpRef.current = ip;
    setSavedServerIp(ip);
    setServerPing('-');
    try {
      await AsyncStorage.setItem('saved_server_ip', ip);
    } catch (err) {
      console.log('Failed to cache server IP:', err);
    }
  };

  const saveNameDevice = async (name: string) => {
    nameDeviceRef.current = name;
    setNameDevice(name);
    try {
      await AsyncStorage.setItem('saved_name_device', name);
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
