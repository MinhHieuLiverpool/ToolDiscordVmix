"""
Toolkit Actions - Module xử lý các lệnh PowerShell, CMD, WMI, Registry quản trị Windows.
"""
import os
import sys
import ctypes
import socket
import subprocess
import getpass
from typing import Tuple, List, Dict


def is_admin() -> bool:
    """Kiểm tra quyền Administrator của tiến trình hiện tại."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin_elevation():
    """Khởi động lại script với quyền Administrator (UAC Prompt)."""
    if is_admin():
        return True
    try:
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        if ret > 32:
            sys.exit(0)
        return False
    except Exception as e:
        print(f"Lỗi khi yêu cầu quyền Admin: {e}")
        return False


def run_command_ps(ps_command: str, timeout: int = 35) -> Tuple[bool, str]:
    """Thực thi lệnh PowerShell với UTF-8 và quyền Admin."""
    utf8_header = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
        "$OutputEncoding = [System.Text.Encoding]::UTF8;\n"
    )
    full_cmd = utf8_header + ps_command
    try:
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", full_cmd
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        success = (proc.returncode == 0)
        
        output = out
        if err:
            output = f"{out}\n[Errors/Warnings]:\n{err}" if out else err
        return success, output if output else ("✓ Hoàn thành (Không có output)" if success else "❌ Lỗi thực thi")
    except subprocess.TimeoutExpired:
        return False, f"⏱️ Timeout ({timeout}s) khi thực thi PowerShell command!"
    except Exception as e:
        return False, f"❌ Lỗi Exception: {str(e)}"


def run_command_cmd(cmd_command: str, timeout: int = 30) -> Tuple[bool, str]:
    """Thực thi lệnh CMD/Batch với UTF-8 (chcp 65001)."""
    try:
        full_cmd = f"chcp 65001 >nul & {cmd_command}"
        proc = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        success = (proc.returncode == 0)
        
        output = out
        if err:
            output = f"{out}\n[Errors/Warnings]:\n{err}" if out else err
        return success, output if output else ("✓ Hoàn thành" if success else "❌ Lỗi thực thi")
    except subprocess.TimeoutExpired:
        return False, f"⏱️ Timeout ({timeout}s) khi thực thi CMD command!"
    except Exception as e:
        return False, f"❌ Lỗi Exception: {str(e)}"


# ── 1. Windows Update (Bật / Tắt) ──────────────────────────────────────────

def disable_windows_update() -> Tuple[bool, str]:
    """
    Tắt hoàn toàn và triệt để Windows Update:
    - Set Registry Services (Start=4: Disabled) cho wuauserv, WaaSMedicSvc, UsoSvc, bits
    - Dừng tiến trình và vô hiệu hóa qua sc.exe / Stop-Service
    - Thiết lập Group Policy Registry chặn tự động quét/tải update
    - Vô hiệu hóa Scheduled Tasks của Windows Update
    """
    ps_script = """
    Write-Host "1. Đang vô hiệu hóa Services Windows Update qua Kernel Registry (Start=4)..."
    $svcs = @("wuauserv", "WaaSMedicSvc", "UsoSvc", "bits")
    foreach ($s in $svcs) {
        try {
            $regKey = "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\$s"
            if (Test-Path $regKey) {
                Set-ItemProperty -Path $regKey -Name "Start" -Value 4 -Type DWord -Force -ErrorAction SilentlyContinue
                Write-Host ("   - [Registry Service] Đã khóa Start=4 (Disabled) cho: " + $s)
            }
        } catch {}
    }

    Write-Host "2. Đang dừng và vô hiệu hóa tiến trình chạy nền..."
    foreach ($s in $svcs) {
        try {
            Stop-Service -Name $s -Force -ErrorAction SilentlyContinue
            sc.exe config $s start=disabled | Out-Null
            sc.exe stop $s | Out-Null
            Write-Host ("   - [Service Control] Đã dừng và Disable: " + $s)
        } catch {}
    }

    Write-Host "3. Đang cấu hình Group Policy Registry chặn Windows Update..."
    try {
        $regPath = "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate"
        $auPath = "$regPath\\AU"
        if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force -ErrorAction SilentlyContinue | Out-Null }
        if (-not (Test-Path $auPath)) { New-Item -Path $auPath -Force -ErrorAction SilentlyContinue | Out-Null }

        Set-ItemProperty -Path $auPath -Name "NoAutoUpdate" -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $auPath -Name "AUOptions" -Value 2 -Type DWord -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $regPath -Name "DisableWindowsUpdateAccess" -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue
        Write-Host "   - Đã cấu hình NoAutoUpdate=1, AUOptions=2, DisableWindowsUpdateAccess=1"
    } catch {}

    Write-Host "4. Đang vô hiệu hóa Scheduled Tasks liên quan tới Update..."
    try {
        Get-ScheduledTask -TaskPath "\\Microsoft\\Windows\\WindowsUpdate\\*" -ErrorAction SilentlyContinue | Disable-ScheduledTask -ErrorAction SilentlyContinue | Out-Null
        Get-ScheduledTask -TaskPath "\\Microsoft\\Windows\\UpdateOrchestrator\\*" -ErrorAction SilentlyContinue | Disable-ScheduledTask -ErrorAction SilentlyContinue | Out-Null
        Write-Host "   - Đã Disable các Task tự động đánh thức Update trong Task Scheduler"
    } catch {}

    Write-Host ""
    Write-Host "✅ ĐÃ TẮT TRIỆT ĐỂ WINDOWS UPDATE THÀNH CÔNG!"
    Write-Host "👉 Dịch vụ wuauserv đã được chuyển sang chế độ Disabled (Tắt hoàn toàn)."
    """
    return run_command_ps(ps_script)


def enable_windows_update() -> Tuple[bool, str]:
    """
    Bật lại Windows Update:
    - Set Registry Services (Start=3: Demand / Manual) cho wuauserv, WaaSMedicSvc, UsoSvc, bits
    - Kích hoạt lại qua sc.exe và Start-Service
    - Xóa các khóa Group Policy Registry chặn Update
    - Kích hoạt lại Scheduled Tasks
    """
    ps_script = """
    Write-Host "1. Đang khôi phục Services Windows Update qua Kernel Registry (Start=3)..."
    $svcs = @("wuauserv", "WaaSMedicSvc", "UsoSvc", "bits")
    foreach ($s in $svcs) {
        try {
            $regKey = "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\$s"
            if (Test-Path $regKey) {
                Set-ItemProperty -Path $regKey -Name "Start" -Value 3 -Type DWord -Force -ErrorAction SilentlyContinue
                Write-Host ("   - [Registry Service] Đã mở lại Start=3 (Manual) cho: " + $s)
            }
        } catch {}
    }

    Write-Host "2. Đang kích hoạt lại dịch vụ..."
    foreach ($s in $svcs) {
        try {
            sc.exe config $s start=demand | Out-Null
            Set-Service -Name $s -StartupType Manual -ErrorAction SilentlyContinue
            Write-Host ("   - [Service Control] Đã Enable: " + $s)
        } catch {}
    }
    Start-Service -Name "wuauserv" -ErrorAction SilentlyContinue
    Start-Service -Name "bits" -ErrorAction SilentlyContinue

    Write-Host "3. Đang xóa cấu hình Group Policy chặn Update..."
    try {
        $regPath = "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate"
        $auPath = "$regPath\\AU"
        if (Test-Path $auPath) {
            Remove-ItemProperty -Path $auPath -Name "NoAutoUpdate" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $auPath -Name "AUOptions" -ErrorAction SilentlyContinue
        }
        if (Test-Path $regPath) {
            Remove-ItemProperty -Path $regPath -Name "DisableWindowsUpdateAccess" -ErrorAction SilentlyContinue
        }
        Write-Host "   - Đã gỡ bỏ các khóa chặn Registry"
    } catch {}

    Write-Host "4. Đang kích hoạt lại Scheduled Tasks..."
    try {
        Get-ScheduledTask -TaskPath "\\Microsoft\\Windows\\WindowsUpdate\\*" -ErrorAction SilentlyContinue | Enable-ScheduledTask -ErrorAction SilentlyContinue | Out-Null
        Get-ScheduledTask -TaskPath "\\Microsoft\\Windows\\UpdateOrchestrator\\*" -ErrorAction SilentlyContinue | Enable-ScheduledTask -ErrorAction SilentlyContinue | Out-Null
        Write-Host "   - Đã mở lại các Task trong Task Scheduler"
    } catch {}

    Write-Host ""
    Write-Host "✅ ĐÃ BẬT LẠI WINDOWS UPDATE THÀNH CÔNG!"
    """
    return run_command_ps(ps_script)


# ── 2. Đổi Mật Khẩu User Windows ───────────────────────────────────────────

def get_local_users() -> List[str]:
    """Lấy danh sách các tài khoản người dùng cục bộ trên máy."""
    users = []
    try:
        success, out = run_command_ps("Get-LocalUser | Select-Object -ExpandProperty Name")
        if success and out:
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            for l in lines:
                if l and not l.startswith("["):
                    users.append(l)
    except Exception:
        pass
    
    if not users:
        curr = getpass.getuser()
        users = [curr, "Administrator"]
    return sorted(list(set(users)))


def change_user_password(username: str, new_password: str) -> Tuple[bool, str]:
    """
    Đổi mật khẩu tài khoản người dùng:
    - Nếu new_password rỗng (""): Đổi mật khẩu thành rỗng (không cần mật khẩu đăng nhập).
    - Nếu có new_password: Đổi sang mật khẩu mới.
    """
    if not username:
        username = getpass.getuser()

    username_clean = username.strip().replace('"', '')
    
    if not new_password:
        # Mật khẩu rỗng
        cmd = f'net user "{username_clean}" ""'
        action_desc = "MẬT KHẨU RỖNG (Không mật khẩu)"
    else:
        # Mật khẩu có giá trị
        cmd = f'net user "{username_clean}" "{new_password}"'
        action_desc = f"MẬT KHẨU MỚI: [{new_password}]"

    success, out = run_command_cmd(cmd)
    if success:
        return True, f"✅ Đã đổi thành công {action_desc} cho User: [{username_clean}]!\n{out}"
    else:
        return False, f"❌ Đổi mật khẩu thất bại cho User: [{username_clean}]!\n{out}\n(Lưu ý: Cần chạy tool với quyền Administrator)"


# ── 3. Rename Device (Đổi Tên Máy Tính) ──────────────────────────────────────

def get_current_device_name() -> str:
    """Lấy tên máy tính hiện tại."""
    try:
        return socket.gethostname()
    except Exception:
        return os.environ.get("COMPUTERNAME", "Unknown")


def rename_device(new_name: str) -> Tuple[bool, str]:
    """
    Đổi tên máy tính (Computer Name).
    Yêu cầu khởi động lại máy để áp dụng.
    """
    new_name = new_name.strip()
    if not new_name:
        return False, "❌ Tên máy tính mới không được để trống!"
    
    # Kiểm tra ký tự hợp lệ cho tên máy Windows (Tối đa 15 ký tự, chữ, số, dấu gạch ngang)
    import re
    if not re.match(r'^[a-zA-Z0-9\-]{1,15}$', new_name):
        return False, "❌ Tên máy tính không hợp lệ! (Chỉ dùng chữ, số, dấu gạch ngang '-', tối đa 15 ký tự)"

    current_name = get_current_device_name()
    if current_name.upper() == new_name.upper():
        return False, f"⚠️ Tên mới trùng với tên máy tính hiện tại: [{current_name}]"

    ps_script = f"""
    try {{
        Rename-Computer -NewName "{new_name}" -Force -ErrorAction Stop
        Write-Host "✅ Đã đổi tên máy thành công từ [{current_name}] sang [{new_name}]!"
        Write-Host "💡 Lưu ý: Vui lòng khởi động lại máy tính (Restart PC) để tên mới có hiệu lực."
    }} catch {{
        Write-Host "❌ Lỗi đổi tên máy: $_"
        exit 1
    }}
    """
    return run_command_ps(ps_script)


# ── 4. Tắt chặn Share File Win 11 (SMB Sharing / Guest Access) ─────────────

def unblock_smb_file_sharing_win11() -> Tuple[bool, str]:
    """
    Tắt chặn share file trên Windows 11 bằng Administrator PowerShell:
    - Set-SmbClientConfiguration -EnableInsecureGuestLogons $true -Force
    - Set-SmbClientConfiguration -RequireSecuritySignature $false -Force
    - Set-SmbServerConfiguration -RequireSecuritySignature $false -Force
    - Bật tường lửa File and Printer Sharing & Network Discovery
    - Bật dịch vụ chia sẻ mạng LanmanServer / Function Discovery
    """
    ps_script = """
    Write-Host "1. Đang cấu hình SMB Client & SMB Server (Win 11 Guest & Signature Fix)..."
    Set-SmbClientConfiguration -EnableInsecureGuestLogons $true -Force -ErrorAction SilentlyContinue
    Set-SmbClientConfiguration -RequireSecuritySignature $false -Force -ErrorAction SilentlyContinue
    Set-SmbServerConfiguration -RequireSecuritySignature $false -Force -ErrorAction SilentlyContinue
    Set-SmbServerConfiguration -EnableSMB2Protocol $true -Force -ErrorAction SilentlyContinue

    Write-Host "2. Đang kích hoạt tường lửa (Firewall) cho File Sharing & Network Discovery..."
    Enable-NetFirewallRule -DisplayGroup "File and Printer Sharing" -ErrorAction SilentlyContinue
    Enable-NetFirewallRule -DisplayGroup "Network Discovery" -ErrorAction SilentlyContinue

    Write-Host "3. Đang khởi động các dịch vụ mạng liên quan..."
    $net_svcs = @("LanmanServer", "LanmanWorkstation", "FDResPub", "fdPHost", "SSDPSRV")
    foreach ($s in $net_svcs) {
        Set-Service -Name $s -StartupType Automatic -ErrorAction SilentlyContinue
        Start-Service -Name $s -ErrorAction SilentlyContinue
    }

    Write-Host "4. Cấu hình Registry cho phép Guest Access..."
    Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\LanmanWorkstation\\Parameters" -Name "AllowInsecureGuestAuth" -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue

    Write-Host "✅ ĐÃ TẮT CHẶN SHARE FILE WIN 11 THÀNH CÔNG!"
    Write-Host "👉 Bây giờ các máy trong mạng LAN có thể truy cập Share File mượt mà, không bị lỗi 0x80070035 / Access Denied."
    """
    return run_command_ps(ps_script)


# ── 5. Cấu Hình Mạng (IP Động / IP Tĩnh / DNS) ──────────────────────────────

def get_active_network_adapters() -> List[str]:
    """Lấy danh sách các card mạng đang kết nối."""
    adapters = []
    ps_cmd = "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -ExpandProperty Name"
    success, out = run_command_ps(ps_cmd)
    if success and out:
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        for l in lines:
            if not l.startswith("["):
                adapters.append(l)
    if not adapters:
        adapters = ["Ethernet", "Wi-Fi"]
    return sorted(list(set(adapters)))


def get_adapter_ip_details(adapter_name: str = None) -> Dict[str, any]:
    """Lấy thông tin cấu hình IP hiện tại của card mạng."""
    target = f'-Name "{adapter_name}"' if adapter_name and adapter_name != "Tất cả Card Mạng (All)" else "| Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1"
    
    ps_script = """
    $targetAdapter = Get-NetAdapter __TARGET__ -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $targetAdapter) {
        $targetAdapter = Get-NetAdapter | Select-Object -First 1
    }
    if ($targetAdapter) {
        $ip_info = Get-NetIPAddress -InterfaceIndex $targetAdapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -First 1
        $gw_info = Get-NetRoute -InterfaceIndex $targetAdapter.ifIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Select-Object -First 1
        $dns_info = Get-DnsClientServerAddress -InterfaceIndex $targetAdapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
        $ip_interface = Get-NetIPInterface -InterfaceIndex $targetAdapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue

        $mask = "255.255.255.0"
        if ($ip_info -and $ip_info.PrefixLength) {
            $p = [int]$ip_info.PrefixLength
            $bin = ('1' * $p).PadRight(32, '0')
            $bytes = @()
            for ($i = 0; $i -lt 32; $i += 8) {
                $bytes += [Convert]::ToByte($bin.Substring($i, 8), 2)
            }
            $mask = $bytes -join '.'
        }

        $dns_list = @()
        if ($dns_info -and $dns_info.ServerAddresses) {
            $dns_list = $dns_info.ServerAddresses
        }

        [PSCustomObject]@{
            AdapterName = $targetAdapter.Name
            Status = $targetAdapter.Status
            MacAddress = $targetAdapter.MacAddress
            LinkSpeed = $targetAdapter.LinkSpeed
            Dhcp = if ($ip_interface -and $ip_interface.Dhcp -eq 1) { "Enabled" } else { "Disabled" }
            IPAddress = if ($ip_info) { $ip_info.IPAddress } else { "" }
            SubnetMask = $mask
            PrefixLength = if ($ip_info) { $ip_info.PrefixLength } else { 24 }
            Gateway = if ($gw_info) { $gw_info.NextHop } else { "" }
            DNS1 = if ($dns_list.Count -gt 0) { $dns_list[0] } else { "" }
            DNS2 = if ($dns_list.Count -gt 1) { $dns_list[1] } else { "" }
        } | ConvertTo-Json
    }
    """.replace("__TARGET__", target)
    
    success, out = run_command_ps(ps_script)
    if success and out:
        import json
        try:
            return json.loads(out)
        except Exception:
            pass
    return {}


def set_static_ip(
    adapter_name: str,
    ip_address: str,
    subnet_mask: str,
    default_gateway: str,
    dns1: str = "",
    dns2: str = ""
) -> Tuple[bool, str]:
    """
    Cấu hình IP Tĩnh (Static IP), Subnet Mask, Default Gateway và DNS cho card mạng.
    """
    if not adapter_name or adapter_name == "Tất cả Card Mạng (All)":
        return False, "❌ Vui lòng chọn một Card Mạng cụ thể (không chọn Tất cả) để đặt IP Tĩnh!"

    ip_address = ip_address.strip()
    subnet_mask = subnet_mask.strip() or "255.255.255.0"
    default_gateway = default_gateway.strip()
    dns1 = dns1.strip()
    dns2 = dns2.strip()

    if not ip_address:
        return False, "❌ Địa chỉ IP không được để trống!"

    cmds = []
    if default_gateway:
        cmds.append(f'netsh interface ip set address name="{adapter_name}" static {ip_address} {subnet_mask} {default_gateway} 1')
    else:
        cmds.append(f'netsh interface ip set address name="{adapter_name}" static {ip_address} {subnet_mask}')

    if dns1:
        cmds.append(f'netsh interface ip set dns name="{adapter_name}" static {dns1}')
        if dns2:
            cmds.append(f'netsh interface ip add dns name="{adapter_name}" {dns2} index=2')
    else:
        cmds.append(f'netsh interface ip set dns name="{adapter_name}" source=dhcp')

    full_batch = " & ".join(cmds)
    success, out = run_command_cmd(full_batch)
    if success:
        return True, (
            f"✅ ĐÃ CẤU HÌNH IP TĨNH THÀNH CÔNG CHO [{adapter_name}]!\n"
            f"• IP Address: {ip_address}\n"
            f"• Subnet Mask: {subnet_mask}\n"
            f"• Gateway: {default_gateway or 'None'}\n"
            f"• Primary DNS: {dns1 or 'None'}\n"
            f"• Alternate DNS: {dns2 or 'None'}"
        )
    else:
        return False, f"❌ Lỗi khi cấu hình IP Tĩnh:\n{out}"


def set_network_dhcp(adapter_name: str = None) -> Tuple[bool, str]:
    """
    Cấu hình card mạng sang chế độ IP động (DHCP) và DNS tự động.
    Nếu adapter_name=None -> Áp dụng cho tất cả card mạng đang Up.
    """
    if adapter_name and adapter_name != "Tất cả Card Mạng (All)":
        ps_script = f"""
        Write-Host "Đang cấu hình DHCP cho card mạng: [{adapter_name}]..."
        $adapter = Get-NetAdapter -Name "{adapter_name}" -ErrorAction SilentlyContinue
        if ($adapter) {{
            Set-NetIPInterface -InterfaceIndex $adapter.ifIndex -Dhcp Enabled -ErrorAction SilentlyContinue
            Set-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -ResetServerAddresses -ErrorAction SilentlyContinue
            netsh interface ip set address name="{adapter_name}" source=dhcp | Out-Null
            netsh interface ip set dns name="{adapter_name}" source=dhcp | Out-Null
            Write-Host "✅ Đã chuyển [{adapter_name}] sang IP Động (DHCP) & DNS Động!"
        }} else {{
            Write-Host "❌ Không tìm thấy card mạng: [{adapter_name}]"
            exit 1
        }}
        """
    else:
        ps_script = """
        Write-Host "Đang chuyển TẤT CẢ card mạng đang hoạt động sang IP Động (DHCP)..."
        $adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }
        foreach ($ad in $adapters) {
            Write-Host "   - Đang cấu hình: $($ad.Name)"
            Set-NetIPInterface -InterfaceIndex $ad.ifIndex -Dhcp Enabled -ErrorAction SilentlyContinue
            Set-DnsClientServerAddress -InterfaceIndex $ad.ifIndex -ResetServerAddresses -ErrorAction SilentlyContinue
            netsh interface ip set address name="$($ad.Name)" source=dhcp | Out-Null
            netsh interface ip set dns name="$($ad.Name)" source=dhcp | Out-Null
        }
        Write-Host "✅ ĐÃ CHUYỂN TOÀN BỘ CARD MẠNG SANG IP ĐỘNG (DHCP) THÀNH CÔNG!"
        """
    return run_command_ps(ps_script)


# ── 6. Quản Lý Nguồn Điện & Power Plan (Chi Tiết Từng Mục) ─────────────────

def get_power_schemes() -> List[Dict[str, any]]:
    """Lấy danh sách tất cả các Power Scheme trong Windows và xác định scheme đang Active."""
    schemes = []
    success, out = run_command_cmd("powercfg /list")
    if success and out:
        import re
        for line in out.splitlines():
            match = re.search(r'Power Scheme GUID:\s+([a-fA-F0-9\-]+)\s+\((.*?)\)(\s*\*|\s*$)', line)
            if match:
                guid = match.group(1).strip()
                name = match.group(2).strip()
                is_active = "*" in match.group(3) or "*" in line
                schemes.append({
                    "guid": guid,
                    "name": name,
                    "is_active": is_active
                })
    if not schemes:
        schemes = [
            {"guid": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "name": "High performance", "is_active": True},
            {"guid": "381b4222-f694-41f0-9685-ff5bb260df2e", "name": "Balanced", "is_active": False}
        ]
    return schemes


def unlock_ultimate_performance() -> Tuple[bool, str]:
    """Mở khóa gói Ultimate Performance (Hiệu năng tối thượng) ẩn trên Windows 10/11."""
    cmd = "powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61"
    success, out = run_command_cmd(cmd)
    if success:
        return True, "✅ Đã mở khóa thành công Power Plan: [Ultimate Performance]!\n" + out
    return False, "❌ Không thể mở khóa Ultimate Performance:\n" + out


def save_power_plan_settings(
    scheme_guid: str,
    monitor_ac: int,
    monitor_dc: int,
    sleep_ac: int,
    sleep_dc: int,
    disk_ac: int,
    disk_dc: int,
    hibernate_enabled: bool,
) -> Tuple[bool, str]:
    """
    Lưu và áp dụng toàn bộ cài đặt Power Options riêng lẻ:
    - Kích hoạt Power Scheme được chọn
    - Thiết lập thời gian tắt màn hình (AC/DC)
    - Thiết lập thời gian sleep (AC/DC)
    - Thiết lập thời gian tắt ổ cứng (AC/DC)
    - Bật/Tắt chế độ ngủ đông (Hibernate)
    """
    cmds = []
    if scheme_guid:
        cmds.append(f"powercfg -setactive {scheme_guid}")
    
    cmds.append(f"powercfg -change -monitor-timeout-ac {monitor_ac}")
    cmds.append(f"powercfg -change -monitor-timeout-dc {monitor_dc}")
    cmds.append(f"powercfg -change -standby-timeout-ac {sleep_ac}")
    cmds.append(f"powercfg -change -standby-timeout-dc {sleep_dc}")
    cmds.append(f"powercfg -change -disk-timeout-ac {disk_ac}")
    cmds.append(f"powercfg -change -disk-timeout-dc {disk_dc}")

    if hibernate_enabled:
        cmds.append("powercfg -hibernate on")
    else:
        cmds.append("powercfg -hibernate off")

    full_batch = " & ".join(cmds)
    success, out = run_command_cmd(full_batch)
    if success:
        def _fmt(val):
            return "Không bao giờ (Never)" if val == 0 else f"{val} phút"

        msg = (
            "✅ ĐÃ LƯU & CẬP NHẬT CẤU HÌNH POWER PLAN THÀNH CÔNG!\n"
            f"• Scheme Active: {scheme_guid}\n"
            f"• Tắt màn hình (AC): {_fmt(monitor_ac)} | (DC Pin): {_fmt(monitor_dc)}\n"
            f"• Chế độ Sleep (AC): {_fmt(sleep_ac)} | (DC Pin): {_fmt(sleep_dc)}\n"
            f"• Tắt ổ cứng (AC/DC): {_fmt(disk_ac)} / {_fmt(disk_dc)}\n"
            f"• Ngủ đông (Hibernate): {'BẬT (Enabled)' if hibernate_enabled else 'TẮT (Disabled)'}"
        )
        return True, msg
    else:
        return False, f"❌ Lỗi áp dụng cấu hình Power Plan:\n{out}"


def disable_windows_power_sleep() -> Tuple[bool, str]:
    """Preset nhanh: Tắt hoàn toàn Sleep & Tiết kiệm điện cho máy Live vMix."""
    return save_power_plan_settings(
        scheme_guid="8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        monitor_ac=0,
        monitor_dc=0,
        sleep_ac=0,
        sleep_dc=0,
        disk_ac=0,
        disk_dc=0,
        hibernate_enabled=False
    )


# ── 7. Tiện ích Phụ Trợ (Restart Explorer / Restart PC) ──────────────────────

def restart_windows_explorer() -> Tuple[bool, str]:
    """Khởi động lại Windows Explorer (Taskbar & Desktop)."""
    cmd = "taskkill /f /im explorer.exe & start explorer.exe"
    return run_command_cmd(cmd)


def restart_computer() -> Tuple[bool, str]:
    """Khởi động lại máy tính sau 5 giây."""
    return run_command_cmd("shutdown /r /t 5 /c \"Khoi dong lai theo yeu cau cua Admin Toolkit\"")


# ── 8. Quét Cấu Hình Máy (Hardware Specs CPU-Z) ───────────────────────────

def get_hardware_specs() -> Dict[str, any]:
    """
    Quét chi tiết toàn bộ phần cứng máy tính (tương tự CPU-Z):
    - CPU, Mainboard, BIOS, RAM Sticks, GPU, Ổ cứng / Disks, Windows OS.
    """
    ps_script = """
    $cpu = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, L2CacheSize, L3CacheSize, SocketDesignation | Select-Object -First 1
    $board = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, SerialNumber | Select-Object -First 1
    $bios = Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, @{N='ReleaseDate';E={($_.ReleaseDate).ToString('yyyy-MM-dd')}} | Select-Object -First 1
    $ram = @(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity, Speed, Manufacturer, PartNumber, BankLabel, DeviceLocator)
    $gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM, VideoModeDescription, CurrentRefreshRate)
    $disks = @(Get-CimInstance Win32_DiskDrive | Select-Object Model, Size, MediaType, InterfaceType)
    $os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, @{N='InstallDate';E={($_.InstallDate).ToString('yyyy-MM-dd HH:mm')}} | Select-Object -First 1

    [PSCustomObject]@{
        CPU = $cpu
        Motherboard = $board
        BIOS = $bios
        RAM = $ram
        GPU = $gpu
        Disks = $disks
        OS = $os
    } | ConvertTo-Json -Depth 4
    """
    success, out = run_command_ps(ps_script, timeout=40)
    if success and out:
        import json
        try:
            return json.loads(out)
        except Exception as e:
            print(f"Error parsing hardware json: {e}")
    return {}


# ── 9. Quản Lý & Kiểm Tra Driver (Chưa Cài Đặt, Chưa Update, Lỗi) ──────────

def scan_driver_problems_and_status() -> Dict[str, any]:
    """
    Quét toàn bộ thiết bị trong Device Manager:
    - Tìm các thiết bị chưa cài đặt driver (Thiếu Driver / Code 28)
    - Tìm các thiết bị báo lỗi (Code 10, 43, 31, 39...) hoặc bị Disable (Code 22)
    - Danh sách các driver phần cứng chính (Display, Network, Audio, Storage, Bluetooth, Chipset...)
    """
    ps_script = """
    $errorMap = @{
        1  = 'Chưa được cấu hình đúng (Not configured)';
        10 = 'Thiết bị không thể khởi động (Device cannot start)';
        14 = 'Cần khởi động lại máy tính (Restart required)';
        18 = 'Cần cài đặt lại driver cho thiết bị này (Reinstall driver)';
        22 = 'Thiết bị đang bị tắt / Vô hiệu hóa (Disabled)';
        28 = 'Chưa cài đặt driver (Thiếu Driver / Unknown Device) ⚠️';
        31 = 'Thiết bị không hoạt động đúng do lỗi nạp driver';
        39 = 'Windows không thể tải driver này';
        43 = 'Windows đã dừng thiết bị do phát sinh lỗi phần cứng/driver'
    }

    $problems = @()
    $devices = Get-CimInstance Win32_PnPEntity | Where-Object { $_.ConfigManagerErrorCode -ne 0 -or $_.Status -ne 'OK' }
    foreach ($d in $devices) {
        $code = [int]$d.ConfigManagerErrorCode
        $desc = if ($errorMap.ContainsKey($code)) { $errorMap[$code] } else { ('Mã lỗi ' + $code) }
        $problems += [PSCustomObject]@{
            Name = $d.Name
            DeviceID = $d.DeviceID
            Class = $d.PNPClass
            Manufacturer = $d.Manufacturer
            ErrorCode = $code
            ErrorMeaning = $desc
            Status = $d.Status
        }
    }

    $mainDrivers = @()
    $cats = @('Display', 'Net', 'MEDIA', 'SCSIAdapter', 'Bluetooth', 'System', 'USB', 'Keyboard', 'Mouse')
    foreach ($c in $cats) {
        $drvs = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceClass -eq $c -and $_.DeviceName -ne $null } | Select-Object -First 10
        foreach ($dr in $drvs) {
            $mainDrivers += [PSCustomObject]@{
                Name = $dr.DeviceName
                Class = $dr.DeviceClass
                DriverVersion = $dr.DriverVersion
                DriverDate = if ($dr.DriverDate) { ($dr.DriverDate).ToString('yyyy-MM-dd') } else { 'N/A' }
                Manufacturer = $dr.Manufacturer
                Signer = $dr.Signer
            }
        }
    }

    [PSCustomObject]@{
        ProblemCount = $problems.Count
        Problems = $problems
        InstalledCount = $mainDrivers.Count
        Installed = $mainDrivers
    } | ConvertTo-Json -Depth 4
    """
    success, out = run_command_ps(ps_script, timeout=40)
    if success and out:
        import json
        try:
            return json.loads(out)
        except Exception as e:
            print(f"Error parsing driver json: {e}")
    return {}


def check_driver_updates_online() -> Tuple[bool, str]:
    """Kiểm tra các bản cập nhật Driver mới có sẵn từ Windows Update Catalog."""
    ps_script = """
    Write-Host "🔍 Đang kết nối tới Windows Update Catalog để kiểm tra bản cập nhật Driver..."
    try {
        $session = New-Object -ComObject Microsoft.Update.Session
        $searcher = $session.CreateUpdateSearcher()
        $searcher.ServerSelection = 2
        $result = $searcher.Search("IsInstalled=0 and Type='Driver'")
        $count = $result.Updates.Count
        if ($count -eq 0) {
            Write-Host "✅ TẤT CẢ DRIVER ĐÃ ĐƯỢC CẬP NHẬT MỚI NHẤT!"
            Write-Host "• Không tìm thấy bản cập nhật driver nào chưa cài đặt từ Microsoft."
        } else {
            Write-Host "⚠️ TÌM THẤY $count BẢN CẬP NHẬT DRIVER MỚI CHƯA CÀI ĐẶT:"
            foreach ($u in $result.Updates) {
                Write-Host ("   └─ [Update] " + $u.Title)
            }
            Write-Host ""
            Write-Host "💡 Gợi ý: Bạn có thể bật lại Windows Update trong tab 'Windows Update' để tự động tải các driver này."
        }
    } catch {
        Write-Host "⚠️ Không thể truy vấn Windows Update Catalog: $($_.Exception.Message)"
    }
    """
    return run_command_ps(ps_script, timeout=60)


def rescan_hardware_devices() -> Tuple[bool, str]:
    """Quét lại phần cứng (Scan for hardware changes / PnP Re-scan)."""
    return run_command_cmd("pnputil /scan-devices")


def open_device_manager() -> Tuple[bool, str]:
    """Mở trình quản lý thiết bị Windows Device Manager."""
    return run_command_cmd("start devmgmt.msc")

