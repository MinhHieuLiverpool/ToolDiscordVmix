#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(DeviceMonitor, NSObject)

RCT_EXTERN_METHOD(getDeviceStats:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getCpuUsage:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(pingGateway:(NSString *)ip
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getBatteryInfo:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getNetworkType:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getFps:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getPacketLoss:(NSString *)ip
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(startBackgroundLoop:(NSString *)apiUrl
                  serverIp:(NSString *)serverIp
                  wanIp:(NSString *)wanIp
                  nameDevice:(NSString *)nameDevice)

RCT_EXTERN_METHOD(stopBackgroundLoop)

@end
