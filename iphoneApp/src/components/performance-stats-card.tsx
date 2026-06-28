import React from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface PerformanceStatsCardProps {
  fps: number;
  packetLoss: number;
  isScanning: boolean;
}

export function PerformanceStatsCard({ fps, packetLoss, isScanning }: PerformanceStatsCardProps) {

  const getFpsColor = () => {
    if (!isScanning || fps <= 0) return '#64748b';
    if (fps >= 55) return '#10b981';
    if (fps >= 30) return '#f59e0b';
    return '#ef4444';
  };

  const getFpsLabel = () => {
    if (!isScanning || fps <= 0) return 'Idle';
    if (fps >= 55) return 'Smooth';
    if (fps >= 30) return 'OK';
    return 'Laggy';
  };

  const getPacketLossColor = () => {
    if (!isScanning || packetLoss < 0) return '#64748b';
    if (packetLoss === 0) return '#10b981';
    if (packetLoss <= 2) return '#f59e0b';
    return '#ef4444';
  };

  const getPacketLossLabel = () => {
    if (!isScanning || packetLoss < 0) return 'Idle';
    if (packetLoss === 0) return 'Perfect';
    if (packetLoss <= 2) return 'Minor';
    return 'Critical';
  };

  const fpsColor = getFpsColor();
  const plColor = getPacketLossColor();

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <MaterialCommunityIcons name="speedometer" size={20} color="#0ea5e9" />
        <Text style={styles.cardTitle}>Performance Monitor</Text>
      </View>

      <View style={styles.gridContainer}>
        {/* FPS Box */}
        <View style={styles.statBox}>
          <MaterialCommunityIcons name="monitor-eye" size={28} color={fpsColor} />
          <Text style={[styles.statValue, { color: fpsColor }]}>
            {isScanning && fps > 0 ? `${fps}` : '-'}
          </Text>
          <Text style={styles.statUnit}>FPS</Text>
          <View style={[styles.statusPill, { backgroundColor: fpsColor + '15' }]}>
            <Text style={[styles.statusPillText, { color: fpsColor }]}>{getFpsLabel()}</Text>
          </View>
        </View>

        {/* Packet Loss Box */}
        <View style={styles.statBox}>
          <MaterialCommunityIcons name="package-variant-closed-remove" size={28} color={plColor} />
          <Text style={[styles.statValue, { color: plColor }]}>
            {isScanning && packetLoss >= 0 ? `${packetLoss}%` : '-'}
          </Text>
          <Text style={styles.statUnit}>Packet Loss</Text>
          <View style={[styles.statusPill, { backgroundColor: plColor + '15' }]}>
            <Text style={[styles.statusPillText, { color: plColor }]}>{getPacketLossLabel()}</Text>
          </View>
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
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0ea5e9',
  },
  gridContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  statBox: {
    flex: 1,
    backgroundColor: '#f8fafc',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    marginTop: 6,
  },
  statUnit: {
    fontSize: 11,
    color: '#64748b',
    fontWeight: '600',
    marginTop: 2,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  statusPill: {
    marginTop: 8,
    paddingVertical: 3,
    paddingHorizontal: 10,
    borderRadius: 10,
  },
  statusPillText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
});
