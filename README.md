# KODA | Kiro Operator Dashboard Application

```
 █▄▀  █▀█  █▀▄  ▄▀█
 █░█  █▄█  █▄▀  █▀█
```

A TUI (Text User Interface) for [Kiro CLI](https://kiro.dev), built with Python and [Textual](https://textual.textualize.io/).

## Install

**Prerequisites:** Python 3.8+ and [kiro-cli](https://kiro.dev/docs/cli/install/) installed.

### One-click (download and double-click)

| Platform | File | How |
|----------|------|-----|
| Windows | [`install.bat`](https://raw.githubusercontent.com/PatryckSans/koda/main/install.bat) | Download → double-click |
| Linux | [`install-koda.desktop`](https://raw.githubusercontent.com/PatryckSans/koda/main/install-koda.desktop) | Download → right-click → Allow Launching → double-click |

### Terminal

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/PatryckSans/koda/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/PatryckSans/koda/main/install.ps1 | iex
```

Then run:
```bash
koda
```

## Features

- **Auth** — Login, Logout, Who Am I
- **Agents** — List, swap agents (restarts chat with MCP servers)
- **Models** — List, switch models on the fly
- **Prompts** — Create, edit, delete, use prompts (local and global)
- **Chat** — Save, Load, List Sessions, Clear, Compact
- **Tools** — Real-time tool permissions manager (Ctrl+T)
  - Fetches live tool list from kiro-cli (`/tools`)
  - Checkboxes toggle trust/untrust immediately per tool
  - Grouped by section: Built-in, MCP servers
  - Trust All / Reset / Done buttons
  - Trust scope picker for granularity (path / directory / entire tool)
- **Action Prompts** — Visual Yes/No/Trust buttons for tool approvals
- **Status Bar** — Animated spinner, agent, model, context usage
- **Command Palette** — Ctrl+P for quick access to all commands
- **i18n** — English, Portuguese, Spanish
- **Cross-platform** — Linux, macOS, Windows (via WSL)

## Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+P` | Command Palette |
| `Ctrl+T` | Tools Manager |
| `Ctrl+S` | Save Chat |
| `Ctrl+L` | Clear Chat |
| `Ctrl+K` | Compact |
| `Ctrl+R` | Manage Prompts |
| `ESC` | Quit |

## Uninstall

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/PatryckSans/koda/main/uninstall.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/PatryckSans/koda/main/uninstall.ps1 | iex
```

## License

MIT
