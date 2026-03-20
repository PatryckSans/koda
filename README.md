# Kiro TUI

Text User Interface for Kiro CLI - A visual interface to interact with Kiro CLI without memorizing slash commands.

## Features

✅ **Implemented (MVP)**:
- **Authentication** - Login with device flow, check auth status
- Agent management (list, swap with badges)
- Chat interface with message history
- Status bar showing current agent/model/status
- Sidebar navigation with keyboard support
- Toast notifications and inline logs
- Async command execution

🚧 **Planned**:
- Model selection
- Chat save/load/list
- Context file management
- Tools visualization
- Code intelligence controls
- Knowledge base management
- Experiments toggle
- Hooks visualization
- Settings management

## Installation

```bash
cd kiro-tui
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Usage

```bash
# From within the venv
python -m kiro_tui.main

# Or if installed globally
kiro-tui

# Or using the alias
kkt
```

## First Time Setup

1. Launch the TUI: `kkt`
2. Navigate to "Auth" section in sidebar
3. Select "🔐 Login"
4. Follow the device flow instructions in the chat
5. Once logged in, you can use all features

## Keyboard Shortcuts

- `q` or `Ctrl+C` - Quit
- `↑/↓` - Navigate sidebar
- `Enter` - Select item
- `Tab` - Switch focus between sidebar and chat

## Architecture

```
kiro-tui/
├── kiro_tui/
│   ├── app.py              # Main Textual app
│   ├── main.py             # Entry point
│   ├── components/
│   │   ├── sidebar.py      # Sidebar with sections
│   │   ├── chat.py         # Chat area
│   │   └── status_bar.py   # Status bar
│   └── services/
│       ├── cli_executor.py # CLI command executor
│       └── agent_manager.py # Agent management
└── pyproject.toml          # Dependencies
```

## Development

### Running Tests

```bash
python test_services.py
```

### Adding New Features

1. Add service in `services/` for CLI integration
2. Create component in `components/` for UI
3. Wire up in `app.py`

## Requirements

- Python 3.8+
- textual >= 0.47.0
- rich >= 13.0.0
- kiro-cli (must be in PATH)

## License

MIT
