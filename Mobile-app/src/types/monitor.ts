export interface DeviceStats {
  localIp: string;
  macAddress: string;
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

export interface PingDetails {
  label: string;
  color: string;
}
