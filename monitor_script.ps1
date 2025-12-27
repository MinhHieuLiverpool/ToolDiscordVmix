param(
  [string]$Ports = "22131,22132,22133,15000",
  [string]$Names = "'CAM LIA','CAM CAN','CAM TOAN','Ban Pick'",
  [string]$Webhook,
  [string]$Prefix = "SRT",
  [int]$PollMs = 1000,
  [int]$WanRefreshSec = 300
)

# Parse ports and names
$PortArray = $Ports -split ',' | ForEach-Object { [int]$_.Trim() }
$NameArray = $Names -split ',' | ForEach-Object { $_.Trim().Trim("'").Trim('"') }

# Default webhook, auto-upgrade to discord.com
$DefaultWebhook = 'https://discord.com/api/webhooks/1448559948408684669/s6plN6AIy9IFBo6coyNCF9YmmHIfIIVe-tEntpPnArRGI0JdIyl1pCz10rL5TyTP1JV6'
if (-not $Webhook -or [string]::IsNullOrWhiteSpace($Webhook)) { $Webhook = $DefaultWebhook }
if ($Webhook -match '^https://discordapp\.com') { $Webhook = $Webhook -replace '^https://discordapp\.com','https://discord.com' }

# Align Names with Ports
if ($NameArray.Count -lt $PortArray.Count) { 
  for ($i=$NameArray.Count; $i -lt $PortArray.Count; $i++) { 
    $NameArray += "port$($PortArray[$i])" 
  } 
}
elseif ($NameArray.Count -gt $PortArray.Count) { 
  $NameArray = $NameArray[0..($PortArray.Count-1)] 
}

# TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Send-DiscordStrict([string]$Message) {
  $json = [PSCustomObject]@{ content = $Message } | ConvertTo-Json -Depth 3
  try {
    $req = Invoke-WebRequest -UseBasicParsing -Method Post -Uri $Webhook -ContentType 'application/json; charset=utf-8' -Body $json -ErrorAction Stop
    Write-Host (">> Webhook OK | HTTP " + $req.StatusCode)
    if ($req.Content) { Write-Host (">> Body: " + $req.Content) }
  } catch {
    Write-Warning ("Webhook ERROR: " + $_.Exception.Message)
    if ($_.Exception.Response) {
      try {
        $code = [int]$_.Exception.Response.StatusCode
        Write-Warning ("HTTP status: " + $code)
        $sr = New-Object IO.StreamReader $_.Exception.Response.GetResponseStream()
        $body = $sr.ReadToEnd(); $sr.Dispose()
        Write-Warning ("Body: " + $body)
      } catch {}
    }
  }
}

function Get-PublicIP {
  $urls = @('https://api.ipify.org','https://ifconfig.me/ip','https://ipinfo.io/ip','https://checkip.amazonaws.com')
  foreach ($u in $urls) {
    try {
      $ip = (Invoke-RestMethod -Method Get -Uri $u -TimeoutSec 5 -ErrorAction Stop).ToString().Trim()
      if ($ip -match '^\d{1,3}(\.\d{1,3}){3}$' -or $ip -match '^[0-9a-fA-F:]+$') { return $ip }
    } catch {}
  }
  return "unknown"
}

function Get-UdpListeners {
  $map = @{}
  $out = netstat -ano -p udp 2>$null
  foreach ($line in $out) {
    if ($line -match '^\s*UDP\s+(\S+):(\d+)\s+\S+\s+(\d+)\s*$') {
      $port = [int]$matches[2]
      $procId = [int]$matches[3]
      if (-not $map.ContainsKey($port)) { $map[$port] = @() }
      $map[$port] += $procId
    }
  }
  return $map
}

function Is-VmixOnPort([int]$Port) {
  $listeners = Get-UdpListeners
  if (-not $listeners.ContainsKey($Port)) { return $false }
  foreach ($procId in $listeners[$Port] | Select-Object -Unique) {
    try { 
      $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
      if ($p -and $p.ProcessName -like 'vMix*') { return $true } 
    } catch {}
  }
  return $false
}

Write-Host "=== vMix Port Monitor Script ==="
Write-Host "Using webhook: $Webhook"
Write-Host "Monitoring ports: $($PortArray -join ', ')"
Write-Host "Camera names: $($NameArray -join ', ')"

$wan = Get-PublicIP
Write-Host ("WAN IP: " + $wan)

# Track previous states
$prevStates = @{}
for ($i=0; $i -lt $PortArray.Count; $i++) {
  $prevStates[$PortArray[$i]] = $false
}

# Build initial snapshot message and send at startup
$msgs = @()
for ($i=0; $i -lt $PortArray.Count; $i++) {
  $p = $PortArray[$i]
  $name = $NameArray[$i]
  $on = Is-VmixOnPort $p
  $prevStates[$p] = $on
  $status = if ($on) { "ON" } else { "OFF" }
  $msgs += ("[$Prefix][$name] SRT {0} | IPWAN: {1} | PORT: {2}" -f $status, $wan, $p)
  Write-Host ("$name ($p): $status")
}
$payloadText = $msgs -join "`n"
Send-DiscordStrict $payloadText

$lastWanCheck = Get-Date

# Main monitoring loop
Write-Host "`n=== Starting continuous monitoring (Ctrl+C to stop) ===`n"
while ($true) {
  Start-Sleep -Milliseconds $PollMs
  
  # Check if WAN IP needs refresh
  $now = Get-Date
  if (($now - $lastWanCheck).TotalSeconds -ge $WanRefreshSec) {
    $newWan = Get-PublicIP
    if ($newWan -ne $wan) {
      Write-Host ("WAN IP changed: $wan -> $newWan")
      $wan = $newWan
    }
    $lastWanCheck = $now
  }
  
  # Check each port for state changes
  $changes = @()
  for ($i=0; $i -lt $PortArray.Count; $i++) {
    $p = $PortArray[$i]
    $name = $NameArray[$i]
    $on = Is-VmixOnPort $p
    
    if ($on -ne $prevStates[$p]) {
      $status = if ($on) { "ON" } else { "OFF" }
      $msg = ("[$Prefix][$name] SRT {0} | IPWAN: {1} | PORT: {2}" -f $status, $wan, $p)
      $changes += $msg
      Write-Host ("CHANGE DETECTED: $name ($p) -> $status")
      $prevStates[$p] = $on
    }
  }
  
  # Send changes to Discord
  if ($changes.Count -gt 0) {
    $changePayload = $changes -join "`n"
    Send-DiscordStrict $changePayload
  }
}
