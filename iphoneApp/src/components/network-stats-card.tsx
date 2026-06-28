import React from 'react';
import { StyleSheet, View, Text, Dimensions } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { DeviceStats } from '../types/monitor';

const { width } = Dimensions.get('window');

interface NetworkStatsCardProps {
  stats: DeviceStats | null;
  wanIp: string;
  networkType: string;
}

export function NetworkStatsCard({ stats, wanIp, networkType }: NetworkStatsCardProps) {

  const getNetworkIcon = (): keyof typeof MaterialCommunityIcons.glyphMap => {
    switch (networkType) {
      case 'WiFi': return 'wifi';
      case 'Cellular': return 'signal-4g';
      case 'Ethernet': return 'ethernet';
      case 'VPN': return 'shield-lock';
      default: return 'web';
    }
  };

  const getNetworkColor = () => {
    switch (networkType) {
      case 'WiFi': return '#10b981';
      case 'Cellular': return '#f59e0b';
      case 'Ethernet': return '#0ea5e9';
      default: return '#64748b';
    }
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <MaterialCommunityIcons name="lan" size={20} color="#0ea5e9" />
        <Text style={styles.cardTitle}>Network Specifications</Text>
      </View>
      
      {/* Network Type Badge */}
      <View style={styles.networkTypeBadge}>
        <View style={[styles.netBadgeInner, { backgroundColor: getNetworkColor() + '15', borderColor: getNetworkColor() + '30' }]}>
          <MaterialCommunityIcons name={getNetworkIcon()} size={16} color={getNetworkColor()} />
          <Text style={[styles.netBadgeText, { color: getNetworkColor() }]}>
            {networkType !== '-' ? networkType : 'Detecting...'}
          </Text>
        </View>
      </View>

      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Local IP Address</Text>
        <Text style={styles.metricValue}>{stats?.localIp || '-'}</Text>
      </View>

      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Public WAN IP</Text>
        <Text style={styles.metricValue}>{wanIp || '-'}</Text>
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
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0ea5e9',
  },
  networkTypeBadge: {
    alignItems: 'center',
    marginBottom: 14,
  },
  netBadgeInner: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1,
    gap: 6,
  },
  netBadgeText: {
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 0.5,
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
