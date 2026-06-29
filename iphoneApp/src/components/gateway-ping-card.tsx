import React, { useState } from 'react';
import { StyleSheet, View, Text, TextInput, TouchableOpacity, Platform } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface PingCardProps {
  pingGateway: string;
  ping8888: string;
  savedServerIp: string;
  serverPing: string;
  onSaveServerIp: (ip: string) => void;
  nameDevice: string;
  onSaveNameDevice: (name: string) => void;
}

export function GatewayPingCard({
  pingGateway,
  ping8888,
  savedServerIp,
  serverPing,
  onSaveServerIp,
  nameDevice,
  onSaveNameDevice,
}: PingCardProps) {
  const [inputIp, setInputIp] = useState(savedServerIp);
  const [inputName, setInputName] = useState(nameDevice);

  const getPingDetails = (ping: string) => {
    if (ping === '-' || ping === 'N/A') return { label: 'Idle', color: '#64748b' };
    if (ping === 'Timeout') return { label: 'Offline', color: '#ef4444' };
    if (ping === 'Error') return { label: 'Error', color: '#ef4444' };
    const value = parseFloat(ping);
    if (isNaN(value)) return { label: 'Error', color: '#ef4444' };
    if (value < 5) return { label: 'Excellent', color: '#10b981' };
    if (value < 20) return { label: 'Good', color: '#0ea5e9' };
    if (value < 50) return { label: 'OK', color: '#f59e0b' };
    return { label: 'High', color: '#ef4444' };
  };

  const gwDetails = getPingDetails(pingGateway);
  const dns8Details = getPingDetails(ping8888);
  const serverDetails = getPingDetails(serverPing);

  const handleSaveIp = () => {
    const trimmed = inputIp.trim();
    if (trimmed.length > 0) {
      onSaveServerIp(trimmed);
    }
  };

  const handleSaveName = () => {
    const trimmed = inputName.trim();
    onSaveNameDevice(trimmed);
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <MaterialCommunityIcons name="radar" size={20} color="#0ea5e9" />
        <Text style={styles.cardTitle}>Ping Diagnostics</Text>
      </View>

      {/* Gateway Ping */}
      <View style={styles.pingRow}>
        <View style={styles.pingInfo}>
          <MaterialCommunityIcons name="router-wireless" size={18} color="#334155" />
          <Text style={styles.pingTarget}>Gateway</Text>
          <View style={[styles.pillBadge, { backgroundColor: gwDetails.color + '15' }]}>
            <Text style={[styles.pillText, { color: gwDetails.color }]}>{gwDetails.label}</Text>
          </View>
        </View>
        <Text style={[styles.pingValue, { color: gwDetails.color }]}>{pingGateway}</Text>
      </View>

      {/* 8.8.8.8 Ping */}
      <View style={styles.pingRow}>
        <View style={styles.pingInfo}>
          <MaterialCommunityIcons name="google" size={18} color="#334155" />
          <Text style={styles.pingTarget}>8.8.8.8</Text>
          <View style={[styles.pillBadge, { backgroundColor: dns8Details.color + '15' }]}>
            <Text style={[styles.pillText, { color: dns8Details.color }]}>{dns8Details.label}</Text>
          </View>
        </View>
        <Text style={[styles.pingValue, { color: dns8Details.color }]}>{ping8888}</Text>
      </View>

      {/* Custom Server Ping */}
      <View style={styles.serverSection}>
        <View style={styles.serverHeader}>
          <MaterialCommunityIcons name="trophy" size={18} color="#334155" />
          <Text style={styles.serverLabel}>Server Giải Đấu</Text>
        </View>
        <View style={styles.serverInputRow}>
          <TextInput
            style={styles.serverInput}
            placeholder="Nhập IP server..."
            placeholderTextColor="#94a3b8"
            value={inputIp}
            onChangeText={setInputIp}
            keyboardType="numeric"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <TouchableOpacity
            style={[styles.saveButton, inputIp.trim().length === 0 && styles.saveButtonDisabled]}
            onPress={handleSaveIp}
            disabled={inputIp.trim().length === 0}
            activeOpacity={0.7}
          >
            <MaterialCommunityIcons name="content-save" size={18} color="#ffffff" />
            <Text style={styles.saveButtonText}>Save</Text>
          </TouchableOpacity>
        </View>
        {savedServerIp.length > 0 && (
          <View style={styles.pingRow}>
            <View style={styles.pingInfo}>
              <MaterialCommunityIcons name="server-network" size={18} color="#334155" />
              <Text style={styles.pingTarget}>{savedServerIp}</Text>
              <View style={[styles.pillBadge, { backgroundColor: serverDetails.color + '15' }]}>
                <Text style={[styles.pillText, { color: serverDetails.color }]}>{serverDetails.label}</Text>
              </View>
            </View>
            <Text style={[styles.pingValue, { color: serverDetails.color }]}>{serverPing}</Text>
          </View>
        )}
      </View>

      {/* Device Name Custom Input */}
      <View style={[styles.serverSection, { marginTop: 12 }]}>
        <View style={styles.serverHeader}>
          <MaterialCommunityIcons name="cellphone-cog" size={18} color="#334155" />
          <Text style={styles.serverLabel}>Tên Thiết Bị (name_device)</Text>
        </View>
        <View style={styles.serverInputRow}>
          <TextInput
            style={styles.serverInput}
            placeholder="Nhập tên thiết bị (Ví dụ: iPhone 15 Pro Max)..."
            placeholderTextColor="#94a3b8"
            value={inputName}
            onChangeText={setInputName}
            autoCapitalize="words"
            autoCorrect={false}
          />
          <TouchableOpacity
            style={styles.saveButton}
            onPress={handleSaveName}
            activeOpacity={0.7}
          >
            <MaterialCommunityIcons name="content-save" size={18} color="#ffffff" />
            <Text style={styles.saveButtonText}>Save</Text>
          </TouchableOpacity>
        </View>
        {nameDevice.length > 0 && (
          <View style={[styles.pingRow, { borderBottomWidth: 0, paddingBottom: 0 }]}>
            <View style={styles.pingInfo}>
              <MaterialCommunityIcons name="tag-outline" size={18} color="#334155" />
              <Text style={styles.pingTarget}>Tên đã lưu: {nameDevice}</Text>
            </View>
          </View>
        )}
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
  pingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  pingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 8,
  },
  pingTarget: {
    color: '#334155',
    fontSize: 13,
    fontWeight: '600',
  },
  pillBadge: {
    borderRadius: 10,
    paddingVertical: 2,
    paddingHorizontal: 7,
  },
  pillText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
  pingValue: {
    fontSize: 16,
    fontWeight: 'bold',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    minWidth: 80,
    textAlign: 'right',
  },
  serverSection: {
    marginTop: 14,
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#f1f5f9',
  },
  serverHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  serverLabel: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#334155',
  },
  serverInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  serverInput: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: '#0f172a',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0ea5e9',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 10,
    gap: 6,
    shadowColor: '#0ea5e9',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  saveButtonDisabled: {
    backgroundColor: '#94a3b8',
    shadowOpacity: 0,
    elevation: 0,
  },
  saveButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
  },
});
