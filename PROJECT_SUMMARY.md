# KODA — Project Summary

## Architecture

```
kiro_tui/
├── main.py              # Entry point
├── app.py               # Main Textual app, modals (1093 lines)
├── i18n.py              # Translations: en, pt, es (170 lines)
├── components/
│   ├── sidebar.py       # Sidebar: agents, models, prompts, chat, auth (281 lines)
│   ├── chat.py          # ChatArea, ActionPrompt, TrustPicker (314 lines)
│   └── status_bar.py    # Agent, model, context %, spinner (68 lines)
├── services/
│   ├── cli_executor.py  # PTY management, kiro-cli communication (742 lines)
│   └── agent_manager.py # Agent config, allowedTools (76 lines)
├── screens/
│   └── project_selector.py  # Project folder picker
└── utils/
    └── __init__.py
```

**16 Python files, ~2700 lines total.**

## Key Systems

### CLI Executor (`cli_executor.py`)
- PTY-based communication with kiro-cli (Linux) / WSL script (Windows)
- Line-by-line output parsing with ANSI stripping
- Prompt detection (`N% >`) for context tracking
- `/tools` output parsing: sends `/tools`, collects `(name, checked, server)` tuples
- Trust/untrust confirmation filtering (suppressed from chat)
- Trust scope picker detection (`navigate` + `select` → `__TRUST_PICKER__` protocol)
- Echo filtering, noise filtering, response state machine

### Tools Modal (`app.py → ToolsModal`)
- Opens via Ctrl+T → sends `/tools` → parses response → shows modal
- Checkboxes grouped by section (Built-in, MCP servers)
- Each toggle immediately sends `/tools trust <name>` or `/tools untrust <name>`
- Trust All → `/tools trust-all`, Reset → `/tools reset`
- Logs each action to chat area

### Trust Scope Picker (`chat.py → TrustPicker`)
- Appears inline in chat when kiro-cli asks for trust granularity
- Options: Specific paths / Complete directory / Entire Tool
- Sends arrow key navigation + Enter to kiro-cli

### Modals
- `ToolsModal` — Tool permissions
- `SaveModal` — Save chat with name input
- `PickerModal` — Generic list picker (agents, models, sessions)
- `ConfirmModal` — Yes/No with custom labels
- `ConfirmQuitModal` — ESC quit confirmation
- `PromptsManagerModal` — Create/edit/delete prompts

## Cross-Platform
- **Linux/macOS**: Native PTY via `pty.openpty()`
- **Windows**: WSL + `script -qc` for PTY emulation
- UTF-8 environment variables forced on Windows

## i18n
- 3 languages: English, Portuguese (BR), Spanish
- Auto-detects from `LANG` environment variable
