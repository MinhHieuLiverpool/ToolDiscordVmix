import Foundation
import UIKit
import Darwin
import QuartzCore
import Network

@objc(DeviceMonitor)
class DeviceMonitorModule: NSObject {
    
    private var lastTxBytes: UInt64 = 0
    private var lastRxBytes: UInt64 = 0
    private var lastStatsTime: TimeInterval = 0
    private var backgroundTimer: Timer?
    private var displayLink: CADisplayLink?
    private var lastFrameTimestamp: CFTimeInterval = 0
    private var currentFps: Double = 60.0
    
    // MARK: - Module Setup
    
    @objc static func requiresMainQueueSetup() -> Bool {
        return false
    }
    
    @objc static func moduleName() -> String! {
        return "DeviceMonitor"
    }
    
    // MARK: - getDeviceStats
    
    @objc func getDeviceStats(_ resolve: @escaping RCTPromiseResolveBlock,
                               rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            
            let modelInfo = IPhoneModelMapper.getModelInfo()
            let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? "unknown_ios"
            let localIp = self.getLocalIpAddress()
            let gatewayIp = self.getGatewayIp()
            let cpuCores = ProcessInfo.processInfo.activeProcessorCount
            let ramTotal = Int64(ProcessInfo.processInfo.physicalMemory)
            let ramInfo = self.getSystemMemoryInfo()
            
            // Network traffic
            let trafficInfo = self.getNetworkTraffic()
            let currentTime = Date().timeIntervalSince1970
            
            var txSpeed: Double = 0
            var rxSpeed: Double = 0
            
            if self.lastStatsTime > 0 {
                let timeDiff = currentTime - self.lastStatsTime
                if timeDiff > 0 {
                    let txDiff = trafficInfo.tx >= self.lastTxBytes ? trafficInfo.tx - self.lastTxBytes : 0
                    let rxDiff = trafficInfo.rx >= self.lastRxBytes ? trafficInfo.rx - self.lastRxBytes : 0
                    txSpeed = Double(txDiff) * 8.0 / (timeDiff * 1_000_000.0)
                    rxSpeed = Double(rxDiff) * 8.0 / (timeDiff * 1_000_000.0)
                    txSpeed = (txSpeed * 100).rounded() / 100
                    rxSpeed = (rxSpeed * 100).rounded() / 100
                }
            }
            
            self.lastTxBytes = trafficInfo.tx
            self.lastRxBytes = trafficInfo.rx
            self.lastStatsTime = currentTime
            
            let result: [String: Any] = [
                "deviceId": deviceId,
                "localIp": localIp,
                "gatewayIp": gatewayIp,
                "cpuModel": "\(modelInfo.name) (\(modelInfo.chip))",
                "cpuCores": cpuCores,
                "ramTotal": ramTotal,
                "ramFree": ramInfo.free,
                "ramUsed": ramInfo.used,
                "ramUsagePercent": ramInfo.usagePercent,
                "txSpeedMbps": txSpeed,
                "rxSpeedMbps": rxSpeed
            ]
            
            resolve(result)
        }
    }
    
    // MARK: - getCpuUsage
    
    @objc func getCpuUsage(_ resolve: @escaping RCTPromiseResolveBlock,
                            rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.global(qos: .userInitiated).async {
            let cpuUsage = self.getSystemCpuUsage()
            resolve(cpuUsage)
        }
    }
    
    // MARK: - pingGateway
    
    @objc func pingGateway(_ ip: String,
                            resolver resolve: @escaping RCTPromiseResolveBlock,
                            rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.global(qos: .userInitiated).async {
            let result = self.pingHost(ip)
            resolve(result)
        }
    }
    
    // MARK: - getBatteryInfo
    
    @objc func getBatteryInfo(_ resolve: @escaping RCTPromiseResolveBlock,
                               rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            UIDevice.current.isBatteryMonitoringEnabled = true
            
            let batteryLevel = UIDevice.current.batteryLevel
            let batteryState = UIDevice.current.batteryState
            let isCharging = batteryState == .charging || batteryState == .full
            
            var chargeSource = "-"
            if isCharging {
                chargeSource = "Charging" // iOS doesn't distinguish USB/AC/Wireless easily
            }
            
            // Temperature approximation from thermal state
            let thermalState = ProcessInfo.processInfo.thermalState
            let temperature: Double
            switch thermalState {
            case .nominal:
                temperature = 25.0
            case .fair:
                temperature = 35.0
            case .serious:
                temperature = 42.0
            case .critical:
                temperature = 48.0
            @unknown default:
                temperature = 25.0
            }
            
            let result: [String: Any] = [
                "batteryLevel": batteryLevel >= 0 ? Int(batteryLevel * 100) : -1,
                "isCharging": isCharging,
                "chargeSource": chargeSource,
                "temperature": temperature
            ]
            
            resolve(result)
        }
    }
    
    // MARK: - getNetworkType
    
    @objc func getNetworkType(_ resolve: @escaping RCTPromiseResolveBlock,
                               rejecter reject: @escaping RCTPromiseRejectBlock) {
        let monitor = NWPathMonitor()
        let queue = DispatchQueue(label: "NetworkTypeCheck")
        
        monitor.pathUpdateHandler = { path in
            monitor.cancel()
            
            var networkType = "-"
            if path.status == .satisfied {
                if path.usesInterfaceType(.wifi) {
                    networkType = "WiFi"
                } else if path.usesInterfaceType(.cellular) {
                    networkType = "Cellular"
                } else if path.usesInterfaceType(.wiredEthernet) {
                    networkType = "Ethernet"
                } else {
                    networkType = "Other"
                }
            }
            
            resolve(networkType)
        }
        
        monitor.start(queue: queue)
    }
    
    // MARK: - getFps
    
    @objc func getFps(_ resolve: @escaping RCTPromiseResolveBlock,
                       rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else {
                resolve(60.0)
                return
            }
            
            if self.displayLink == nil {
                self.displayLink = CADisplayLink(target: self, selector: #selector(self.handleDisplayLink(_:)))
                self.displayLink?.add(to: .main, forMode: .common)
            }
            
            resolve(self.currentFps)
        }
    }
    
    @objc private func handleDisplayLink(_ displayLink: CADisplayLink) {
        if lastFrameTimestamp > 0 {
            let diff = displayLink.timestamp - lastFrameTimestamp
            if diff > 0 {
                let fps = 1.0 / diff
                currentFps = min(fps, 240.0)
                currentFps = (currentFps * 10).rounded() / 10
            }
        }
        lastFrameTimestamp = displayLink.timestamp
    }
    
    // MARK: - getPacketLoss
    
    @objc func getPacketLoss(_ ip: String,
                              resolver resolve: @escaping RCTPromiseResolveBlock,
                              rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.global(qos: .userInitiated).async {
            var successCount = 0
            let totalPings = 5
            
            for _ in 0..<totalPings {
                let result = self.pingHost(ip)
                if result != "Timeout" {
                    successCount += 1
                }
            }
            
            let lossPercent = Double(totalPings - successCount) / Double(totalPings) * 100.0
            resolve(lossPercent)
        }
    }
    
    // MARK: - startBackgroundLoop
    
    @objc func startBackgroundLoop(_ apiUrl: String,
                                    serverIp: String,
                                    wanIp: String) {
        stopBackgroundLoop()
        
        DispatchQueue.main.async { [weak self] in
            self?.backgroundTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
                self?.postMetricsToServer(apiUrl: apiUrl, serverIp: serverIp, wanIp: wanIp)
            }
        }
    }
    
    // MARK: - stopBackgroundLoop
    
    @objc func stopBackgroundLoop() {
        DispatchQueue.main.async { [weak self] in
            self?.backgroundTimer?.invalidate()
            self?.backgroundTimer = nil
        }
    }
    
    // MARK: - Private Helpers
    
    /// Get local IP address (WiFi interface en0)
    private func getLocalIpAddress() -> String {
        var address = "-"
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        
        guard getifaddrs(&ifaddr) == 0, let firstAddr = ifaddr else {
            return address
        }
        
        defer { freeifaddrs(ifaddr) }
        
        var ptr = firstAddr
        while true {
            let interface = ptr.pointee
            let addrFamily = interface.ifa_addr.pointee.sa_family
            
            if addrFamily == UInt8(AF_INET) {
                let name = String(cString: interface.ifa_name)
                if name == "en0" { // WiFi
                    var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                    getnameinfo(interface.ifa_addr, socklen_t(interface.ifa_addr.pointee.sa_len),
                                &hostname, socklen_t(hostname.count),
                                nil, 0, NI_NUMERICHOST)
                    address = String(cString: hostname)
                    break
                }
            }
            
            guard let next = interface.ifa_next else { break }
            ptr = next
        }
        
        return address
    }
    
    /// Get gateway IP address
    private func getGatewayIp() -> String {
        // Use routing table to find default gateway
        var mib: [Int32] = [CTL_NET, PF_ROUTE, 0, AF_INET, NET_RT_FLAGS, RTF_GATEWAY]
        var bufferSize: Int = 0
        
        guard sysctl(&mib, UInt32(mib.count), nil, &bufferSize, nil, 0) == 0, bufferSize > 0 else {
            return "-"
        }
        
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        defer { buffer.deallocate() }
        
        guard sysctl(&mib, UInt32(mib.count), buffer, &bufferSize, nil, 0) == 0 else {
            return "-"
        }
        
        // Parse routing table entries
        var offset = 0
        while offset < bufferSize {
            let rtm = buffer.advanced(by: offset).withMemoryRebound(to: rt_msghdr.self, capacity: 1) { $0.pointee }
            
            if rtm.rtm_flags & RTF_GATEWAY != 0 {
                let sa = buffer.advanced(by: offset + MemoryLayout<rt_msghdr>.size)
                // Skip destination sockaddr
                let dstSa = sa.withMemoryRebound(to: sockaddr.self, capacity: 1) { $0.pointee }
                let gatewayOffset = Int(dstSa.sa_len)
                
                let gatewaySa = sa.advanced(by: gatewayOffset).withMemoryRebound(to: sockaddr_in.self, capacity: 1) { $0.pointee }
                if gatewaySa.sin_family == UInt8(AF_INET) {
                    var addr = gatewaySa.sin_addr
                    let ipStr = String(cString: inet_ntoa(addr))
                    return ipStr
                }
            }
            
            offset += Int(rtm.rtm_msglen)
        }
        
        return "-"
    }
    
    /// Get system memory info using vm_statistics64
    private func getSystemMemoryInfo() -> (free: Int64, used: Int64, usagePercent: Double) {
        let totalRam = Int64(ProcessInfo.processInfo.physicalMemory)
        
        var vmStats = vm_statistics64()
        var count = mach_msg_type_number_t(MemoryLayout<vm_statistics64>.size / MemoryLayout<integer_t>.size)
        let pageSize = Int64(vm_kernel_page_size)
        
        let result = withUnsafeMutablePointer(to: &vmStats) { ptr in
            ptr.withMemoryRebound(to: integer_t.self, capacity: Int(count)) { intPtr in
                host_statistics64(mach_host_self(), HOST_VM_INFO64,
                                  intPtr, &count)
            }
        }
        
        guard result == KERN_SUCCESS else {
            return (free: totalRam / 2, used: totalRam / 2, usagePercent: 50.0)
        }
        
        let freePages = Int64(vmStats.free_count) + Int64(vmStats.inactive_count)
        let freeRam = freePages * pageSize
        let usedRam = totalRam - freeRam
        let usagePercent = (Double(usedRam) / Double(totalRam)) * 100.0
        let roundedPercent = (usagePercent * 10).rounded() / 10
        
        return (free: freeRam, used: usedRam, usagePercent: roundedPercent)
    }
    
    /// Get system-wide CPU usage using host_processor_info
    private func getSystemCpuUsage() -> Double {
        var numCPUs: natural_t = 0
        var cpuInfo: processor_info_array_t?
        var numCpuInfo: mach_msg_type_number_t = 0
        
        let result = host_processor_info(mach_host_self(),
                                          PROCESSOR_CPU_LOAD_INFO,
                                          &numCPUs,
                                          &cpuInfo,
                                          &numCpuInfo)
        
        guard result == KERN_SUCCESS, let info = cpuInfo else {
            return 0.0
        }
        
        var totalUser: Int32 = 0
        var totalSystem: Int32 = 0
        var totalIdle: Int32 = 0
        var totalNice: Int32 = 0
        
        for i in 0..<Int(numCPUs) {
            let offset = Int(CPU_STATE_MAX) * i
            totalUser += info[offset + Int(CPU_STATE_USER)]
            totalSystem += info[offset + Int(CPU_STATE_SYSTEM)]
            totalIdle += info[offset + Int(CPU_STATE_IDLE)]
            totalNice += info[offset + Int(CPU_STATE_NICE)]
        }
        
        let totalTicks = totalUser + totalSystem + totalIdle + totalNice
        let usedTicks = totalUser + totalSystem + totalNice
        
        // Deallocate
        let size = vm_size_t(numCpuInfo) * vm_size_t(MemoryLayout<integer_t>.size)
        vm_deallocate(mach_task_self_, vm_address_t(bitPattern: info), size)
        
        guard totalTicks > 0 else { return 0.0 }
        
        let usage = (Double(usedTicks) / Double(totalTicks)) * 100.0
        return (usage * 10).rounded() / 10
    }
    
    /// Get network traffic bytes (tx/rx) from all interfaces
    private func getNetworkTraffic() -> (tx: UInt64, rx: UInt64) {
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddr) == 0, let firstAddr = ifaddr else {
            return (0, 0)
        }
        defer { freeifaddrs(ifaddr) }
        
        var totalTx: UInt64 = 0
        var totalRx: UInt64 = 0
        
        var ptr = firstAddr
        while true {
            let interface = ptr.pointee
            let addrFamily = interface.ifa_addr.pointee.sa_family
            
            if addrFamily == UInt8(AF_LINK) {
                let name = String(cString: interface.ifa_name)
                if name == "en0" || name == "pdp_ip0" { // WiFi or Cellular
                    let data = interface.ifa_data.assumingMemoryBound(to: if_data.self).pointee
                    totalTx += UInt64(data.ifi_obytes)
                    totalRx += UInt64(data.ifi_ibytes)
                }
            }
            
            guard let next = interface.ifa_next else { break }
            ptr = next
        }
        
        return (tx: totalTx, rx: totalRx)
    }
    
    /// Ping a host using socket-based ICMP
    private func pingHost(_ host: String) -> String {
        let startTime = Date()
        
        // Resolve hostname
        var hints = addrinfo()
        hints.ai_family = AF_INET
        hints.ai_socktype = SOCK_DGRAM
        
        var result: UnsafeMutablePointer<addrinfo>?
        let status = getaddrinfo(host, nil, &hints, &result)
        guard status == 0, let addrInfo = result else {
            return "Timeout"
        }
        defer { freeaddrinfo(result) }
        
        // Create raw ICMP socket
        let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_ICMP)
        guard sock >= 0 else {
            return "Timeout"
        }
        defer { close(sock) }
        
        // Set timeout
        var timeout = timeval(tv_sec: 2, tv_usec: 0)
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        
        // Build ICMP echo request
        var icmpPacket = [UInt8](repeating: 0, count: 64)
        icmpPacket[0] = 8  // Type: Echo Request
        icmpPacket[1] = 0  // Code
        icmpPacket[2] = 0  // Checksum (will be calculated)
        icmpPacket[3] = 0
        icmpPacket[4] = 0  // Identifier
        icmpPacket[5] = 1
        icmpPacket[6] = 0  // Sequence
        icmpPacket[7] = 1
        
        // Calculate checksum
        var checksum: UInt32 = 0
        for i in stride(from: 0, to: icmpPacket.count, by: 2) {
            let word = UInt32(icmpPacket[i]) << 8
            let nextByte = i + 1 < icmpPacket.count ? UInt32(icmpPacket[i + 1]) : 0
            checksum += word + nextByte
        }
        checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum += checksum >> 16
        let finalChecksum = UInt16(~checksum & 0xFFFF)
        icmpPacket[2] = UInt8(finalChecksum >> 8)
        icmpPacket[3] = UInt8(finalChecksum & 0xFF)
        
        // Send
        let destAddr = addrInfo.pointee.ai_addr
        let destLen = addrInfo.pointee.ai_addrlen
        let sendResult = sendto(sock, icmpPacket, icmpPacket.count, 0, destAddr, destLen)
        guard sendResult > 0 else {
            return "Timeout"
        }
        
        // Receive
        var receiveBuffer = [UInt8](repeating: 0, count: 1024)
        let recvResult = recv(sock, &receiveBuffer, receiveBuffer.count, 0)
        
        if recvResult > 0 {
            let elapsed = Date().timeIntervalSince(startTime) * 1000.0
            let ms = (elapsed * 10).rounded() / 10
            return "\(ms)"
        }
        
        return "Timeout"
    }
    
    /// Post metrics to backend server
    private func postMetricsToServer(apiUrl: String, serverIp: String, wanIp: String) {
        DispatchQueue.global(qos: .utility).async { [weak self] in
            guard let self = self else { return }
            
            let modelInfo = IPhoneModelMapper.getModelInfo()
            let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? "unknown_ios"
            let ramInfo = self.getSystemMemoryInfo()
            let trafficInfo = self.getNetworkTraffic()
            let cpuUsage = self.getSystemCpuUsage()
            
            UIDevice.current.isBatteryMonitoringEnabled = true
            let batteryLevel = UIDevice.current.batteryLevel
            let batteryState = UIDevice.current.batteryState
            let isCharging = batteryState == .charging || batteryState == .full
            
            let thermalState = ProcessInfo.processInfo.thermalState
            let temperature: Double
            switch thermalState {
            case .nominal: temperature = 25.0
            case .fair: temperature = 35.0
            case .serious: temperature = 42.0
            case .critical: temperature = 48.0
            @unknown default: temperature = 25.0
            }
            
            let pingGw = self.pingHost(self.getGatewayIp())
            let ping8 = self.pingHost("8.8.8.8")
            var serverPingResult = "-"
            if !serverIp.isEmpty {
                serverPingResult = self.pingHost(serverIp)
            }
            
            let formatter = ISO8601DateFormatter()
            
            let payload: [String: Any] = [
                "deviceId": deviceId,
                "deviceName": modelInfo.name,
                "wanIp": wanIp,
                "pingGateway": pingGw == "Timeout" ? "Timeout" : "\(pingGw) ms",
                "ping8888": ping8 == "Timeout" ? "Timeout" : "\(ping8) ms",
                "serverIp": serverIp,
                "serverPing": serverPingResult == "Timeout" ? "Timeout" : (serverPingResult == "-" ? "-" : "\(serverPingResult) ms"),
                "cpuLoad": Int(cpuUsage),
                "localIp": self.getLocalIpAddress(),
                "gatewayIp": self.getGatewayIp(),
                "cpuModel": "\(modelInfo.name) (\(modelInfo.chip))",
                "cpuCores": ProcessInfo.processInfo.activeProcessorCount,
                "ramTotal": Int64(ProcessInfo.processInfo.physicalMemory),
                "ramFree": ramInfo.free,
                "ramUsed": ramInfo.used,
                "ramUsagePercent": ramInfo.usagePercent,
                "txSpeedMbps": 0,
                "rxSpeedMbps": 0,
                "batteryLevel": batteryLevel >= 0 ? Int(batteryLevel * 100) : -1,
                "isCharging": isCharging,
                "chargeSource": isCharging ? "Charging" : "-",
                "temperature": temperature,
                "networkType": "iOS",
                "fps": self.currentFps,
                "packetLoss": 0,
                "timestamp": formatter.string(from: Date())
            ]
            
            guard let url = URL(string: apiUrl),
                  let jsonData = try? JSONSerialization.data(withJSONObject: payload) else {
                return
            }
            
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = jsonData
            
            URLSession.shared.dataTask(with: request) { _, _, error in
                if let error = error {
                    print("Error posting metrics: \(error.localizedDescription)")
                }
            }.resume()
        }
    }
}
