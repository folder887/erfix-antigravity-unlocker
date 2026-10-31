import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

PROXIES = [
    {"name": "Уфа -> Швеция 2", "proxy": "api-key:jxaq9q2zm82@89.125.28.207:3128"},
    {"name": "Москва 1 -> Швеция 2", "proxy": "m8uabtcdi:kq4po2qyi4@13.143.243.181:3128"},
    {"name": "Америка 1", "proxy": "ag:nova@178.130.47.220:3128"},
    {"name": "Швеция 2 (прямой)", "proxy": "antigravity:nova-agy@2.26.124.30:3128"},
]

def get_ag_unlocker_dir():
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    path = os.path.join(local_appdata, 'AGUnlocker')
    os.makedirs(path, exist_ok=True)
    return path

def get_antigravity_path():
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    candidates = [
        os.path.join(local_appdata, 'Programs', 'Antigravity', 'Antigravity.exe'),
        os.path.join(local_appdata, 'Programs', 'Antigravity IDE', 'Antigravity.exe'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

def test_single_proxy(proxy_item, timeout=4.0):
    proxy_str = proxy_item["proxy"]
    proxy_url = f"http://{proxy_str}"
    t0 = time.time()
    try:
        proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(
            'https://www.google.com',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with opener.open(req, timeout=timeout) as resp:
            latency = int((time.time() - t0) * 1000)
            if resp.status == 200:
                return True, latency, proxy_item
    except Exception as e:
        pass
    latency = int((time.time() - t0) * 1000)
    return False, latency, proxy_item

def find_best_proxy():
    best_item = None
    min_latency = 999999
    
    with ThreadPoolExecutor(max_workers=len(PROXIES)) as executor:
        futures = [executor.submit(test_single_proxy, item) for item in PROXIES]
        for f in as_completed(futures):
            ok, latency, item = f.result()
            if ok and latency < min_latency:
                min_latency = latency
                best_item = item

    if best_item is not None:
        return best_item["proxy"], min_latency, best_item["name"]
    # Fallback to the known working proxy
    return PROXIES[0]["proxy"], 0, PROXIES[0]["name"]

def apply_settings(proxy_str, enable=True):
    unlocker_dir = get_ag_unlocker_dir()
    settings_file = os.path.join(unlocker_dir, 'settings.json')
    upstream_file = os.path.join(unlocker_dir, 'upstream.txt')

    settings = {
        "client_patch": True,
        "auto_patch": True,
        "patch_declined": False,
        "dns": False,
        "local_proxy": True,
        "builtin_exits": True,
        "group_proxy": False,
        "debug_route": "",
        "disabled_providers": [],
        "custom_dns": "",
        "rotate_providers": True,
        "provider_order": [
            "comss.one",
            "geohide.ru",
            "dns-ai.ru"
        ],
        "vpn_detect": True,
        "verify_tls": True,
        "own_proxy": proxy_str,
        "own_proxy_enabled": enable,
        "manual_paths": []
    }

    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                if isinstance(existing, dict):
                    settings.update(existing)
                    settings["own_proxy"] = proxy_str
                    settings["own_proxy_enabled"] = enable
                    settings["group_proxy"] = False
                    settings["dns"] = False
                    settings["local_proxy"] = True
        except Exception:
            pass

    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    with open(upstream_file, 'w', encoding='utf-8') as f:
        f.write(proxy_str.strip())

    return True

def is_service_running():
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq ag_dns.exe", "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        ).decode('cp866', errors='ignore')
        return "ag_dns.exe" in output.lower()
    except Exception:
        return False

def ensure_service_running():
    if is_service_running():
        return True
    
    # Try starting via Scheduled Task
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Start-ScheduledTask -TaskName 'AG Unlocker DNS'"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            timeout=5
        )
        time.sleep(1)
        if is_service_running():
            return True
    except Exception:
        pass

    # Try starting directly from ProgramData if available
    direct_exe = r"C:\ProgramData\AGUnlocker\ag_dns.exe"
    if os.path.exists(direct_exe):
        try:
            subprocess.Popen(
                [direct_exe, "--dns-forwarder"],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
                close_fds=True
            )
            time.sleep(1)
            return is_service_running()
        except Exception:
            pass

    return False

def is_antigravity_running():
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq Antigravity.exe", "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        ).decode('cp866', errors='ignore')
        return "antigravity.exe" in output.lower()
    except Exception:
        return False

def launch_antigravity():
    exe_path = get_antigravity_path()
    if not os.path.exists(exe_path):
        return False, f"Antigravity.exe не найден по пути: {exe_path}"

    try:
        # If running, gracefully kill first
        if is_antigravity_running():
            subprocess.run(
                ["taskkill", "/F", "/IM", "Antigravity.exe", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=5
            )
            time.sleep(1.5)

        # Launch fresh instance
        subprocess.Popen(
            [exe_path],
            cwd=os.path.dirname(exe_path),
            creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
            close_fds=True
        )
        return True, "Antigravity успешно запущен"
    except Exception as e:
        return False, str(e)
