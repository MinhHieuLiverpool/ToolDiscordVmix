import React from 'react';
import { StyleSheet, View, Text, Dimensions } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { DeviceStats } from '../types/monitor';

const { width } = Dimensions.get('window');

interface HardwareStatsCardProps {
  stats: DeviceStats | null;
  cpuLoad: number;
}

export function HardwareStatsCard({ stats, cpuLoad }: HardwareStatsCardProps) {
  
  // Format bytes to GB
  const formatGB = (bytes: number) => {
    if (!bytes) return '-';
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <MaterialCommunityIcons name="chip" size={20} color="#0ea5e9" />
        <Text style={styles.cardTitle}>Hardware Specifications</Text>
      </View>

      {/* CPU Section */}
      <Text style={styles.sectionHeader}>CPU Info</Text>
      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Processor</Text>
        <Text style={styles.metricValue} numberOfLines={1}>{stats?.cpuModel || '-'}</Text>
      </View>
      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Cores</Text>
        <Text style={styles.metricValue}>{stats?.cpuCores ? `${stats.cpuCores} Cores` : '-'}</Text>
      </View>

      <View style={styles.progressContainer}>
        <View style={styles.progressLabels}>
          <Text style={styles.progressTitle}>Active CPU Load</Text>
          <Text style={styles.progressVal}>{stats ? `${cpuLoad}%` : '-'}</Text>
        </View>
        <View style={styles.progressBarBg}>
          <View 
            style={[
              styles.progressBarFill, 
              { 
                width: `${stats ? cpuLoad : 0}%`,
                backgroundColor: cpuLoad > 75 ? '#ef4444' : cpuLoad > 40 ? '#f97316' : '#0ea5e9' 
              }
            ]} 
          />
        </View>
      </View>

      <View style={styles.divider} />

      {/* RAM Section */}
      <Text style={styles.sectionHeader}>RAM Info</Text>
      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Total Capacity</Text>
        <Text style={styles.metricValue}>{stats?.ramTotal ? formatGB(stats.ramTotal) : '-'}</Text>
      </View>
      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Used RAM</Text>
        <Text style={styles.metricValue}>{stats?.ramUsed ? formatGB(stats.ramUsed) : '-'}</Text>
      </View>
      <View style={styles.metricRow}>
        <Text style={styles.metricLabel}>Free RAM</Text>
        <Text style={styles.metricValue}>{stats?.ramFree ? formatGB(stats.ramFree) : '-'}</Text>
      </View>

      <View style={styles.progressContainer}>
        <View style={styles.progressLabels}>
          <Text style={styles.progressTitle}>Memory Usage</Text>
          <Text style={styles.progressVal}>{stats?.ramUsagePercent ? `${stats.ramUsagePercent}%` : '-'}</Text>
        </View>
        <View style={styles.progressBarBg}>
          <View 
            style={[
              styles.progressBarFill, 
              { 
                width: `${stats?.ramUsagePercent || 0}%`,
                backgroundColor: (stats?.ramUsagePercent || 0) > 85 ? '#ef4444' : (stats?.ramUsagePercent || 0) > 60 ? '#f97316' : '#10b981'
              }
            ]} 
          />
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
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0ea5e9',
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
  sectionHeader: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#0f172a',
    marginTop: 12,
    marginBottom: 6,
    borderLeftWidth: 3,
    borderLeftColor: '#0ea5e9',
    paddingLeft: 8,
  },
  progressContainer: {
    marginVertical: 12,
  },
  progressLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  progressTitle: {
    color: '#64748b',
    fontSize: 13,
    fontWeight: '500',
  },
  progressVal: {
    color: '#0f172a',
    fontSize: 13,
    fontWeight: 'bold',
  },
  progressBarBg: {
    height: 8,
    backgroundColor: '#f1f5f9',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  divider: {
    height: 1,
    backgroundColor: '#f1f5f9',
    marginVertical: 16,
  },
});
