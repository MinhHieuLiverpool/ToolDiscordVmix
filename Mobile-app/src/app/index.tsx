import React from 'react';
import { StyleSheet, ScrollView, SafeAreaView, View, Text } from 'react-native';
import { useDeviceStats } from '../hooks/useDeviceStats';
import { ScanControlCard } from '../components/scan-control-card';
import { NetworkStatsCard } from '../components/network-stats-card';
import { BandwidthStatsCard } from '../components/bandwidth-stats-card';
import { GatewayPingCard } from '../components/gateway-ping-card';
import { HardwareStatsCard } from '../components/hardware-stats-card';

export default function HomeScreen() {
  const {
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
  } = useDeviceStats();

  return (
    <SafeAreaView style={styles.container}>
      {/* Light Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>MobileMonitor</Text>
        <View style={styles.brandingRow}>
          <Text style={styles.brandingSub}>Diagnostics Terminal</Text>
        </View>
      </View>

      {/* Warning Banner for Simulator Fallback */}
      {isFallbackMode && isScanning && (
        <View style={styles.fallbackBanner}>
          <Text style={styles.fallbackBannerText}>
            ⚠️ Running in Expo Go (Simulated Mode). Build native app to see real hardware stats.
          </Text>
        </View>
      )}

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Modular Circular Scan Controls */}
        <ScanControlCard
          isScanning={isScanning}
          loading={loading}
          scanTime={scanTime}
          deviceName={deviceName}
          onStart={startScanning}
          onStop={stopScanning}
        />

        {/* Modular Network Metrics */}
        <NetworkStatsCard
          stats={isScanning ? stats : null}
          wanIp={isScanning ? wanIp : '-'}
        />

        {/* Modular Bandwidth Telemetry */}
        <BandwidthStatsCard
          stats={isScanning ? stats : null}
        />

        {/* Modular Diagnostics Ping */}
        <GatewayPingCard
          pingStatus={isScanning ? pingStatus : '-'}
        />

        {/* Modular Hardware Specifications */}
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
});
