"""Internationalization module"""
import json, os

CONFIG_PATH = os.path.expanduser("~/.config/koda/config.json")

_current_lang = "en"

STRINGS = {
    # Project Selector
    "select_project": {"en": "Select Project Folder", "pt": "Selecionar Pasta do Projeto", "es": "Seleccionar Carpeta del Proyecto"},
    "add": {"en": "+ Add", "pt": "+ Adicionar", "es": "+ Agregar"},
    "remove": {"en": "Remove", "pt": "Remover", "es": "Eliminar"},
    "new_folder_name": {"en": "New folder name:", "pt": "Nome da nova pasta:", "es": "Nombre de la carpeta:"},
    "folder_placeholder": {"en": "my-project", "pt": "meu-projeto", "es": "mi-proyecto"},
    "create": {"en": "Create", "pt": "Criar", "es": "Crear"},
    "cancel": {"en": "Cancel", "pt": "Cancelar", "es": "Cancelar"},
    "select_remove": {"en": "Select folder to remove:", "pt": "Selecionar pasta para remover:", "es": "Seleccionar carpeta a eliminar:"},
    "confirm_delete": {"en": "Delete '{name}' and all its contents?", "pt": "Deletar '{name}' e todo seu conteudo?", "es": "Eliminar '{name}' y todo su contenido?"},
    "yes_delete": {"en": "Yes, delete", "pt": "Sim, deletar", "es": "Si, eliminar"},
    "no": {"en": "No", "pt": "Nao", "es": "No"},
    "language": {"en": "Language: EN", "pt": "Idioma: PT", "es": "Idioma: ES"},

    # Sidebar
    "auth": {"en": "Auth", "pt": "Auth", "es": "Auth"},
    "agents": {"en": "Agents", "pt": "Agentes", "es": "Agentes"},
    "models": {"en": "Models", "pt": "Modelos", "es": "Modelos"},
    "chat": {"en": "Chat", "pt": "Chat", "es": "Chat"},
    "login": {"en": "> Login", "pt": "> Login", "es": "> Login"},
    "logout": {"en": "> Logout", "pt": "> Logout", "es": "> Logout"},
    "whoami": {"en": "> Who Am I", "pt": "> Quem Sou Eu", "es": "> Quien Soy"},
    "save": {"en": "> Save", "pt": "> Salvar", "es": "> Guardar"},
    "load": {"en": "> Load", "pt": "> Carregar", "es": "> Cargar"},
    "list_sessions": {"en": "> List Sessions", "pt": "> Listar Sessoes", "es": "> Listar Sesiones"},
    "clear": {"en": "> Clear", "pt": "> Limpar", "es": "> Limpiar"},
    "compact": {"en": "> Compact", "pt": "> Compactar", "es": "> Compactar"},
    "loading_agents": {"en": "Loading agents...", "pt": "Carregando agentes...", "es": "Cargando agentes..."},

    # Chat
    "type_message": {"en": "Type a message...", "pt": "Digite uma mensagem...", "es": "Escribe un mensaje..."},

    # Status / Logs
    "ready": {"en": "Ready", "pt": "Pronto", "es": "Listo"},
    "thinking": {"en": "Thinking...", "pt": "Pensando...", "es": "Pensando..."},
    "starting_chat": {"en": "Initializing Kiro CLI chat session...", "pt": "Iniciando sessao de chat Kiro CLI...", "es": "Iniciando sesion de chat Kiro CLI..."},
    "chat_active": {"en": "Chat session active", "pt": "Sessao de chat ativa", "es": "Sesion de chat activa"},
    "chat_failed": {"en": "Chat failed to start", "pt": "Falha ao iniciar chat", "es": "Error al iniciar chat"},
    "chat_failed_msg": {"en": "Failed to start chat session. Try restarting.", "pt": "Falha ao iniciar sessao. Tente reiniciar.", "es": "Error al iniciar sesion. Intente reiniciar."},
    "switching_agent": {"en": "Switching to {name}...", "pt": "Trocando para {name}...", "es": "Cambiando a {name}..."},
    "now_chatting": {"en": "Now chatting with: {name}", "pt": "Conversando com: {name}", "es": "Conversando con: {name}"},
    "switch_failed": {"en": "Failed to switch agent", "pt": "Falha ao trocar agente", "es": "Error al cambiar agente"},
    "switching_model": {"en": "Switching to model: {name}", "pt": "Trocando para modelo: {name}", "es": "Cambiando a modelo: {name}"},
    "now_model": {"en": "Now using model: {name}", "pt": "Usando modelo: {name}", "es": "Usando modelo: {name}"},
    "switch_model_failed": {"en": "Failed to switch model", "pt": "Falha ao trocar modelo", "es": "Error al cambiar modelo"},
    "save_chat": {"en": "Save chat session:", "pt": "Salvar sessao de chat:", "es": "Guardar sesion de chat:"},
    "load_chat": {"en": "Load chat session:", "pt": "Carregar sessao de chat:", "es": "Cargar sesion de chat:"},
    "no_saved_chats": {"en": "No saved chat files found", "pt": "Nenhum arquivo de chat encontrado", "es": "No se encontraron archivos de chat"},
    "listing_sessions": {"en": "Listing sessions...", "pt": "Listando sessoes...", "es": "Listando sesiones..."},
    "logging_in": {"en": "Logging in...", "pt": "Fazendo login...", "es": "Iniciando sesion..."},
    "login_success": {"en": "Login successful", "pt": "Login realizado", "es": "Inicio de sesion exitoso"},
    "login_failed": {"en": "Login failed", "pt": "Falha no login", "es": "Error de inicio de sesion"},
    "logging_out": {"en": "Logging out...", "pt": "Fazendo logout...", "es": "Cerrando sesion..."},
    "logout_success": {"en": "Logged out", "pt": "Deslogado", "es": "Sesion cerrada"},
    "logout_failed": {"en": "Logout failed", "pt": "Falha no logout", "es": "Error al cerrar sesion"},
    "error": {"en": "Error", "pt": "Erro", "es": "Error"},
    "or_overwrite": {"en": "Or overwrite existing:", "pt": "Ou sobrescrever existente:", "es": "O sobrescribir existente:"},
    "tools_title": {"en": "Available Tools (toggle to trust/untrust):", "pt": "Ferramentas (alternar confianca):", "es": "Herramientas (alternar confianza):"},
    "trust_selected": {"en": "Trust Selected", "pt": "Confiar Selecionados", "es": "Confiar Seleccionados"},

    # Welcome / Project
    "welcome": {"en": "Welcome to KODA", "pt": "Bem-vindo ao KODA", "es": "Bienvenido a KODA"},
    "project_label": {"en": "Project: {path}", "pt": "Projeto: {path}", "es": "Proyecto: {path}"},

    # Status bar
    "status_bar": {"en": "Agent: {agent} | Model: {model} | {status} | Ctx [{bar}] {pct}%", "pt": "Agente: {agent} | Modelo: {model} | {status} | Ctx [{bar}] {pct}%", "es": "Agente: {agent} | Modelo: {model} | {status} | Ctx [{bar}] {pct}%"},

    # Chat actions feedback
    "chat_cleared": {"en": "Chat cleared", "pt": "Chat limpo", "es": "Chat limpiado"},
    "compact_sent": {"en": "Compact sent", "pt": "Compactar enviado", "es": "Compactar enviado"},
    "saved_as": {"en": "Chat saved as: {name}", "pt": "Chat salvo como: {name}", "es": "Chat guardado como: {name}"},
    "loading_chat": {"en": "Loading chat: {name}", "pt": "Carregando chat: {name}", "es": "Cargando chat: {name}"},
    "sessions_found": {"en": "{n} sessions found:", "pt": "{n} sessoes encontradas:", "es": "{n} sesiones encontradas:"},
    "no_sessions": {"en": "No sessions found", "pt": "Nenhuma sessao encontrada", "es": "No se encontraron sesiones"},

    # Misc
    "apply": {"en": "Apply", "pt": "Aplicar", "es": "Aplicar"},
    "action_yes": {"en": "Yes", "pt": "Sim", "es": "Si"},
    "action_no": {"en": "No", "pt": "Nao", "es": "No"},
    "action_trust": {"en": "Trust", "pt": "Confiar", "es": "Confiar"},

    # Prompts
    "prompts": {"en": "Prompts", "pt": "Prompts", "es": "Prompts"},
    "prompt_create_action": {"en": "+ Create Prompt", "pt": "+ Criar Prompt", "es": "+ Crear Prompt"},
    "prompt_manage": {"en": "⚙ Manage Prompts", "pt": "⚙ Gerenciar Prompts", "es": "⚙ Gestionar Prompts"},
    "prompt_edit": {"en": "Edit", "pt": "Editar", "es": "Editar"},
    "prompt_name": {"en": "Prompt name:", "pt": "Nome do prompt:", "es": "Nombre del prompt:"},
    "prompt_content": {"en": "Prompt content:", "pt": "Conteudo do prompt:", "es": "Contenido del prompt:"},
    "prompt_created": {"en": "Prompt created: {name}", "pt": "Prompt criado: {name}", "es": "Prompt creado: {name}"},
    "prompt_removed": {"en": "Prompt removed: {name}", "pt": "Prompt removido: {name}", "es": "Prompt eliminado: {name}"},
    "prompt_sent": {"en": "Prompt sent: {name}", "pt": "Prompt enviado: {name}", "es": "Prompt enviado: {name}"},
    "prompt_use": {"en": "Use", "pt": "Usar", "es": "Usar"},
    "prompt_delete": {"en": "Delete", "pt": "Deletar", "es": "Eliminar"},
    "prompt_pick_action": {"en": "Action for '{name}':", "pt": "Acao para '{name}':", "es": "Accion para '{name}':"},
    "prompt_scope": {"en": "Scope:", "pt": "Escopo:", "es": "Alcance:"},
    "prompt_local": {"en": "Local (this project)", "pt": "Local (este projeto)", "es": "Local (este proyecto)"},
    "prompt_global": {"en": "Global (all projects)", "pt": "Global (todos projetos)", "es": "Global (todos proyectos)"},

    # Auth flow
    "login_title": {"en": "Login to Kiro", "pt": "Login no Kiro", "es": "Iniciar sesion en Kiro"},
    "license_type": {"en": "License type:", "pt": "Tipo de licenca:", "es": "Tipo de licencia:"},
    "free_label": {"en": "Free (Builder ID / Social)", "pt": "Free (Builder ID / Social)", "es": "Free (Builder ID / Social)"},
    "pro_label": {"en": "Pro (Identity Center)", "pt": "Pro (Identity Center)", "es": "Pro (Identity Center)"},
    "identity_provider_url": {"en": "Identity Provider URL:", "pt": "URL do Identity Provider:", "es": "URL del Identity Provider:"},
    "region_label": {"en": "Region:", "pt": "Regiao:", "es": "Region:"},
    "login_btn": {"en": "Login", "pt": "Entrar", "es": "Iniciar sesion"},
    "skip_login": {"en": "Skip", "pt": "Pular", "es": "Omitir"},
    "auth_checking": {"en": "Checking auth...", "pt": "Verificando auth...", "es": "Verificando auth..."},
    "auth_logged_as": {"en": "Logged in", "pt": "Logado", "es": "Conectado"},
    "auth_not_logged": {"en": "Not logged in", "pt": "Nao logado", "es": "No conectado"},
    "auth_device_flow": {"en": "Follow the instructions in your terminal/browser", "pt": "Siga as instrucoes no terminal/browser", "es": "Siga las instrucciones en su terminal/navegador"},
}

LANGUAGES = {"en": "English", "pt": "Portugues", "es": "Espanol"}


def set_lang(lang: str):
    global _current_lang
    _current_lang = lang


def get_lang() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    s = STRINGS.get(key, {})
    text = s.get(_current_lang, s.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text


def load_lang_from_config():
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
            set_lang(cfg.get("language", "en"))
    except Exception:
        pass


def save_lang_to_config(lang: str):
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    cfg["language"] = lang
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f)
