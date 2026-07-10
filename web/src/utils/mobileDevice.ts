// Helpers to identify mobile devices consistently across pages.
//
// A mobile device can be referenced by three fields:
//   - name_device : friendly name the user can edit (CHANGES on rename)
//   - deviceName  : OS device name (stable)
//   - deviceId    : unique id (stable)
//
// Channels historically stored the friendly display name, which breaks when a
// device is renamed. To be resilient we match a device against a channel by
// checking ANY of its identifiers, and we persist a STABLE key for new picks.

export interface MobileDeviceLike {
  deviceId?: string
  deviceName?: string
  name_device?: string
}

/** All non-empty identifiers a device can be referenced by. */
export function getMobileIdentifiers(item: MobileDeviceLike): string[] {
  return Array.from(
    new Set(
      [item.name_device, item.deviceName, item.deviceId].filter(
        (v): v is string => Boolean(v && v.trim())
      )
    )
  )
}

/** Friendly label for UI (prefers the user-defined name). */
export function getMobileDisplayName(item: MobileDeviceLike): string {
  return item.name_device || item.deviceName || item.deviceId || 'Thiết bị'
}

/** Stable key to persist so renaming the friendly name never breaks membership. */
export function getMobileStableKey(item: MobileDeviceLike): string {
  return item.deviceId || item.deviceName || item.name_device || ''
}

/** True if the given stored key list references this device by any identifier. */
export function machinesIncludeDevice(
  machines: string[] | undefined,
  item: MobileDeviceLike
): boolean {
  if (!machines || machines.length === 0) return false
  const ids = getMobileIdentifiers(item)
  return machines.some((m) => ids.includes(m))
}
