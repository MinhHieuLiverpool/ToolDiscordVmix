import React from 'react';
import { StyleSheet, View, Text } from 'react-native';

interface GatewayPingCardProps {
  pingStatus: string;
}

export function GatewayPingCard({ pingStatus }: GatewayPingCardProps) {
  
  // Determine color and rating label based on latency value
  const getPingDetails = () => {
    if (pingStatus === '-' || pingStatus === 'N/A') return { label: 'Idle', color: '#64748b' };
    if (pingStatus === 'Timeout') return { label: 'Offline', color: '#ef4444' };
    const value = parseFloat(pingStatus);
    if (isNaN(value)) return { label: 'Error', color: '#ef4444' };
    if (value < 5) return { label: 'Excellent', color: '#10b981' };
    if (value < 20) return { label: 'Good', color: '#0ea5e9' };
    return { label: 'High Latency', color: '#f97316' };
  };

  const pingDetails = getPingDetails();

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderWithAction}>
        <Text style={styles.cardTitle}>Gateway Diagnostics</Text>
        <View style={[styles.pillBadge, { backgroundColor: pingDetails.color + '15' }]}>
          <Text style={[styles.pillText, { color: pingDetails.color }]}>{pingDetails.label}</Text>
        </View>
      </View>
      
      <View style={styles.pingDisplay}>
        <Text style={styles.pingLabel}>Ping to Default Gateway</Text>
        <Text style={[styles.pingValue, { color: pingDetails.color }]}>{pingStatus}</Text>
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
  cardHeaderWithAction: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0ea5e9',
  },
  pillBadge: {
    borderRadius: 12,
    paddingVertical: 2,
    paddingHorizontal: 8,
  },
  pillText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  pingDisplay: {
    alignItems: 'center',
    marginVertical: 10,
    backgroundColor: '#f8fafc',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f1f5f9',
  },
  pingLabel: {
    color: '#64748b',
    fontSize: 13,
    marginBottom: 6,
    fontWeight: '500',
  },
  pingValue: {
    fontSize: 28,
    fontWeight: 'bold',
  },
});
