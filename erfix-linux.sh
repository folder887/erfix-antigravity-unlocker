#!/usr/bin/env bash
# ==============================================================================
# erfix v1.0 — Antigravity One-Click Unlocker (Linux edition)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$SCRIPT_DIR"

print_header() {
    echo -e "\033[1;36m=====================================================\033[0m"
    echo -e "\033[1;36m  ⚡ erfix v1.0 — Antigravity One-Click Unlocker (Linux)  \033[0m"
    echo -e "\033[1;36m=====================================================\033[0m"
}

run_cli() {
    print_header
    echo -e "\033[1;33m[1/3] Поиск наименее загруженного и быстрого прокси...\033[0m"
    python3 -c "
import core
proxy_str, latency, name = core.find_best_proxy()
print(f'Выбран сервер: {name} ({latency} ms)')
core.apply_settings(proxy_str, enable=True)
print('[2/3] Конфигурация применена в settings.json и upstream.txt')
core.ensure_service_running()
print('[3/3] Перезапуск Antigravity...')
ok, msg = core.launch_antigravity()
if ok:
    print(f'\033[1;32m✔ Успешно: {msg}!\033[0m')
    print('Сетевой маршрут активен. Ошибка 400 снята.')
else:
    print(f'\033[1;31m✖ Ошибка: {msg}\033[0m')
"
}

stop_proxy() {
    print_header
    echo -e "\033[1;33mОтключение обхода...\033[0m"
    python3 -c "
import core
core.apply_settings('', enable=False)
print('\033[1;32m✔ Обход выключен.\033[0m')
"
}

show_status() {
    print_header
    python3 -c "
import os, json, core
dirs = core.get_ag_unlocker_dirs()
settings_file = os.path.join(dirs[0], 'settings.json')
if os.path.exists(settings_file):
    with open(settings_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        enabled = data.get('own_proxy_enabled', False)
        proxy = data.get('own_proxy', 'None')
        status = '\033[1;32mВКЛЮЧЕНО\033[0m' if enabled else '\033[1;31mВЫКЛЮЧЕНО\033[0m'
        print(f'Статус: {status}')
        print(f'Текущий прокси: {proxy}')
        print(f'Служба ag_dns активна: {core.is_service_running()}')
        print(f'Antigravity запущен: {core.is_antigravity_running()}')
else:
    print('Конфигурация еще не создана. Запустите: ./erfix-linux.sh start')
"
}

CMD="${1:-auto}"

case "$CMD" in
    start|enable)
        run_cli
        ;;
    stop|disable)
        stop_proxy
        ;;
    status)
        show_status
        ;;
    cli)
        run_cli
        ;;
    *)
        # Auto mode: try GUI if DISPLAY/WAYLAND is present and PyQt6 is installed
        if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
            if python3 -c "import PyQt6" 2>/dev/null; then
                exec python3 main.py
            fi
        fi
        # Fallback to CLI
        run_cli
        ;;
esac
