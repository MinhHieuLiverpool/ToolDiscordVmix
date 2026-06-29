import Foundation
import UIKit
import Darwin
import QuartzCore
import Network
import CoreLocation

@objc(DeviceMonitor)
class DeviceMonitorModule: NSObject, CLLocationManagerDelegate {
    
    private var locationManager: CLLocationManager?
    private var nameDevice: String = ""
    
    private var lastTxBytes: UInt64 = 0
    private var lastRxBytes: UInt64 = 0
    private var lastStatsTime: TimeInterval = 0
    private var backgroundTimer: Timer?
    private var displayLink: CADisplayLink?
    private var currentFps: Double = 60.0
    private var frameCount: Int = 0
    private var lastFpsUpdateTime: CFTimeInterval = 0
    
    // MARK: - Module Setup
    
    @objc static func requiresMainQueueSetup() -> Bool {
        return true
    }
    
    override init() {
        super.init()
        DispatchQueue.main.async {
            UIDevice.current.isBatteryMonitoringEnabled = true
        }
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
                "cpuModel": modelInfo.chip == "Unknown" ? modelInfo.name : "\(modelInfo.name) (\(modelInfo.chip))",
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
                "batteryLevel": batteryLevel >= 0 ? Int((batteryLevel * 100).rounded()) : -1,
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
        frameCount += 1
        
        let currentTime = displayLink.timestamp
        if lastFpsUpdateTime == 0 {
            lastFpsUpdateTime = currentTime
            return
        }
        
        let elapsed = currentTime - lastFpsUpdateTime
        if elapsed >= 1.0 {
            let calculatedFps = Double(frameCount) / elapsed
            currentFps = min(calculatedFps, 240.0)
            currentFps = (currentFps * 10).rounded() / 10
            
            // Reset
            frameCount = 0
            lastFpsUpdateTime = currentTime
        }
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
                                    wanIp: String,
                                    nameDevice: String) {
        stopBackgroundLoop()
        
        self.nameDevice = nameDevice
        
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            
            // Request low-power location updates to keep background execution alive
            self.setupLocationManager()
            
            self.backgroundTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
                self?.postMetricsToServer(apiUrl: apiUrl, serverIp: serverIp, wanIp: wanIp)
            }
        }
    }
    
    // MARK: - stopBackgroundLoop
    
    @objc func stopBackgroundLoop() {
        DispatchQueue.main.async { [weak self] in
            self?.backgroundTimer?.invalidate()
            self?.backgroundTimer = nil
            self?.locationManager?.stopUpdatingLocation()
        }
    }
    
    private func setupLocationManager() {
        if self.locationManager == nil {
            let lm = CLLocationManager()
            lm.delegate = self
            lm.desiredAccuracy = kCLLocationAccuracyThreeKilometers
            lm.distanceFilter = 999999
            lm.allowsBackgroundLocationUpdates = true
            lm.pausesLocationUpdatesAutomatically = false
            self.locationManager = lm
        }
        
        let status: CLAuthorizationStatus
        if #available(iOS 14.0, *) {
            status = self.locationManager?.authorizationStatus ?? .notDetermined
        } else {
            status = CLLocationManager.authorizationStatus()
        }
        
        if status == .notDetermined {
            self.locationManager?.requestAlwaysAuthorization()
        }
        
        self.locationManager?.startUpdatingLocation()
    }
    
    // MARK: - Private Helpers
    
    /// Get local IP address (WiFi en0, fallback to cellular pdp_ip)
    /// Checks IFF_UP and IFF_RUNNING flags to ensure the interface is actually active
    private func getLocalIpAddress() -> String {
        var wifiAddress: String? = nil
        var cellularAddress: String? = nil
        var ethernetAddress: String? = nil
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        
        guard getifaddrs(&ifaddr) == 0, let firstAddr = ifaddr else {
            return "-"
        }
        
        defer { freeifaddrs(ifaddr) }
        
        var ptr = firstAddr
        while true {
            let interface = ptr.pointee
            let addrFamily = interface.ifa_addr.pointee.sa_family
            let flags = Int32(interface.ifa_flags)
            
            // Only consider interfaces that are UP and RUNNING
            let isUp = (flags & IFF_UP) != 0
            let isRunning = (flags & IFF_RUNNING) != 0
            
            if addrFamily == UInt8(AF_INET) && isUp && isRunning {
                let name = String(cString: interface.ifa_name)
                if name != "lo0" { // Exclude loopback
                    var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                    getnameinfo(interface.ifa_addr, socklen_t(interface.ifa_addr.pointee.sa_len),
                                &hostname, socklen_t(hostname.count),
                                nil, 0, NI_NUMERICHOST)
                    let ipStr = String(cString: hostname)
                    
                    // Skip invalid/transitional IPs
                    if ipStr == "0.0.0.0" || ipStr == "127.0.0.1" || ipStr.isEmpty {
                        // do nothing
                    } else if name == "en0" { // WiFi
                        wifiAddress = ipStr
                    } else if name.hasPrefix("pdp_ip") { // Cellular
                        cellularAddress = ipStr
                    } else if name == "en1" || name == "en2" || name == "en3" { // Ethernet/USB
                        ethernetAddress = ipStr
                    }
                }
            }
            
            guard let next = interface.ifa_next else { break }
            ptr = next
        }
        
        // Priority: WiFi > Ethernet > Cellular
        if let wifi = wifiAddress { return wifi }
        if let ethernet = ethernetAddress { return ethernet }
        if let cellular = cellularAddress { return cellular }
        return "-"
    }
    
    /// Synchronously get network type using active network interfaces
    /// Checks IFF_UP and IFF_RUNNING flags to determine the actual active connection
    private func getNetworkTypeSynchronous() -> String {
        var networkType = "-"
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddr) == 0, let firstAddr = ifaddr else {
            return networkType
        }
        defer { freeifaddrs(ifaddr) }
        
        var hasWifi = false
        var hasCellular = false
        var hasEthernet = false
        
        var ptr = firstAddr
        while true {
            let interface = ptr.pointee
            let addrFamily = interface.ifa_addr.pointee.sa_family
            let flags = Int32(interface.ifa_flags)
            
            // Only consider interfaces that are UP and RUNNING
            let isUp = (flags & IFF_UP) != 0
            let isRunning = (flags & IFF_RUNNING) != 0
            
            if (addrFamily == UInt8(AF_INET) || addrFamily == UInt8(AF_INET6)) && isUp && isRunning {
                let name = String(cString: interface.ifa_name)
                if name == "en0" {
                    hasWifi = true
                } else if name.hasPrefix("pdp_ip") {
                    hasCellular = true
                } else if name == "en1" || name == "en2" || name == "en3" {
                    hasEthernet = true
                }
            }
            
            guard let next = interface.ifa_next else { break }
            ptr = next
        }
        
        if hasWifi {
            networkType = "WiFi"
        } else if hasEthernet {
            networkType = "Ethernet"
        } else if hasCellular {
            networkType = "Cellular"
        }
        
        return networkType
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
        // Fetch UI/Main-thread bound values first on the main thread
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            
            UIDevice.current.isBatteryMonitoringEnabled = true
            let batteryLevel = UIDevice.current.batteryLevel
            let batteryState = UIDevice.current.batteryState
            let isCharging = batteryState == .charging || batteryState == .full
            let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? "unknown_ios"
            let currentFpsValue = self.currentFps
            let networkType = self.getNetworkTypeSynchronous()
            
            // Determine charge source from battery state
            var chargeSource = "-"
            if batteryState == .charging {
                chargeSource = "Charging"
            } else if batteryState == .full {
                chargeSource = "Full"
            } else {
                chargeSource = "Not Charging"
            }
            
            // Get temperature approximation from thermal state
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
            
            // Now execute network and heavy system tasks in the background
            DispatchQueue.global(qos: .utility).async { [weak self] in
                guard let self = self else { return }
                
                let modelInfo = IPhoneModelMapper.getModelInfo()
                let ramInfo = self.getSystemMemoryInfo()
                let cpuUsage = self.getSystemCpuUsage()
                let localIp = self.getLocalIpAddress()
                let gatewayIp = self.getGatewayIp()
                
                // Real ping measurements
                var pingGatewayStr = "-"
                if gatewayIp != "-" {
                    let gwResult = self.pingHost(gatewayIp)
                    pingGatewayStr = gwResult == "Timeout" ? "Timeout" : "\(gwResult) ms"
                }
                
                let ping8Result = self.pingHost("8.8.8.8")
                let ping8888Str = ping8Result == "Timeout" ? "Timeout" : "\(ping8Result) ms"
                
                var serverPingStr = "-"
                if !serverIp.isEmpty {
                    let srvResult = self.pingHost(serverIp)
                    serverPingStr = srvResult == "Timeout" ? "Timeout" : "\(srvResult) ms"
                }
                
                // Network traffic for bandwidth
                let trafficInfo = self.getNetworkTraffic()
                let currentTime = Date().timeIntervalSince1970
                var txSpeed: Double = -1.0
                var rxSpeed: Double = -1.0
                
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
                
                // Real packet loss measurement (3 pings for speed)
                var packetLossPercent: Double = -1.0
                let totalPings = 3
                var successCount = 0
                for _ in 0..<totalPings {
                    let result = self.pingHost("8.8.8.8")
                    if result != "Timeout" {
                        successCount += 1
                    }
                }
                packetLossPercent = Double(totalPings - successCount) / Double(totalPings) * 100.0
                
                let formatter = ISO8601DateFormatter()
                
                let payload: [String: Any] = [
                    "deviceId": deviceId,
                    "deviceName": modelInfo.name,
                    "name_device": self.nameDevice,
                    "wanIp": wanIp,
                    "pingGateway": pingGatewayStr,
                    "ping8888": ping8888Str,
                    "serverIp": serverIp,
                    "serverPing": serverPingStr,
                    "cpuLoad": Int(cpuUsage),
                    "localIp": localIp,
                    "gatewayIp": gatewayIp,
                    "cpuModel": modelInfo.chip == "Unknown" ? modelInfo.name : "\(modelInfo.name) (\(modelInfo.chip))",
                    "cpuCores": ProcessInfo.processInfo.activeProcessorCount,
                    "ramTotal": Int64(ProcessInfo.processInfo.physicalMemory),
                    "ramFree": ramInfo.free,
                    "ramUsed": ramInfo.used,
                    "ramUsagePercent": ramInfo.usagePercent,
                    "txSpeedMbps": txSpeed,
                    "rxSpeedMbps": rxSpeed,
                    "batteryLevel": batteryLevel >= 0 ? Int((batteryLevel * 100).rounded()) : -1,
                    "isCharging": isCharging,
                    "chargeSource": chargeSource,
                    "temperature": temperature,
                    "networkType": networkType,
                    "fps": Int(currentFpsValue.rounded()),
                    "packetLoss": packetLossPercent,
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
}
