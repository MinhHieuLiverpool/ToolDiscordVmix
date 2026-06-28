import React from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BatteryInfo } from '../types/monitor';

interface BatteryStatsCardProps {
  batteryInfo: BatteryInfo;
  isScanning: boolean;
}

export function BatteryStatsCard({ batteryInfo, isScanning }: BatteryStatsCardProps) {

  const getBatteryColor = () => {
    if (!isScanning || batteryInfo.batteryLevel < 0) return '#64748b';
    if (batteryInfo.batteryLevel > 60) return '#10b981';
    if (batteryInfo.batteryLevel > 20) return '#f59e0b';
    return '#ef4444';
  };

  const getBatteryIcon = (): keyof typeof MaterialCommunityIcons.glyphMap => {
    if (!isScanning || batteryInfo.batteryLevel < 0) return 'battery-unknown';
    if (batteryInfo.isCharging) return 'battery-charging';
    if (batteryInfo.batteryLevel > 80) return 'battery-high';
    if (batteryInfo.batteryLevel > 40) return 'battery-medium';
    if (batteryInfo.batteryLevel > 10) return 'battery-low';
    return 'battery-alert';
  };

  const getTempColor = () => {
    if (!isScanning || batteryInfo.temperature <= 0) return '#64748b';
    if (batteryInfo.temperature < 35) return '#10b981';
    if (batteryInfo.temperature < 42) return '#f59e0b';
    return '#ef4444';
  };

  const batteryColor = getBatteryColor();
  const tempColor = getTempColor();

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <MaterialCommunityIcons name="battery-heart-variant" size={20} color="#0ea5e9" />
        <Text style={styles.cardTitle}>Battery & Temperature</Text>
      </View>

      <View style={styles.gridContainer}>
        {/* Battery Level */}
        <View style={styles.statBox}>
          <MaterialCommunityIcons name={getBatteryIcon()} size={28} color={batteryColor} />
          <Text style={[styles.statValue, { color: batteryColor }]}>
            {isScanning && batteryInfo.batteryLevel >= 0 ? `${batteryInfo.batteryLevel}%` : '-'}
          </Text>
          <Text style={styles.statLabel}>Battery</Text>
        </View>

        {/* Temperature */}
        <View style={styles.statBox}>
          <MaterialCommunityIcons name="thermometer" size={28} color={tempColor} />
          <Text style={[styles.statValue, { color: tempColor }]}>
            {isScanning && batteryInfo.temperature > 0 ? `${batteryInfo.temperature.toFixed(1)}°` : '-'}
          </Text>
          <Text style={styles.statLabel}>Temperature</Text>
        </View>
      </View>

      {/* Charging Status Row */}
      <View style={styles.chargingRow}>
        <View style={styles.chargingInfo}>
          <MaterialCommunityIcons
            name={isScanning && batteryInfo.isCharging ? 'lightning-bolt' : 'power-plug-off'}
            size={18}
            color={isScanning && batteryInfo.isCharging ? '#10b981' : '#64748b'}
          />
          <Text style={styles.chargingLabel}>Charging Status</Text>
        </View>
        <View style={[
          styles.chargingBadge,
          { backgroundColor: isScanning && batteryInfo.isCharging ? '#10b98115' : '#64748b15' }
        ]}>
          <Text style={[
            styles.chargingBadgeText,
            { color: isScanning && batteryInfo.isCharging ? '#10b981' : '#64748b' }
          ]}>
            {!isScanning ? '-' : batteryInfo.isCharging
              ? `Charging (${batteryInfo.chargeSource})`
              : 'Not Charging'
            }
          </Text>
        </View>
      </View>

      {/* Battery Progress Bar */}
      {isScanning && batteryInfo.batteryLevel >= 0 && (
        <View style={styles.progressContainer}>
          <View style={styles.progressBarBg}>
            <View
              style={[
                styles.progressBarFill,
                {
                  width: `${batteryInfo.batteryLevel}%`,
                  backgroundColor: batteryColor,
                },
              ]}
            />
          </View>
        </View>
      )}
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
    marginBottom: 14,
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
    fontSize: 22,
    fontWeight: 'bold',
    marginTop: 6,
  },
  statLabel: {
    fontSize: 11,
    color: '#64748b',
    fontWeight: '600',
    marginTop: 4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  chargingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9',
  },
  chargingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  chargingLabel: {
    fontSize: 13,
    color: '#64748b',
    fontWeight: '500',
  },
  chargingBadge: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 12,
  },
  chargingBadgeText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  progressContainer: {
    marginTop: 8,
  },
  progressBarBg: {
    height: 6,
    backgroundColor: '#f1f5f9',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 3,
  },
});
