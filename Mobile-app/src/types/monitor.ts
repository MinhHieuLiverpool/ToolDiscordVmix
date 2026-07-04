export interface DeviceStats {
  deviceId?: string;
  localIp: string;
  gatewayIp: string;
  cpuModel: string;
  cpuCores: number;
  ramTotal: number;
  ramFree: number;
  ramUsed: number;
  ramUsagePercent: number;
  txSpeedMbps: number;
  rxSpeedMbps: number;
}

export interface BatteryInfo {
  batteryLevel: number;
  isCharging: boolean;
  chargeSource: string;
  chargingMode: string;
  temperature: number;
}

export interface PingDetails {
  label: string;
  color: string;
}
