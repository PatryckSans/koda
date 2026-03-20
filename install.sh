#!/usr/bin/env bash
set -e

# KODA - Kiro Operator Dashboard Application
# Installer for Linux and macOS

REPO_URL="https://github.com/patrycksans/koda/archive/refs/heads/main.tar.gz"
INSTALL_DIR="$HOME/.koda"
VENV_DIR="$INSTALL_DIR/venv"
BIN_LINK="/usr/local/bin/koda"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${CYAN}[KODA]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}"
echo "  █▄▀  █▀█  █▀▄  ▄▀█"
echo "  █░█  █▄█  █▄▀  █▀█"
echo "  Kiro Operator Dashboard Application"
echo -e "${NC}"
echo ""

# --- Detect OS ---
OS="$(uname -s)"
case "$OS" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    MINGW*|MSYS*|CYGWIN*) fail "Windows detected. Use install.ps1 instead:\n  irm https://raw.githubusercontent.com/patrycksans/koda/main/install.ps1 | iex" ;;
    *) fail "Unsupported OS: $OS" ;;
esac
ok "Platform: $PLATFORM"

# --- Check Python 3.8+ ---
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done
[ -z "$PYTHON" ] && fail "Python 3.8+ is required. Install it first:\n  Linux: sudo apt install python3 python3-venv python3-pip\n  macOS: brew install python3"
ok "Python: $($PYTHON --version)"

# --- Check pip/venv ---
$PYTHON -c "import venv" 2>/dev/null || fail "Python venv module not found.\n  Linux: sudo apt install python3-venv\n  macOS: brew install python3"

# --- Check kiro-cli ---
if command -v kiro-cli &>/dev/null; then
    ok "kiro-cli: $(kiro-cli --version 2>/dev/null || echo 'installed')"
else
    warn "kiro-cli is NOT installed. KODA requires kiro-cli to function."
    warn "Install it from: https://kiro.dev/docs/cli/install/"
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo ""
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# --- Remove previous installation ---
if [ -d "$INSTALL_DIR" ]; then
    info "Removing previous installation..."
    rm -rf "$INSTALL_DIR"
fi

# --- Download and extract ---
info "Downloading KODA..."
mkdir -p "$INSTALL_DIR"
TMP=$(mktemp -d)
curl -sSL "$REPO_URL" -o "$TMP/koda.tar.gz"
tar -xzf "$TMP/koda.tar.gz" -C "$TMP"
cp -r "$TMP"/koda-main/kiro_tui "$INSTALL_DIR/"
cp "$TMP"/koda-main/pyproject.toml "$INSTALL_DIR/"
rm -rf "$TMP"
ok "Downloaded to $INSTALL_DIR"

# --- Create venv and install ---
info "Creating virtual environment..."
$PYTHON -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$INSTALL_DIR"
ok "Dependencies installed"

# --- Create launcher script ---
LAUNCHER="$INSTALL_DIR/koda.sh"
cat > "$LAUNCHER" << 'EOF'
#!/usr/bin/env bash
source "$HOME/.koda/venv/bin/activate"
python -m kiro_tui.main "$@"
EOF
chmod +x "$LAUNCHER"

# --- Create symlink or shell alias ---
ALIAS_ADDED=false
if [ -w "$(dirname "$BIN_LINK")" ] || [ "$EUID" -eq 0 ]; then
    ln -sf "$LAUNCHER" "$BIN_LINK" 2>/dev/null && ok "Command 'koda' available globally" || true
else
    # Try with sudo
    if command -v sudo &>/dev/null; then
        info "Creating global command (may ask for password)..."
        sudo ln -sf "$LAUNCHER" "$BIN_LINK" 2>/dev/null && ok "Command 'koda' available globally" || ALIAS_ADDED=false
    fi
fi

# Add shell alias as fallback
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ]; then
        # Remove old alias if exists
        sed -i.bak '/# KODA/d; /alias koda=/d' "$rc" 2>/dev/null
        echo "# KODA | Kiro Operator Dashboard Application" >> "$rc"
        echo "alias koda='$LAUNCHER'" >> "$rc"
        ALIAS_ADDED=true
    fi
done
[ "$ALIAS_ADDED" = true ] && ok "Shell alias added"

# --- Desktop shortcut (Linux) ---
if [ "$PLATFORM" = "linux" ]; then
    DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
    APPS_DIR="$HOME/.local/share/applications"
    mkdir -p "$APPS_DIR"

    cat > "$APPS_DIR/koda.desktop" << EOF
[Desktop Entry]
Name=KODA
Comment=Kiro Operator Dashboard Application
Exec=bash -c 'source $INSTALL_DIR/venv/bin/activate && python -m kiro_tui.main'
Terminal=true
Type=Application
Categories=Development;
Icon=utilities-terminal
EOF

    # Copy to desktop if it exists
    if [ -d "$DESKTOP_DIR" ]; then
        cp "$APPS_DIR/koda.desktop" "$DESKTOP_DIR/"
        chmod +x "$DESKTOP_DIR/koda.desktop" 2>/dev/null
        ok "Desktop shortcut created"
    fi
    ok "App menu entry created"
fi

# --- Desktop shortcut (macOS) ---
if [ "$PLATFORM" = "macos" ]; then
    APP_DIR="$HOME/Applications/KODA.app/Contents/MacOS"
    mkdir -p "$APP_DIR"
    cat > "$APP_DIR/koda" << EOF
#!/usr/bin/env bash
open -a Terminal "$INSTALL_DIR/koda.sh"
EOF
    chmod +x "$APP_DIR/koda"

    # Info.plist
    cat > "$HOME/Applications/KODA.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>KODA</string>
    <key>CFBundleExecutable</key><string>koda</string>
    <key>CFBundleIdentifier</key><string>com.koda.app</string>
    <key>CFBundleVersion</key><string>0.1.0</string>
</dict>
</plist>
EOF
    ok "macOS app created in ~/Applications/KODA.app"
fi

# --- Done ---
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  KODA installed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Run:  koda"
echo "  Or:   source ~/.bashrc && koda"
echo ""
echo "  Uninstall: curl -sSL https://raw.githubusercontent.com/patrycksans/koda/main/uninstall.sh | bash"
echo ""
