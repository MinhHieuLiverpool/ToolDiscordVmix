import React from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { DeviceStats } from '../types/monitor';

interface BandwidthStatsCardProps {
  stats: DeviceStats | null;
}

export function BandwidthStatsCard({ stats }: BandwidthStatsCardProps) {
  const formatSpeed = (speedMbps: number | undefined) => {
    if (speedMbps === undefined || stats === null) return '- Mbps';
    return `${speedMbps.toFixed(2)} Mbps`;
  };

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Bandwidth Telemetry</Text>
      
      <View style={styles.gridContainer}>
        {/* Sender / Upload Box */}
        <View style={styles.speedBox}>
          <Text style={styles.speedLabel}>▲ SENDER (UPLOAD)</Text>
          <Text style={[styles.speedValue, { color: '#0ea5e9' }]}>
            {formatSpeed(stats?.txSpeedMbps)}
          </Text>
        </View>

        {/* Receiver / Download Box */}
        <View style={styles.speedBox}>
          <Text style={styles.speedLabel}>▼ RECEIVER (DOWNLOAD)</Text>
          <Text style={[styles.speedValue, { color: '#10b981' }]}>
            {formatSpeed(stats?.rxSpeedMbps)}
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.03,
    shadowRadius: 6,
    elevation: 1,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0ea5e9',
    marginBottom: 16,
  },
  gridContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  speedBox: {
    flex: 1,
    backgroundColor: '#f8fafc',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    alignItems: 'center',
  },
  speedLabel: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#64748b',
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  speedValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
});
