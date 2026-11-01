import os
import sys
import json
import time
import shutil
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

IS_WINDOWS = os.name == 'nt'

def get_ag_unlocker_dirs():
    dirs = []
    if IS_WINDOWS:
        local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        p = os.path.join(local_appdata, 'AGUnlocker')
        os.makedirs(p, exist_ok=True)
        dirs.append(p)
    else:
        home = os.path.expanduser('~')
        xdg_data = os.environ.get('XDG_DATA_HOME', os.path.join(home, '.local', 'share'))
        p1 = os.path.join(xdg_data, 'agunlocker')
        p2 = os.path.join(xdg_data, 'AGUnlocker')
        p3 = os.path.join(home, '.config', 'AGUnlocker')
        for p in [p1, p2, p3]:
            os.makedirs(p, exist_ok=True)
            dirs.append(p)
    return dirs

def get_antigravity_path():
    if IS_WINDOWS:
        local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        candidates = [
            os.path.join(local_appdata, 'Programs', 'Antigravity', 'Antigravity.exe'),
            os.path.join(local_appdata, 'Programs', 'Antigravity IDE', 'Antigravity.exe'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return candidates[0]
    else:
        home = os.path.expanduser('~')
        xdg_data = os.environ.get('XDG_DATA_HOME', os.path.join(home, '.local', 'share'))
        candidates = [
            os.path.join(xdg_data, 'Antigravity', 'antigravity'),
            os.path.join(home, '.local', 'share', 'Antigravity', 'antigravity'),
            '/opt/Antigravity/antigravity',
            '/usr/bin/antigravity',
            '/usr/local/bin/antigravity',
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        # Try finding via PATH
        which_path = shutil.which('antigravity')
        if which_path:
            return which_path
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
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with opener.open(req, timeout=timeout) as resp:
            latency = int((time.time() - t0) * 1000)
            if resp.status == 200:
                return True, latency, proxy_item
    except Exception:
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
    return PROXIES[0]["proxy"], 0, PROXIES[0]["name"]

def apply_settings(proxy_str, enable=True):
    unlocker_dirs = get_ag_unlocker_dirs()

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

    for u_dir in unlocker_dirs:
        settings_file = os.path.join(u_dir, 'settings.json')
        upstream_file = os.path.join(u_dir, 'upstream.txt')

        current = dict(settings)
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    if isinstance(existing, dict):
                        current.update(existing)
                        current["own_proxy"] = proxy_str
                        current["own_proxy_enabled"] = enable
                        current["group_proxy"] = False
                        current["dns"] = False
                        current["local_proxy"] = True
            except Exception:
                pass

        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(current, f, indent=2, ensure_ascii=False)
            with open(upstream_file, 'w', encoding='utf-8') as f:
                f.write(proxy_str.strip())
        except Exception:
            pass

    return True

def is_service_running():
    if IS_WINDOWS:
        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq ag_dns.exe", "/NH"],
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            ).decode('cp866', errors='ignore')
            return "ag_dns.exe" in output.lower()
        except Exception:
            return False
    else:
        try:
            res = subprocess.run(["pgrep", "-f", "ag_dns|ag_unlocker"], stdout=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception:
            return False

def ensure_service_running():
    if is_service_running():
        return True
    
    if IS_WINDOWS:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Start-ScheduledTask -TaskName 'AG Unlocker DNS'"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            time.sleep(1)
            if is_service_running():
                return True
        except Exception:
            pass

        direct_exe = r"C:\ProgramData\AGUnlocker\ag_dns.exe"
        if os.path.exists(direct_exe):
            try:
                subprocess.Popen(
                    [direct_exe, "--dns-forwarder"],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True
                )
                time.sleep(1)
                return is_service_running()
            except Exception:
                pass
    else:
        # Linux service check
        try:
            subprocess.run(["systemctl", "--user", "start", "ag_dns"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            if is_service_running():
                return True
        except Exception:
            pass

        # Try user-local ag_unlocker
        home = os.path.expanduser('~')
        candidates = [
            os.path.join(home, '.local', 'share', 'ag-unlocker', 'ag_unlocker'),
            os.path.join(home, '.local', 'share', 'agunlocker', 'ag_unlocker'),
        ]
        for c in candidates:
            if os.path.exists(c):
                try:
                    subprocess.Popen([c, "--dns-forwarder"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                    time.sleep(1)
                    return is_service_running()
                except Exception:
                    pass

    return False

def is_antigravity_running():
    if IS_WINDOWS:
        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq Antigravity.exe", "/NH"],
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            ).decode('cp866', errors='ignore')
            return "antigravity.exe" in output.lower()
        except Exception:
            return False
    else:
        try:
            res = subprocess.run(["pgrep", "-f", "antigravity|Antigravity"], stdout=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception:
            return False

def launch_antigravity():
    exe_path = get_antigravity_path()

    try:
        if is_antigravity_running():
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "Antigravity.exe", "/T"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5
                )
            else:
                subprocess.run(["pkill", "-9", "-f", "antigravity"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-9", "-f", "Antigravity"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)

        if not os.path.exists(exe_path):
            if not IS_WINDOWS:
                # Try running plain command
                subprocess.Popen(["antigravity"], start_new_session=True)
                return True, "Команда antigravity вызвана"
            return False, f"Antigravity.exe не найден по пути: {exe_path}"

        if IS_WINDOWS:
            subprocess.Popen(
                [exe_path],
                cwd=os.path.dirname(exe_path),
                creationflags=subprocess.DETACHED_PROCESS,
                close_fds=True
            )
        else:
            subprocess.Popen(
                [exe_path],
                cwd=os.path.dirname(exe_path),
                start_new_session=True,
                close_fds=True
            )
        return True, "Antigravity успешно запущен"
    except Exception as e:
        return False, str(e)
