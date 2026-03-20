#!/usr/bin/env bash
# KODA Uninstaller for Linux/macOS

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
INSTALL_DIR="$HOME/.koda"

echo -e "${CYAN}[KODA]${NC} Uninstalling..."

# Remove install dir
[ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR" && echo -e "${GREEN}[OK]${NC} Removed $INSTALL_DIR"

# Remove symlink
[ -L "/usr/local/bin/koda" ] && sudo rm -f "/usr/local/bin/koda" 2>/dev/null && echo -e "${GREEN}[OK]${NC} Removed /usr/local/bin/koda"

# Remove shell aliases
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    [ -f "$rc" ] && sed -i.bak '/# KODA/d; /alias koda=/d' "$rc" 2>/dev/null
done
echo -e "${GREEN}[OK]${NC} Removed shell aliases"

# Remove desktop shortcut (Linux)
rm -f "$HOME/.local/share/applications/koda.desktop" 2>/dev/null
rm -f "${XDG_DESKTOP_DIR:-$HOME/Desktop}/koda.desktop" 2>/dev/null

# Remove macOS app
rm -rf "$HOME/Applications/KODA.app" 2>/dev/null

echo -e "${GREEN}[OK]${NC} KODA uninstalled. Config at ~/.config/koda/ was kept."
