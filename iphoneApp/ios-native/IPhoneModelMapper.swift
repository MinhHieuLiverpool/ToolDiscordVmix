import Foundation

/// Maps internal iPhone model identifiers to commercial names and chip info
struct IPhoneModelMapper {
    
    struct ModelInfo {
        let name: String
        let chip: String
    }
    
    /// Get the current device's machine identifier (e.g., "iPhone14,5")
    static func getMachineIdentifier() -> String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let machineMirror = Mirror(reflecting: systemInfo.machine)
        let identifier = machineMirror.children.reduce("") { identifier, element in
            guard let value = element.value as? Int8, value != 0 else { return identifier }
            return identifier + String(UnicodeScalar(UInt8(value)))
        }
        return identifier
    }
    
    /// Mapping table: internal identifier → (Commercial Name, Chip)
    static let models: [String: ModelInfo] = [
        // iPhone SE
        "iPhone8,4": ModelInfo(name: "iPhone SE (1st gen)", chip: "Apple A9"),
        "iPhone12,8": ModelInfo(name: "iPhone SE (2nd gen)", chip: "Apple A13 Bionic"),
        "iPhone14,6": ModelInfo(name: "iPhone SE (3rd gen)", chip: "Apple A15 Bionic"),
        
        // iPhone 8 series
        "iPhone10,1": ModelInfo(name: "iPhone 8", chip: "Apple A11 Bionic"),
        "iPhone10,4": ModelInfo(name: "iPhone 8", chip: "Apple A11 Bionic"),
        "iPhone10,2": ModelInfo(name: "iPhone 8 Plus", chip: "Apple A11 Bionic"),
        "iPhone10,5": ModelInfo(name: "iPhone 8 Plus", chip: "Apple A11 Bionic"),
        
        // iPhone X series
        "iPhone10,3": ModelInfo(name: "iPhone X", chip: "Apple A11 Bionic"),
        "iPhone10,6": ModelInfo(name: "iPhone X", chip: "Apple A11 Bionic"),
        "iPhone11,2": ModelInfo(name: "iPhone XS", chip: "Apple A12 Bionic"),
        "iPhone11,4": ModelInfo(name: "iPhone XS Max", chip: "Apple A12 Bionic"),
        "iPhone11,6": ModelInfo(name: "iPhone XS Max", chip: "Apple A12 Bionic"),
        "iPhone11,8": ModelInfo(name: "iPhone XR", chip: "Apple A12 Bionic"),
        
        // iPhone 11 series
        "iPhone12,1": ModelInfo(name: "iPhone 11", chip: "Apple A13 Bionic"),
        "iPhone12,3": ModelInfo(name: "iPhone 11 Pro", chip: "Apple A13 Bionic"),
        "iPhone12,5": ModelInfo(name: "iPhone 11 Pro Max", chip: "Apple A13 Bionic"),
        
        // iPhone 12 series
        "iPhone13,1": ModelInfo(name: "iPhone 12 mini", chip: "Apple A14 Bionic"),
        "iPhone13,2": ModelInfo(name: "iPhone 12", chip: "Apple A14 Bionic"),
        "iPhone13,3": ModelInfo(name: "iPhone 12 Pro", chip: "Apple A14 Bionic"),
        "iPhone13,4": ModelInfo(name: "iPhone 12 Pro Max", chip: "Apple A14 Bionic"),
        
        // iPhone 13 series
        "iPhone14,4": ModelInfo(name: "iPhone 13 mini", chip: "Apple A15 Bionic"),
        "iPhone14,5": ModelInfo(name: "iPhone 13", chip: "Apple A15 Bionic"),
        "iPhone14,2": ModelInfo(name: "iPhone 13 Pro", chip: "Apple A15 Bionic"),
        "iPhone14,3": ModelInfo(name: "iPhone 13 Pro Max", chip: "Apple A15 Bionic"),
        
        // iPhone 14 series
        "iPhone14,7": ModelInfo(name: "iPhone 14", chip: "Apple A15 Bionic"),
        "iPhone14,8": ModelInfo(name: "iPhone 14 Plus", chip: "Apple A15 Bionic"),
        "iPhone15,2": ModelInfo(name: "iPhone 14 Pro", chip: "Apple A16 Bionic"),
        "iPhone15,3": ModelInfo(name: "iPhone 14 Pro Max", chip: "Apple A16 Bionic"),
        
        // iPhone 15 series
        "iPhone15,4": ModelInfo(name: "iPhone 15", chip: "Apple A16 Bionic"),
        "iPhone15,5": ModelInfo(name: "iPhone 15 Plus", chip: "Apple A16 Bionic"),
        "iPhone16,1": ModelInfo(name: "iPhone 15 Pro", chip: "Apple A17 Pro"),
        "iPhone16,2": ModelInfo(name: "iPhone 15 Pro Max", chip: "Apple A17 Pro"),
        
        // iPhone 16 series
        "iPhone17,1": ModelInfo(name: "iPhone 16 Pro", chip: "Apple A18 Pro"),
        "iPhone17,2": ModelInfo(name: "iPhone 16 Pro Max", chip: "Apple A18 Pro"),
        "iPhone17,3": ModelInfo(name: "iPhone 16", chip: "Apple A18"),
        "iPhone17,4": ModelInfo(name: "iPhone 16 Plus", chip: "Apple A18"),
        "iPhone17,5": ModelInfo(name: "iPhone 16e", chip: "Apple A18"),
        
        // Simulators
        "i386": ModelInfo(name: "Simulator", chip: "x86"),
        "x86_64": ModelInfo(name: "Simulator", chip: "x86_64"),
        "arm64": ModelInfo(name: "Simulator", chip: "Apple Silicon"),
    ]
    
    /// Get model info for the current device
    static func getModelInfo() -> ModelInfo {
        let identifier = getMachineIdentifier()
        if let info = models[identifier] {
            return info
        }
        // Fallback: return raw identifier
        return ModelInfo(name: identifier, chip: "Unknown")
    }
    
    /// Get just the commercial name
    static func getModelName() -> String {
        return getModelInfo().name
    }
    
    /// Get just the chip name
    static func getChipName() -> String {
        return getModelInfo().chip
    }
}
