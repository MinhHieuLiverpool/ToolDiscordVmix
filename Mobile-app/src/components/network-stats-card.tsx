import React from 'react';
import { StyleSheet, View, Text, Dimensions } from 'react-native';
import { DeviceStats } from '../types/monitor';

const { width } = Dimensions.get('window');

interface NetworkStatsCardProps {
  stats: DeviceStats | null;
  wanIp: string;
}

export function NetworkStatsCard({ stats, wanIp }: NetworkStatsCardProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Network Specifications</Text>
      
      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Local IP Address</Text>
        <Text style={styles.metricValue}>{stats?.localIp || '-'}</Text>
      </View>

      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Public WAN IP</Text>
        <Text style={styles.metricValue}>{wanIp || '-'}</Text>
      </View>

      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>MAC Address</Text>
        <Text style={styles.metricValue}>{stats?.macAddress || '-'}</Text>
      </View>

      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Default Gateway</Text>
        <Text style={styles.metricValue}>{stats?.gatewayIp || '-'}</Text>
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
    marginBottom: 12,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  metricLabel: {
    color: '#64748b',
    fontSize: 14,
    fontWeight: '500',
  },
  metricValue: {
    color: '#0f172a',
    fontSize: 14,
    fontWeight: 'bold',
    maxWidth: width * 0.5,
  },
});
