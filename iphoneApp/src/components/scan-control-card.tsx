import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity, ActivityIndicator, Platform } from 'react-native';

interface ScanControlCardProps {
  isScanning: boolean;
  loading: boolean;
  scanTime: number;
  deviceName: string;
  onStart: () => void;
  onStop: () => void;
}

export function ScanControlCard({
  isScanning,
  loading,
  scanTime,
  deviceName,
  onStart,
  onStop,
}: ScanControlCardProps) {
  
  // Format stopwatch seconds to MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View style={styles.controlCard}>
      {/* Device Info Header */}
      <View style={styles.deviceHeader}>
        <Text style={styles.deviceLabel}>Target Device</Text>
        <Text style={styles.deviceName}>{deviceName}</Text>
      </View>

      {/* Ticking Status Badge */}
      <View style={styles.badgeRow}>
        <View style={[styles.statusBadge, { borderColor: isScanning ? '#10b981' : '#64748b' }]}>
          <View style={[styles.statusDot, { backgroundColor: isScanning ? '#10b981' : '#64748b' }]} />
          <Text style={[styles.statusText, { color: isScanning ? '#10b981' : '#64748b' }]}>
            {isScanning ? 'LIVE TELEMETRY' : 'READY TO SCAN'}
          </Text>
        </View>
      </View>

      {/* Circular Start/Stop Button */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity
          activeOpacity={0.8}
          style={[
            styles.circleButton,
            isScanning ? styles.buttonActive : styles.buttonIdle,
          ]}
          onPress={isScanning ? onStop : onStart}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#0ea5e9" size="large" />
          ) : (
            <View style={styles.innerCircleContent}>
              <Text style={[styles.buttonActionText, { color: isScanning ? '#ef4444' : '#0ea5e9' }]}>
                {isScanning ? 'STOP' : 'START'}
              </Text>
              
              {isScanning ? (
                <Text style={styles.stopwatchText}>{formatTime(scanTime)}</Text>
              ) : (
                <Text style={styles.tapToScanText}>TAP TO DIAGNOSE</Text>
              )}
            </View>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  controlCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  deviceHeader: {
    alignItems: 'center',
    marginBottom: 8,
  },
  deviceLabel: {
    fontSize: 11,
    color: '#64748b',
    fontWeight: 'bold',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 2,
  },
  deviceName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0f172a',
  },
  badgeRow: {
    marginBottom: 20,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 20,
    paddingVertical: 3,
    paddingHorizontal: 10,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 6,
  },
  statusText: {
    fontSize: 9,
    fontWeight: 'bold',
    letterSpacing: 0.8,
  },
  buttonContainer: {
    marginVertical: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  circleButton: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 5,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ffffff',
    shadowColor: '#0ea5e9',
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 12,
    elevation: 6,
  },
  buttonIdle: {
    borderColor: '#e2e8f0',
    shadowOpacity: 0.05,
  },
  buttonActive: {
    borderColor: '#10b981',
    shadowColor: '#10b981',
    shadowOpacity: 0.15,
  },
  innerCircleContent: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonActionText: {
    fontSize: 24,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
  tapToScanText: {
    fontSize: 9,
    color: '#94a3b8',
    fontWeight: 'bold',
    marginTop: 4,
    letterSpacing: 0.5,
  },
  stopwatchText: {
    fontSize: 16,
    color: '#475569',
    fontWeight: 'bold',
    marginTop: 4,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
});
