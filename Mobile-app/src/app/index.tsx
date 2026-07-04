import React, { useState, useEffect } from 'react';
import { StyleSheet, ScrollView, View, Text, TextInput, TouchableOpacity, StatusBar, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useDeviceStats } from '../hooks/useDeviceStats';
import { ScanControlCard } from '../components/scan-control-card';
import { NetworkStatsCard } from '../components/network-stats-card';
import { BandwidthStatsCard } from '../components/bandwidth-stats-card';
import { GatewayPingCard } from '../components/gateway-ping-card';
import { HardwareStatsCard } from '../components/hardware-stats-card';
import { BatteryStatsCard } from '../components/battery-stats-card';
import { PerformanceStatsCard } from '../components/performance-stats-card';

export default function HomeScreen() {
  const {
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
  } = useDeviceStats();

  const [inputNameDevice, setInputNameDevice] = useState(nameDevice);

  // Sync input when cached nameDevice loads asynchronously
  useEffect(() => {
    if (nameDevice && !inputNameDevice) {
      setInputNameDevice(nameDevice);
    }
  }, [nameDevice]);
  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
      
      {/* Light Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>MobileMonitor</Text>
        <View style={styles.brandingRow}>
          <Text style={styles.brandingSub}>Diagnostics Terminal</Text>
        </View>
      </View>

      {/* Name Device Input Bar - Sticky at Top */}
      <View style={styles.nameDeviceBar}>
        <Text style={styles.nameDeviceLabel}>📱 Thiết bị:</Text>
        <TextInput
          style={styles.nameDeviceInput}
          placeholder="Nhập tên thiết bị (name_device)..."
          placeholderTextColor="#fca5a5"
          value={inputNameDevice}
          onChangeText={setInputNameDevice}
          autoCapitalize="words"
          autoCorrect={false}
        />
        <TouchableOpacity
          style={styles.nameDeviceSaveBtn}
          onPress={() => {
            const trimmed = inputNameDevice.trim();
            saveNameDevice(trimmed);
            Alert.alert(
              '✅ Đã lưu',
              `Tên thiết bị đã được lưu: "${trimmed || '(trống)'}"`,
              [{ text: 'OK' }]
            );
          }}
          activeOpacity={0.7}
        >
          <Text style={styles.nameDeviceSaveBtnText}>💾 Save</Text>
        </TouchableOpacity>
      </View>

      {/* Warning Banner for Simulator Fallback */}
      {isFallbackMode && isScanning && (
        <View style={styles.fallbackBanner}>
          <Text style={styles.fallbackBannerText}>
            ⚠️ Running in Expo Go (Simulated Mode). Build native app to see real hardware stats.
          </Text>
        </View>
      )}

      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        {/* Scan Controls */}
        <ScanControlCard
          isScanning={isScanning}
          loading={loading}
          scanTime={scanTime}
          deviceName={deviceName}
          onStart={startScanning}
          onStop={stopScanning}
        />

        {/* Network Specs */}
        <NetworkStatsCard
          stats={isScanning ? stats : null}
          wanIp={isScanning ? wanIp : '-'}
          networkType={isScanning ? networkType : '-'}
        />

        {/* Bandwidth Telemetry */}
        <BandwidthStatsCard
          stats={isScanning ? stats : null}
        />

        {/* Ping Diagnostics */}
        <GatewayPingCard
          pingGateway={isScanning ? pingGateway : '-'}
          ping8888={isScanning ? ping8888 : '-'}
          savedServerIp={savedServerIp}
          serverPing={isScanning ? serverPing : '-'}
          onSaveServerIp={saveServerIp}
        />

        {/* Performance Monitor */}
        <PerformanceStatsCard
          fps={fps}
          packetLoss={packetLoss}
          isScanning={isScanning}
        />

        {/* Battery & Temperature */}
        <BatteryStatsCard
          batteryInfo={batteryInfo}
          isScanning={isScanning}
        />

        {/* Hardware Specifications */}
        <HardwareStatsCard
          stats={isScanning ? stats : null}
          cpuLoad={isScanning ? cpuLoad : 0}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  fallbackBanner: {
    backgroundColor: '#fffbeb',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#fef3c7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fallbackBannerText: {
    color: '#d97706',
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    backgroundColor: '#ffffff',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#0ea5e9',
    letterSpacing: 0.5,
  },
  brandingRow: {
    justifyContent: 'center',
  },
  brandingSub: {
    fontSize: 11,
    color: '#64748b',
    fontStyle: 'italic',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  nameDeviceBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fef2f2',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#fee2e2',
    gap: 8,
  },
  nameDeviceLabel: {
    fontSize: 14,
    fontWeight: '900',
    color: '#dc2626',
  },
  nameDeviceInput: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#fca5a5',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 14,
    color: '#b91c1c',
    fontWeight: '900',
  },
  nameDeviceSaveBtn: {
    backgroundColor: '#dc2626',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
  },
  nameDeviceSaveBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: 'bold',
  },
});
