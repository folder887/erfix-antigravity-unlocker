#!/usr/bin/env bash
# ==============================================================================
# erfix v1.0 — Linux Installer
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"

mkdir -p "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

chmod +x "$SCRIPT_DIR/erfix-linux.sh"

# Link CLI executable
ln -sf "$SCRIPT_DIR/erfix-linux.sh" "$BIN_DIR/erfix"

# Copy Icon
if [ -f "$SCRIPT_DIR/Frame 35.png" ]; then
    cp "$SCRIPT_DIR/Frame 35.png" "$ICON_DIR/erfix.png"
fi

# Create .desktop entry
cat > "$DESKTOP_DIR/erfix.desktop" << EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=erfix
GenericName=Antigravity Unlocker
Comment=One-click bypass for Google Antigravity error 400
Exec="$SCRIPT_DIR/erfix-linux.sh"
Icon=erfix
Terminal=false
Categories=Utility;Development;
StartupNotify=false
EOF

chmod +x "$DESKTOP_DIR/erfix.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "====================================================="
echo "✔ erfix успешно установлен в систему Linux!"
echo "• Ярлык добавлен в меню приложений (GNOME/KDE)."
echo "• Консольная команда: erfix [start|stop|status]"
echo "====================================================="
