# ui.py
# -*- coding: utf-8 -*-
import asyncio
import datetime
import threading
from nicegui import app, ui
from timer import FocusTimer
import subjects
import statistics
import settings
import database

# Centralized global state to prevent multi-tab/refresh desynchronization and race conditions
cached_stats = {'today': 0, 'week': 0, 'total': 0, 'avg_week_hours': 0.0, 'focus_days': 0}
cached_active_subject = None
cached_weekly_goal_hours = 10
cached_auto_rotate = True  # Track dynamic rotation mode state
cached_language = 'en'     # Track active interface language state
active_clients = set()

# Thread-safety lock to prevent ASGI render loop desynchronization
_CACHE_LOCK = threading.Lock()

# Global translation map (English default, selectable PT-BR)
TRANSLATIONS = {
    'en': {
        'greeting_morning': "Good morning!",
        'greeting_afternoon': "Good afternoon!",
        'greeting_evening': "Good evening!",
        'config_title': "Configuration",
        'config_focus': "Focus Period (min)",
        'config_break': "Break Period (min)",
        'config_goal': "Weekly Target (hours)",
        'config_rotation_mode': "Rotation Mode",
        'config_rotation_auto': "Daily Automatic",
        'config_rotation_manual': "Manual Session-Based",
        'config_language': "Language / Idioma",
        'config_reset_stats': "Reset statistics",
        'config_confirm_title': "Are you sure?",
        'config_confirm_desc': "This will permanently delete all logged focus sessions.",
        'config_cancel': "Cancel",
        'config_reset': "Reset",
        'config_save': "Save Changes",
        'config_notify_wiped': "Statistics wiped out.",
        'edit_title': "Edit Suggestions",
        'edit_placeholder': "Activity name",
        'edit_add': "Add",
        'edit_no_items': "[No items defined]",
        'edit_close': "Close Panel",
        'help_title': "Information",
        'help_subtitle': "Consistency and Focus Engine",
        'help_desc': """
            <div class="text-xs frappe-dark mb-4 leading-relaxed" style="text-transform: none !important; display: flex; flex-direction: column; gap: 10px;">
                <p class="m-0">This system utilizes integrated countdown and count-up timers as the mechanism to support focus while tracking data.</p>
                <p class="m-0">Every session automatically commits data logs including the calendar date, study duration, suggestion studied and starting and ending timestamps into the history log.</p>
                <p class="m-0">You can define a pool of specific suggestions with assigned probability weights; the engine triggers a weighted selection loop to generate a single daily suggestion which alters every new day.</p>
                <p class="m-0">To safeguard late-night sessions from abrupt changes, this rotation occurs exclusively upon your first application launch of a fresh calendar day.</p>
            </div>
        """,
        'help_close': "Close Info",
        'log_title': "Focus Sessions Log",
        'log_export': "Export CSV",
        'log_weekly_blueprint': "Weekly Activity Blueprint:",
        'log_no_sessions': "[No sessions recorded yet]",
        'log_col_day': "Day (Date | Weekday)",
        'log_col_sub': "Suggestion Studied",
        'log_col_time': "Time",
        'log_close': "Close Log",
        'main_weekly_goal': "Weekly Goal",
        'main_stats_title': "Statistics",
        'main_pace': "Pace",
        'main_pace_suffix': " hours/week",
        'main_total_hours': "Total Hours",
        'main_total_days': "Total Focus Days",
        'main_total_days_suffix': " days",
        'main_show_more': "Show More »",
        'main_timer_title': "Timer",
        'main_timer_focus': "Focus",
        'main_timer_break': "Break",
        'main_stopwatch': "Stopwatch",
        'main_today_label': "Today:",
        'main_skip_break': "Skip Break »",
        'main_suggestion_today': "Today's suggestion:",
        'main_suggestion_current': "Current suggestion:",
        'main_define_suggestions': "+ Define Suggestions",
    },
    'pt': {
        'greeting_morning': "Bom dia!",
        'greeting_afternoon': "Boa tarde!",
        'greeting_evening': "Boa noite!",
        'config_title': "Configurações",
        'config_focus': "Período de Foco (min)",
        'config_break': "Intervalo de Descanso (min)",
        'config_goal': "Meta Semanal (horas)",
        'config_rotation_mode': "Modo de Rotação",
        'config_rotation_auto': "Automático Diário",
        'config_rotation_manual': "Manual por Sessão",
        'config_language': "Idioma / Language",
        'config_reset_stats': "Limpar estatísticas",
        'config_confirm_title': "Tem certeza?",
        'config_confirm_desc': "Isso excluirá permanentemente todo o seu histórico de foco.",
        'config_cancel': "Cancelar",
        'config_reset': "Excluir",
        'config_save': "Salvar Alterações",
        'config_notify_wiped': "Estatísticas redefinidas.",
        'edit_title': "Editar Matérias",
        'edit_placeholder': "Nome da matéria",
        'edit_add': "Criar",
        'edit_no_items': "[Nenhuma matéria definida]",
        'edit_close': "Fechar Painel",
        'help_title': "Informações",
        'help_subtitle': "Consistency and Focus Engine",
        'help_desc': """
            <div class="text-xs frappe-dark mb-4 leading-relaxed" style="text-transform: none !important; display: flex; flex-direction: column; gap: 10px;">
                <p class="m-0">Este sistema utiliza cronômetros integrados de contagem regressiva (Pomodoro) e contagem progressiva (Cronômetro) como mecanismo para impulsionar o foco e registrar dados de estudo.</p>
                <p class="m-0">Cada sessão registra e consolida automaticamente no banco de dados local a data, a duração real do foco, a matéria estudada e os horários exatos de início e término.</p>
                <p class="m-0">Você pode cadastrar uma lista de matérias com pesos de probabilidade específicos; o motor de sorteio utiliza um loop baseado em bilhetes para sugerir dinamicamente a matéria da vez.</p>
                <p class="m-0">Para proteger sessões de estudo noturnas de interrupções bruscas de rotação, o rodízio automático diário ocorre apenas quando o app é aberto pela primeira vez em um novo dia do calendário.</p>
            </div>
        """,
        'help_close': "Fechar Informações",
        'log_title': "Histórico de Foco",
        'log_export': "Exportar CSV",
        'log_weekly_blueprint': "Atividade Semanal (Gráfico):",
        'log_no_sessions': "[Nenhuma sessão registrada ainda]",
        'log_col_day': "Dia (Data | Semana)",
        'log_col_sub': "Matéria Estudada",
        'log_col_time': "Duração",
        'log_close': "Fechar Registro",
        'main_weekly_goal': "Meta Semanal",
        'main_stats_title': "Estatísticas",
        'main_pace': "Ritmo",
        'main_pace_suffix': " horas/semana",
        'main_total_hours': "Total de Horas",
        'main_total_days': "Dias de Foco",
        'main_total_days_suffix': " dias",
        'main_show_more': "Ver Mais »",
        'main_timer_title': "Cronômetro",
        'main_timer_focus': "Foco",
        'main_timer_break': "Intervalo",
        'main_stopwatch': "Cronômetro",
        'main_today_label': "Hoje:",
        'main_skip_break': "Pular Descanso »",
        'main_suggestion_today': "Sugestão de hoje:",
        'main_suggestion_current': "Sugestão atual:",
        'main_define_suggestions': "+ Definir Matérias",
    }
}

def t(key: str) -> str:
    """Thread-safe dynamic translation retrieval dictionary wrapper."""
    with _CACHE_LOCK:
        lang = cached_language
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, '')

def refresh_global_cache():
    """Refreshes all memory caches at once to prevent main thread disk blocking loops."""
    global cached_stats, cached_active_subject, cached_weekly_goal_hours, cached_auto_rotate, cached_language
    
    new_stats = statistics.get_stats()
    new_subject = subjects.get_active_subject()
    new_hours = settings.get_weekly_goal_hours()
    new_auto_rotate = settings.get_auto_rotate()
    new_language = settings.get_setting('language', 'en')
    
    with _CACHE_LOCK:
        cached_stats = new_stats
        cached_active_subject = new_subject
        cached_weekly_goal_hours = new_hours
        cached_auto_rotate = new_auto_rotate
        cached_language = new_language

def global_on_session_complete(duration_seconds: int, mode: str):
    with _CACHE_LOCK:
        current_subject = cached_active_subject
        
    def save_and_refresh():
        if current_subject:
            statistics.record_session(current_subject.id, duration_seconds, mode)
        refresh_global_cache()
    
    try:
        # Safely hand off the blocking DB save operation to the running event loop's thread pool executor
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, save_and_refresh)
    except RuntimeError:
        # Robust fallback for non-async calling parameters
        threading.Thread(target=save_and_refresh, daemon=True).start()

def global_on_timer_end(mode: str):
    # Safe non-blocking broadcast across all active user client connections
    js_code = ""
    if mode == 'pomodoro':
        js_code = "const ctx = new (window.AudioContext || window.webkitAudioContext)(); const osc = ctx.createOscillator(); const gain = ctx.createGain(); osc.type = 'sine'; osc.frequency.setValueAtTime(880, ctx.currentTime); gain.gain.setValueAtTime(0.1, ctx.currentTime); gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.5); osc.connect(gain); gain.connect(ctx.destination); osc.start(); osc.stop(ctx.currentTime + 0.5);"
    elif mode == 'break':
        js_code = "const ctx = new (window.AudioContext || window.webkitAudioContext)(); [0, 0.2].forEach(t => { const osc = ctx.createOscillator(); const gain = ctx.createGain(); osc.type = 'square'; osc.frequency.setValueAtTime(440, ctx.currentTime + t); gain.gain.setValueAtTime(0.05, ctx.currentTime + t); gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + 0.15); osc.connect(gain); gain.connect(ctx.destination); osc.start(ctx.currentTime + t); osc.stop(ctx.currentTime + t + 0.15); });"
    
    if js_code:
        for client in list(active_clients):
            try:
                client.run_javascript(js_code, respond=False)
            except Exception:
                pass

focus_timer = FocusTimer(on_tick=lambda: None, on_complete=global_on_session_complete, on_timer_end=global_on_timer_end)

async def global_timer_ticker():
    while True:
        await asyncio.sleep(1.0)
        focus_timer.tick()

app.on_startup(global_timer_ticker)

def load_initial_stats():
    """Hydrates local UI state from the database; safely invoked by main orchestrator."""
    try:
        refresh_global_cache()
    except Exception as e:
        print(f"[Hydration Error] Failed to initialize ui cache elements: {e}")

async def build_ui():
    """Builds the main user interface layout asynchronously without event loop stalls."""
    global active_clients

    ui.colors(primary='#4e3629', positive='#a3b18a')
    
    client = ui.context.client
    active_clients.add(client)
    
    def on_disconnect():
        active_clients.discard(client)
        if not active_clients:
            focus_timer.handle_disconnect()
            
    ui.context.client.on_disconnect(on_disconnect)
    
    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght=0,400;0,700;1,400;1,700&display=swap');
        
        * {
            font-family: 'Courier Prime', monospace !important;
            font-weight: normal !important;
        }
        
        .q-icon, .material-icons {
            font-family: 'Material Icons' !important;
        }
        
        body {
            background-color: #000000 !important;
            font-size: 15px !important;
        }
        
        .mono-card {
            background-color: #000000 !important;
            border: 1px solid #16100d !important;
        }
        
        .mono-divider {
            border-bottom: 1px solid #16100d !important;
        }

        /* CLOCK ISOLATED CONTAINER TINT LOCK */
        .clock-fixed-tint, .clock-fixed-tint * {
            color: #59514a !important;
            font-size: 12px !important;
            font-family: 'Courier Prime', monospace !important;
        }
        
        /* PROPRIETARY SEMANTIC CLASSES */
        .frappe-light { color: #ebdcd0 !important; }
        .frappe-dark { color: #59514a !important; }
        .frappe-muted { color: #382d26 !important; }
        
        /* TOTAL RIPPLE EXTERMINATION */
        .q-ripple, .q-ripple__inner, [class*="q-ripple"] {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
            background: transparent !important;
            background-color: transparent !important;
        }
        
        /* RADICAL RECTANGULAR HOVER REMOVAL FOR ALL COMPONENT STATES */
        html body .q-focus-helper,
        html body .q-btn .q-focus-helper,
        html body .q-btn::before,
        html body .q-btn::after {
            display: none !important;
            opacity: 0 !important;
            background: transparent !important;
            background-color: transparent !important;
            box-shadow: none !important;
            content: none !important;
        }
        
        /* STANDARD RECTANGULAR BUTTONS */
        .mono-btn {
            background-color: #000000 !important;
            border: 1px solid #16100d !important;
            color: #b5a499 !important;
            text-transform: uppercase !important;
            border-radius: 2px !important;
            box-shadow: none !important;
            font-size: 13px !important;
            padding: 5px 14px !important;
            transition: all 0.1s ease-in-out;
        }
        .mono-btn:hover {
            background-color: #120c09 !important;
            color: #ebdcd0 !important;
            border-color: #382d26 !important;
        }
        
        /* TIMER CONTROL ROUND BUTTONS */
        html body .q-btn.timer-btn,
        html body .q-btn.timer-btn:hover,
        html body .q-btn.timer-btn:focus,
        html body .q-btn.timer-btn:active {
            background-color: transparent !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        html body .q-btn.timer-btn .q-icon,
        html body .q-btn.timer-btn .q-btn__content {
            color: #4e3629 !important;
            font-size: 30px !important;
            transition: color 0.1s ease-in-out;
        }
        html body .q-btn.timer-btn:hover .q-icon,
        html body .q-btn.timer-btn:hover .q-btn__content {
            color: #875d46 !important;
        }
        html body .q-btn.timer-btn:focus .q-icon,
        html body .q-btn.timer-btn:active .q-icon {
            color: #4e3629 !important;
        }
        html body .q-btn.timer-btn:hover:focus .q-icon {
            color: #875d46 !important;
        }
        
        /* HELP AND SETTINGS BUTTONS - RADICAL HOVER OVERRIDE */
        html body .icon-panel-btn,
        html body .icon-panel-btn:hover,
        html body .icon-panel-btn:focus,
        html body .icon-panel-btn:active {
            background: transparent !important;
            background-color: transparent !important;
            box-shadow: none !important;
            border: none !important;
        }
        html body .icon-panel-btn .q-icon {
            color: #59514a !important;
            transition: color 0.1s ease-in-out;
        }
        html body .icon-panel-btn:hover .q-icon {
            color: #ebdcd0 !important;
        }
        html body .icon-panel-btn:focus .q-icon,
        html body .icon-panel-btn:active .q-icon {
            color: #59514a !important;
        }
        html body .icon-panel-btn:hover:focus .q-icon {
            color: #ebdcd0 !important;
        }

        /* INLINE SUGGESTION EDIT PENCIL BUTTON (SUPERSCRIPT EXPONENT DESIGN) */
        html body .edit-pencil-btn,
        html body .edit-pencil-btn:hover,
        html body .edit-pencil-btn:focus,
        html body .edit-pencil-btn:active {
            background: transparent !important;
            background-color: transparent !important;
            box-shadow: none !important;
            border: none !important;
            align-self: flex-start !important;
            position: relative !important;
            top: -1px !important;
            margin-left: -1px !important;
            padding: 0 !important;
        }
        html body .edit-pencil-btn .q-icon {
            color: #4e3629 !important;
            font-size: 10px !important;
            transition: color 0.1s ease-in-out;
        }
        html body .edit-pencil-btn:hover .q-icon {
            color: #875d46 !important;
        }

        /* INLINE SUGGESTION ROTATE BUTTON (PROMINENT DESIGN WITH HOVER SPIN) */
        html body .rotate-main-btn,
        html body .rotate-main-btn:hover,
        html body .rotate-main-btn:focus,
        html body .rotate-main-btn:active {
            background: transparent !important;
            background-color: transparent !important;
            box-shadow: none !important;
            border: none !important;
            align-self: center !important;
            padding: 0 !important;
            margin-left: 6px !important;
            margin-right: 2px !important;
        }
        html body .rotate-main-btn .q-icon {
            color: #ebdcd0 !important;
            font-size: 16px !important;
            transition: transform 0.3s ease-in-out, color 0.1s ease-in-out;
        }
        html body .rotate-main-btn:hover .q-icon {
            color: #875d46 !important;
            transform: rotate(180deg);
        }
        
        /* DEFINE SUGGESTIONS BUTTON */
        .inline-mono-btn {
            background-color: #4e3629 !important;
            border: 1px solid #4e3629 !important;
            color: #ebdcd0 !important;
            text-transform: uppercase !important;
            border-radius: 2px !important;
            box-shadow: none !important;
            font-size: 11px !important;
            padding: 0px 8px !important;
            height: 22px !important;
            min-height: 22px !important;
            display: inline-flex !important;
            align-items: center !important;
            transition: all 0.1s ease-in-out;
        }
        html body .inline-mono-btn,
        html body .inline-mono-btn *,
        html body .inline-mono-btn .q-btn__content {
            color: #ebdcd0 !important;
        }
        .inline-mono-btn:hover {
            background-color: #6f4e37 !important;
            border-color: #6f4e37 !important;
            color: #ffffff !important;
        }
        html body .inline-mono-btn:hover * {
            color: #ffffff !important;
        }
        
        /* UNIFIED LINK HOVER (SHOW MORE) */
        .blue-link {
            color: #4e3629 !important;
            transition: color 0.1s ease-in-out;
        }
        .blue-link:hover {
            color: #875d46 !important;
        }
        
        /* DIALOG CONFIGURATION CORES - SEPARATED LABEL AND INPUT VALUE COLORS */
        html body .q-dialog .q-field__label {
            color: #59514a !important;
        }
        html body .q-dialog .q-field__native,
        html body .q-dialog .q-field__input,
        html body .q-dialog .q-field__prefix,
        html body .q-dialog .q-field__suffix {
            color: #ebdcd0 !important;
        }
        html body .q-dialog .q-field--outlined .q-field__control {
            border: 1px solid #16100d !important;
        }
        html body .q-dialog .mono-card .text-white {
            color: #ebdcd0 !important;
        }
        html body .q-dialog .mono-card .text-neutral-500 {
            color: #59514a !important;
        }
        
        /* ABSOLUTE REMOVAL OF WHITE GLOW / SHADOWS FROM DIALOGS AND MODALS */
        html body .q-dialog .mono-card,
        html body .q-dialog__inner > div {
            box-shadow: none !important;
            border: 1px solid #16100d !important;
        }
        
        /* PROGRESS BAR: HOLLOW CONTEXT WITH DARK BORDER */
        html body .q-linear-progress { 
            background-color: #000000 !important; 
            background: #000000 !important;
            color: #6f4e37 !important; 
            border: 1px solid #4e3629 !important;
        }
        html body .q-linear-progress__track {
            background-color: #000000 !important;
            background: #000000 !important;
            opacity: 0 !important;
            display: none !important;
        }
        
        @keyframes gradient-flow-right {
            0% { background-position: 200% 50%; }
            100% { background-position: 0% 50%; }
            }
        .q-linear-progress__model {
            background: linear-gradient(90deg, #120c09, #6f4e37, #120c09) !important;
            background-size: 200% 200% !important;
            animation: gradient-flow-right 3s linear infinite !important;
            }
        
        /* SKIP BREAK LINK SHORTCUT BUTTON */
        .skip-btn-custom {
            color: #59514a !important;
        }
        .skip-btn-custom:hover {
            color: #ebdcd0 !important;
        }

        /* ANCHORED OVERRIDES FOR METRICS AND HEADERS */
        html body .text-white, 
        html body [class*="text-white"],
        html body .text-neutral-300, 
        html body [class*="text-neutral-300"],
        html body .text-neutral-400.uppercase,
        html body [class*="text-neutral-400"].uppercase,
        html body .text-base,
        html body .text-5xl { 
            color: #ebdcd0 !important; 
        }
        html body .text-neutral-500, 
        html body [class*="text-neutral-500"],
        html body .text-neutral-400:not(.uppercase),
        html body [class*="text-neutral-400"]:not(.uppercase) { 
            color: #59514a !important; 
        }
        .text-neutral-600 { color: #382d26 !important; }
        .bg-neutral-950 { background-color: #000000 !important; }
        .border-neutral-950 { border-color: #16100d !important; }

        /* ANTI-LAG ATOMIC DISCRETE BUTTON TOGGLE SPECIFICATIONS */
        html body .toggle-btn-pomo, html body .toggle-btn-sw {
            font-size: 11px !important;
            padding: 3px 10px !important;
            border-radius: 0px !important;
            box-shadow: none !important;
            text-transform: uppercase !important;
            transition: none !important;
        }
        html body .toggle-btn-pomo {
            border-top-left-radius: 2px !important;
            border-bottom-left-radius: 2px !important;
        }
        html body .toggle-btn-sw {
            border-top-right-radius: 2px !important;
            border-bottom-right-radius: 2px !important;
        }
        
        /* GITHUB LOGO UNCLIPPED & LINK COLOR MATRIX */
        a.gh-link-custom {
            display: inline-flex !important;
            align-items: center !important;
            gap: 6px !important;
            text-decoration: none !important;
            color: #875d46 !important;
            font-size: 11px !important;
            transition: color 0.1s ease-in-out !important;
            line-height: 16px !important;
        }
        a.gh-link-custom:hover, a.gh-link-custom:hover * {
            color: #ebdcd0 !important;
        }
    </style>
    ''')

    def get_greeting() -> str:
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return t('greeting_morning')
        elif 12 <= hour < 18:
            return t('greeting_afternoon')
        else:
            return t('greeting_evening')

    def open_settings_panel():
        with ui.dialog().props('transition-show=none transition-hide=none') as dialog, ui.card().classes('w-80 rounded-none p-4 mono-card'):
            ui.label(t('config_title')).classes('text-xs frappe-light uppercase tracking-wider mb-4 w-full')
            
            with _CACHE_LOCK:
                current_pomo = settings.get_pomodoro_minutes()
                current_break = settings.get_break_minutes()
                current_goal = cached_weekly_goal_hours
                current_auto_rotate = cached_auto_rotate
                current_language = cached_language
            
            pomo_input = ui.number(t('config_focus'), value=current_pomo, format='%.0f').classes('w-full mb-2')
            break_input = ui.number(t('config_break'), value=current_break, format='%.0f').classes('w-full mb-2')
            goal_input = ui.number(t('config_goal'), value=current_goal, format='%.0f').classes('w-full mb-2')
            
            # Dynamic Dropdown Selector to switch between rotation models
            rotation_mode_input = ui.select(
                options={True: t('config_rotation_auto'), False: t('config_rotation_manual')},
                value=current_auto_rotate,
                label=t('config_rotation_mode')
            ).classes('w-full mb-2')

            # Dropdown Selector to change UI languages live
            language_input = ui.select(
                options={'en': 'English', 'pt': 'Português'},
                value=current_language,
                label=t('config_language')
            ).classes('w-full mb-4')
            
            def confirm_reset():
                with ui.dialog().props('transition-show=none transition-hide=none') as confirm_dialog, ui.card().classes('w-72 rounded-none p-4 mono-card'):
                    ui.label(t('config_confirm_title')).classes('text-xs frappe-light uppercase tracking-wider mb-1')
                    ui.label(t('config_confirm_desc')).classes('text-xs frappe-dark mb-4')
                    with ui.row().classes('w-full justify-end gap-2'):
                        ui.button(t('config_cancel'), on_click=confirm_dialog.close).classes('mono-btn text-xs')
                        async def perform_reset():
                            def b_delete():
                                with database.get_db() as db:
                                    db.execute('DELETE FROM focus_sessions')
                                refresh_global_cache()
                            await asyncio.get_running_loop().run_in_executor(None, b_delete)
                            update_display()
                            confirm_dialog.close()
                            dialog.close()
                            ui.notify(t('config_notify_wiped'), type='warning')
                        ui.button(t('config_reset'), on_click=perform_reset).classes('mono-btn text-xs border-red-900 text-red-500')
                confirm_dialog.open()
                
            ui.button(t('config_reset_stats'), on_click=confirm_reset).props('flat dense no-ripple').classes('text-red-500/70 hover:text-red-400 text-xs self-start mb-3').style('text-transform: none; padding-left: 0;')

            async def save_settings():
                pomo_val = int(pomo_input.value) if pomo_input.value is not None else 25
                break_val = int(break_input.value) if break_input.value is not None else 5
                goal_val = int(goal_input.value) if goal_input.value is not None else 10
                auto_rotate_val = bool(rotation_mode_input.value)
                lang_val = str(language_input.value)

                def b_save():
                    settings.set_setting('pomodoro_minutes', pomo_val)
                    settings.set_setting('break_minutes', break_val)
                    settings.set_setting('weekly_goal_hours', goal_val)
                    settings.set_auto_rotate(auto_rotate_val)
                    settings.set_setting('language', lang_val)
                    focus_timer.sync_durations()
                    refresh_global_cache()
                await asyncio.get_running_loop().run_in_executor(None, b_save)
                update_language_labels()  # Force update to static layouts once.
                update_display()
                dialog.close()

            ui.button(t('config_save'), on_click=save_settings).classes('w-full mono-btn mb-1')
        dialog.open()

    async def open_suggestions_panel():
        with ui.dialog().props('transition-show=none transition-hide=none') as dialog, ui.card().classes('w-[360px] rounded-none p-4 mono-card'):
            ui.label(t('edit_title')).classes('text-xs frappe-light uppercase tracking-wider mb-3')
            
            with ui.row().classes('w-full items-center gap-1 mb-3 pb-3 mono-divider'):
                new_name = ui.input(placeholder=t('edit_placeholder')).classes('w-36').props('dense dark')
                new_weight = ui.number(value=1, format='%.0f').classes('w-10').props('dense dark')
                async def quick_add():
                    if new_name.value:
                        name = new_name.value
                        weight = int(new_weight.value) if new_weight.value else 1
                        def b_add():
                            subjects.add_subject(name, weight)
                            refresh_global_cache()
                        await asyncio.get_running_loop().run_in_executor(None, b_add)
                        new_name.value = ''
                        await rebuild_management_view()
                        update_display()
                ui.button(t('edit_add'), on_click=quick_add).classes('mono-btn text-xs py-1')

            subject_list_container = ui.column().classes('w-full gap-1 mb-4 max-h-48 overflow-y-auto')
            
            async def trigger_update(s_id, name_val, weight_val):
                def b_update():
                    subjects.update_subject(s_id, name_val, int(weight_val) if weight_val else 1)
                    refresh_global_cache()
                await asyncio.get_running_loop().run_in_executor(None, b_update)
                refresh_global_cache()

            async def trigger_delete(s_id):
                def b_delete():
                    subjects.delete_subject(s_id)
                    refresh_global_cache()
                await asyncio.get_running_loop().run_in_executor(None, b_delete)
                await rebuild_management_view()
                update_display()
            
            async def rebuild_management_view():
                all_items = await asyncio.get_running_loop().run_in_executor(None, subjects.get_all_subjects)
                subject_list_container.clear()
                
                with subject_list_container:
                    if not all_items:
                        ui.label(t('edit_no_items')).classes('text-xs frappe-muted italic')
                    
                    for sub in all_items:
                        with ui.row().classes('w-full items-center justify-between gap-2 p-1 bg-neutral-950 mono-divider'):
                            # Occupy full width dynamically with flex-grow
                            name_edit = ui.input(value=sub.name).classes('flex-grow').props('dense dark')
                            weight_edit = ui.number(value=sub.weight, format='%.0f').classes('w-12').props('dense dark')
                            
                            # Optimized automatic saving routine using closed closures
                            def make_save_handler(sid, n, w, old_n, old_w):
                                async def handler():
                                    new_name = n.value
                                    new_weight = int(w.value) if w.value else 1
                                    if new_name != old_n or new_weight != old_w:
                                        await trigger_update(sid, new_name, new_weight)
                                return handler
                            
                            save_handler = make_save_handler(sub.id, name_edit, weight_edit, sub.name, sub.weight)
                            
                            # Dynamic triggers to auto-save on blurs and enter key strokes
                            name_edit.on('blur', save_handler)
                            name_edit.on('keydown.enter', save_handler)
                            weight_edit.on('blur', save_handler)
                            weight_edit.on('keydown.enter', save_handler)
                            
                            ui.button(icon='delete', on_click=lambda e, sid=sub.id: trigger_delete(sid)).props('flat dense size=sm color=grey no-ripple')
                subject_list_container.update()

            ui.button(t('edit_close'), on_click=dialog.close).classes('w-full mono-btn mt-1')
            await rebuild_management_view()
        dialog.open()

    def open_help_panel():
        with ui.dialog().props('transition-show=none transition-hide=none') as dialog, ui.card().classes('w-[420px] rounded-none p-4 mono-card'):
            ui.label(t('help_title')).classes('text-xs frappe-light uppercase tracking-wider mb-3 w-full pb-1 mono-divider')
            
            ui.html('<div class="text-xs mb-3" style="color: #59514a !important; text-transform: none !important;"><span style="color: #4e3629 !important; font-weight: bold;">C</span>onsistency <span style="color: #4e3629 !important; font-weight: bold;">a</span>nd <span style="color: #4e3629 !important; font-weight: bold;">F</span>ocus <span style="color: #4e3629 !important; font-weight: bold;">E</span>ngine</div>')
            
            ui.html(t('help_desc'))
                        
            with ui.row().classes('w-full pt-2.5 mt-1 items-center').style('border-top: 1px solid #16100d;'):
                ui.html('''
                <a href="https://github.com/j46-txt/CaFE" target="_blank" class="gh-link-custom">
                    <svg height="16" width="16" viewBox="0 0 16 16" fill="currentColor" style="display: inline-block; vertical-align: middle; flex-shrink: 0; width: 16px; height: 16px;"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2 3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.85.54 1.71 0 1.24-.01 2.23-.01 2.53 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg><span style="font-family: 'Courier Prime', monospace !important;">github.com/j46-txt/CaFE</span>
                </a>
                ''')
            
            ui.button(t('help_close'), on_click=dialog.close).classes('w-full mono-btn mt-4 text-xs')
        dialog.open()

    async def open_history_panel():
        # Render dialog immediately with loading spinner to prevent UI freeze
        with ui.dialog().props('transition-show=none transition-hide=none') as dialog, ui.card().classes('w-[480px] rounded-none p-4 mono-card'):
            with ui.row().classes('w-full justify-between items-center mb-3 pb-1 mono-divider'):
                ui.label(t('log_title')).classes('text-xs frappe-light uppercase tracking-wider')
                ui.button(t('log_export'), on_click=download_csv_log).classes('mono-btn').style('font-size: 10px !important; padding: 2px 8px !important; height: auto; min-height: 0;')
            
            content_container = ui.column().classes('w-full gap-0')
            with content_container:
                ui.spinner('dots', size='md', color='#59514a').classes('self-center mt-4 mb-4')

            ui.button(t('log_close'), on_click=dialog.close).classes('w-full mono-btn text-xs mt-2')

        dialog.open()

        def fetch_history_data():
            with database.get_db() as db:
                summary_rows = db.execute('''
                    SELECT start_date, SUM(duration_seconds) as total_sec 
                    FROM focus_sessions 
                    GROUP BY start_date 
                    ORDER BY start_date DESC LIMIT 7
                ''').fetchall()
                summary = [dict(r) for r in summary_rows]
                
                rows = db.execute('''
                    SELECT fs.start_date, fs.duration_seconds, s.name as subject_name
                    FROM focus_sessions fs
                    LEFT JOIN subjects s ON fs.subject_id = s.id
                    ORDER BY fs.id DESC LIMIT 50
                ''').fetchall()
                logs = [dict(r) for r in rows]
            return summary, logs

        summary_rows, rows = await asyncio.get_running_loop().run_in_executor(None, fetch_history_data)

        content_container.clear()
        with content_container:
            if summary_rows:
                ui.label(t('log_weekly_blueprint')).classes('text-[11px] frappe-dark uppercase mb-1 mt-2')
                with ui.column().classes('w-full gap-0.5 mb-4 p-2 bg-neutral-950 text-[11px] mono-card'):
                    for s_row in reversed(summary_rows):
                        hours = s_row['total_sec'] / 3600
                        bars = '■' * min(10, max(1, int(hours * 2)))
                        ui.label(f"{s_row['start_date'][-5:]} | {bars:<10} ({hours:.1f}h)").classes('frappe-dark')

            log_container = ui.column().classes('w-full gap-1 max-h-48 overflow-y-auto mb-4 text-xs text-neutral-400')
            
            with log_container:
                if not rows:
                    ui.label(t('log_no_sessions')).classes('text-xs frappe-muted italic')
                else:
                    with ui.row().classes('w-full justify-between mono-divider pb-1 text-neutral-500 text-[11px]'):
                        ui.label(t('log_col_day')).classes('w-36 frappe-dark')
                        ui.label(t('log_col_sub')).classes('w-24 frappe-dark')
                        ui.label(t('log_col_time')).classes('w-16 text-right frappe-dark')
                    
                    for row in rows:
                        duration_str = statistics.format_duration(row['duration_seconds'])
                        sub_name = row['subject_name'] or "Deleted"
                        
                        try:
                            dt_obj = datetime.datetime.strptime(row['start_date'], '%Y-%m-%d')
                            with _CACHE_LOCK:
                                lang = cached_language
                            if lang == 'pt':
                                day_names = {'Mon': 'Seg', 'Tue': 'Ter', 'Wed': 'Qua', 'Thu': 'Qui', 'Fri': 'Sex', 'Sat': 'Sáb', 'Sun': 'Dom'}
                                day_name = day_names.get(dt_obj.strftime('%a'), '???')
                            else:
                                day_name = dt_obj.strftime('%a')
                        except:
                            day_name = '???'
                            
                        with ui.row().classes('w-full justify-between py-1 border-b border-neutral-950 text-[11px]'):
                            ui.label(f"{row['start_date']} ({day_name})").classes('w-36 frappe-dark')
                            ui.label(sub_name).classes('w-24 truncate frappe-light')
                            ui.label(duration_str).classes('w-16 text-right frappe-light')

        content_container.update()

    def toggle_start_pause():
        status = focus_timer.state.status
        if status in ('idle', 'paused'):
            focus_timer.start()
        elif status == 'running':
            focus_timer.pause()
        update_display()

    async def download_csv_log():
        with _CACHE_LOCK:
            lang = cached_language
        loop = asyncio.get_running_loop()
        csv_data = await loop.run_in_executor(None, statistics.export_history_csv)
        ui.download(csv_data, 'focus_history.csv' if lang == 'en' else 'historico_foco.csv')

    async def manual_rotate():
        """Asynchronously requests a thread-safe weighted subject rotation and updates the view."""
        def b_rotate():
            subjects.rotate_subject()
            refresh_global_cache()
        await asyncio.get_running_loop().run_in_executor(None, b_rotate)
        update_display()

    def update_language_labels():
        """Isolates heavy UI language label updates to avoid WebSocket network spam during timer ticks."""
        weekly_goal_header_label.text = t('main_weekly_goal')
        stats_header_label.text = t('main_stats_title')
        pace_header_label.text = t('main_pace')
        total_hours_header_label.text = t('main_total_hours')
        total_focus_days_header_label.text = t('main_total_days')
        show_more_label.text = t('main_show_more')
        timer_header_label.text = t('main_timer_title')
        pomo_toggle_btn.text = 'Pomodoro'
        stopwatch_toggle_btn.text = t('main_stopwatch')
        today_static_label.text = t('main_today_label')
        skip_btn.text = t('main_skip_break')
        add_suggestion_inline_btn.text = t('main_define_suggestions')

        with _CACHE_LOCK:
            current_auto_rotate = cached_auto_rotate

        if current_auto_rotate:
            suggestion_title_label.text = t('main_suggestion_today')
        else:
            suggestion_title_label.text = t('main_suggestion_current')

        # Push updates down the wire strictly once per invocation
        weekly_goal_header_label.update()
        stats_header_label.update()
        pace_header_label.update()
        total_hours_header_label.update()
        total_focus_days_header_label.update()
        show_more_label.update()
        timer_header_label.update()
        pomo_toggle_btn.update()
        stopwatch_toggle_btn.update()
        today_static_label.update()
        skip_btn.update()
        add_suggestion_inline_btn.update()
        suggestion_title_label.update()

    def update_display():
        """Lean updater responsible only for dynamic timer states and performance-critical metrics."""
        status = focus_timer.state.status

        # Safely capture a snapshot of the current state via Thread Lock
        with _CACHE_LOCK:
            current_stats = cached_stats.copy()
            current_subject = cached_active_subject
            current_goal = cached_weekly_goal_hours
            current_auto_rotate = cached_auto_rotate
            current_language = cached_language

        if status == 'idle':
            start_pause_btn.props("icon=play_arrow")
        elif status == 'running':
            start_pause_btn.props("icon=pause")
        elif status == 'paused':
            start_pause_btn.props("icon=play_arrow")

        is_pomo_mode = focus_timer.state.mode in ('pomodoro', 'break')
        is_stopwatch = focus_timer.state.mode == 'stopwatch'
        is_break = focus_timer.state.mode == 'break'

        if focus_timer.state.mode == 'pomodoro':
            timer_status_label.text = t('main_timer_focus')
            timer_status_label.style('color: #de9c52; background-color: rgba(222, 156, 82, 0.06); border: 0.5px solid #de9c52; padding: 3px 5px 2px 7px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-flex; align-items: center; justify-content: center; border-radius: 2px; line-height: 1; height: 18px;')
            timer_status_label.set_visibility(True)
            mode_label = t('main_timer_focus')
        elif focus_timer.state.mode == 'break':
            timer_status_label.text = t('main_timer_break')
            timer_status_label.style('color: #a3b18a; background-color: rgba(163, 177, 138, 0.06); border: 0.5px solid rgba(163, 177, 138, 0.2); padding: 3px 5px 2px 7px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; display: inline-flex; align-items: center; justify-content: center; border-radius: 2px; line-height: 1; height: 18px;')
            timer_status_label.set_visibility(True)
            mode_label = t('main_timer_break')
        else:
            timer_status_label.set_visibility(False)
            mode_label = t('main_stopwatch')

        timer_label.text = focus_timer.display_time
        ui.page_title(f"{focus_timer.display_time} · {mode_label}")

        skip_btn.set_visibility(is_break)
        reset_btn.set_visibility(is_pomo_mode and status != 'idle')
        stop_btn.set_visibility(is_stopwatch and status != 'idle')

        # FORCE DIRECT INLINE STYLES FOR TOGGLES TO COMPLETELY BYPASS RENDER NETWORK DELAY OVERLAPS
        is_pomo_active = focus_timer.state.mode in ('pomodoro', 'break')
        if is_pomo_active:
            pomo_toggle_btn.style('background-color: #4e3629 !important; color: #ebdcd0 !important; border: 1px solid #4e3629 !important;')
            stopwatch_toggle_btn.style('background-color: transparent !important; color: #59514a !important; border: 1px solid #16100d !important;')
        else:
            pomo_toggle_btn.style('background-color: transparent !important; color: #59514a !important; border: 1px solid #16100d !important;')
            stopwatch_toggle_btn.style('background-color: #4e3629 !important; color: #ebdcd0 !important; border: 1px solid #4e3629 !important;')

        if status == 'idle':
            pomo_toggle_btn.enable()
            stopwatch_toggle_btn.enable()
        else:
            pomo_toggle_btn.disable()
            stopwatch_toggle_btn.disable()

        active_focus_seconds = 0
        if status == 'running':
            active_focus_seconds = focus_timer.state.seconds_focused_in_turn

        goal_seconds = current_goal * 3600

        live_today = current_stats['today'] + active_focus_seconds
        live_week = current_stats['week'] + active_focus_seconds
        live_total = current_stats['total'] + active_focus_seconds

        week_label.text = f"{statistics.format_duration(live_week)} / {current_goal}h"
        total_label.text = statistics.format_duration(live_total)
        
        avg_label.text = f"{current_stats['avg_week_hours']:.1f}{t('main_pace_suffix')}"
        
        live_focus_days = current_stats['focus_days']
        if current_stats['today'] == 0 and active_focus_seconds > 0:
            live_focus_days += 1
        focus_days_label.text = f"{live_focus_days}{t('main_total_days_suffix')}"
        
        today_label.text = statistics.format_duration(live_today)
        
        progress_val = min(1.0, live_week / goal_seconds) if goal_seconds > 0 else 0
        week_progress.value = progress_val

        if current_subject:
            suggestion_val_label.set_visibility(True)
            edit_suggestion_inline_btn.set_visibility(True)
            rotate_suggestion_inline_btn.set_visibility(True)
            add_suggestion_inline_btn.set_visibility(False)
            suggestion_val_label.text = f"{current_subject.name}"
        else:
            suggestion_val_label.set_visibility(False)
            edit_suggestion_inline_btn.set_visibility(False)
            rotate_suggestion_inline_btn.set_visibility(False)
            add_suggestion_inline_btn.set_visibility(True)

        timer_label.update()
        week_label.update()
        total_label.update()
        today_label.update()
        focus_days_label.update()
        suggestion_val_label.update()
        edit_suggestion_inline_btn.update()
        rotate_suggestion_inline_btn.update()
        start_pause_btn.update()
        reset_btn.update()
        stop_btn.update()
        timer_status_label.update()
        week_progress.update()
        avg_label.update()

    # Offload initial database hits into the worker pool execution thread to ensure zero event loop freezes
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: (subjects.ensure_daily_rotation(), refresh_global_cache())
    )
    
    def update_clock():
        now = datetime.datetime.now()
        date_str = now.strftime('%d/%m/%Y')
        with _CACHE_LOCK:
            lang = cached_language
        if lang == 'pt':
            day_names = {
                'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
                'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            day_str = day_names.get(now.strftime('%A'), now.strftime('%A'))
        else:
            day_str = now.strftime('%A')
        time_str = now.strftime('%H:%M')
        clock_label.content = f'<div style="color: #59514a !important;">{date_str} · {day_str} · {time_str}</div>'
        greeting_label.text = get_greeting()
        update_display()

    ui.timer(1.0, update_clock)

    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4').style('background-color: #000000;'):
        
        clock_label = ui.html('').classes('clock-fixed-tint pl-1')
        
        with ui.column().classes('w-full gap-4 p-4 mono-card'):
            
            with ui.row().classes('w-full justify-between items-start text-sm'):
                with ui.column().classes('gap-1'):
                    greeting_label = ui.label('').classes('frappe-light')
                    
                    with ui.row().classes('items-center gap-1.5').style('height: 28px; max-height: 28px;'):
                        # Initialized smoothly using actual localized cache on first render
                        suggestion_title_label = ui.label(t('main_suggestion_today')).classes('frappe-dark text-sm')
                        suggestion_val_label = ui.label('').classes('frappe-light uppercase text-sm')
                        
                        rotate_suggestion_inline_btn = ui.button(icon='autorenew', on_click=manual_rotate).props('flat dense size=sm no-ripple').classes('rotate-main-btn')
                        edit_suggestion_inline_btn = ui.button(icon='edit', on_click=open_suggestions_panel).props('flat dense size=xs no-ripple').classes('edit-pencil-btn')
                        add_suggestion_inline_btn = ui.button(t('main_define_suggestions'), on_click=open_suggestions_panel).classes('inline-mono-btn')
                
                with ui.row().classes('gap-2 items-center'):
                    ui.button(icon='help', on_click=open_help_panel).props('flat dense size=sm color=grey no-ripple').classes('icon-panel-btn')
                    ui.button(icon='settings', on_click=open_settings_panel).props('flat dense size=sm color=grey no-ripple').classes('icon-panel-btn')

            with ui.column().classes('w-full gap-1.5 mt-2'):
                with ui.row().classes('w-full justify-between items-baseline'):
                    weekly_goal_header_label = ui.label(t('main_weekly_goal')).classes('text-xs uppercase tracking-wider frappe-dark')
                    week_label = ui.label('0h 0m / 10h').classes('frappe-light text-sm')
                
                week_progress = ui.linear_progress(value=0.0, show_value=False).classes('w-full').style('height: 14px !important; border-radius: 0px;')

        with ui.row().classes('w-full gap-6 items-stretch'):
            
            with ui.column().classes('p-4 gap-4 relative mono-card').style('flex: 1 1 0; min-width: 320px; min-height: 250px;'):
                with ui.row().classes('w-full justify-between items-center pb-2 mono-divider'):
                    stats_header_label = ui.label(t('main_stats_title')).classes('text-sm uppercase tracking-wider frappe-light')
                
                with ui.column().classes('w-full gap-3 text-sm text-neutral-400'):
                    with ui.column().classes('gap-0'):
                        pace_header_label = ui.label(t('main_pace')).classes('text-sm uppercase tracking-wider frappe-dark')
                        avg_label = ui.label('0.0' + t('main_pace_suffix')).classes('frappe-light text-base')
                        
                    with ui.column().classes('gap-0'):
                        total_hours_header_label = ui.label(t('main_total_hours')).classes('text-sm uppercase tracking-wider frappe-dark')
                        total_label = ui.label('0h 0m').classes('frappe-light text-base')

                    with ui.column().classes('gap-0'):
                        total_focus_days_header_label = ui.label(t('main_total_days')).classes('text-sm uppercase tracking-wider frappe-dark')
                        focus_days_label = ui.label('0' + t('main_total_days_suffix')).classes('frappe-light text-base')
                
                show_more_label = ui.label(t('main_show_more')).on('click', open_history_panel).classes('absolute bottom-4 left-4 cursor-pointer text-xs uppercase tracking-wider transition-colors blue-link')

            with ui.column().classes('p-4 gap-4 items-center justify-start relative mono-card').style('flex: 1 1 0; min-width: 320px; min-height: 250px;'):
                with ui.row().classes('w-full items-center pb-2 relative').style('height: 32px; min-height: 32px; max-height: 32px; border-bottom: 1px solid #16100d;'):
                    timer_header_label = ui.label(t('main_timer_title')).classes('text-sm uppercase tracking-wider frappe-light')
                    with ui.row().classes('absolute right-0 top-0 bottom-2 items-center'):
                        timer_status_label = ui.label('[Focus]').classes('rounded-none font-mono')
                
                with ui.row().classes('mt-1 gap-0 justify-center items-center'):
                    pomo_toggle_btn = ui.button('Pomodoro', on_click=lambda: (focus_timer.set_mode('Pomodoro'), update_display())).props('flat dense no-ripple').classes('toggle-btn-pomo')
                    stopwatch_toggle_btn = ui.button(t('main_stopwatch'), on_click=lambda: (focus_timer.set_mode('Stopwatch'), update_display())).props('flat dense no-ripple').classes('toggle-btn-sw')
                
                with ui.column().classes('w-full items-center mt-1'):
                    timer_label = ui.label(focus_timer.display_time).classes('text-5xl frappe-light tracking-normal')
                    
                    with ui.row().classes('gap-1.5 h-10 items-center justify-center w-full'):
                        start_pause_btn = ui.button(on_click=toggle_start_pause).classes('timer-btn').props('flat round size=md no-ripple')
                        reset_btn = ui.button(on_click=lambda: (focus_timer.reset(), update_display())).classes('timer-btn').props('flat round icon=refresh size=md no-ripple')
                        stop_btn = ui.button(on_click=lambda: (focus_timer.stop(), update_display())).classes('timer-btn').props('flat round icon=stop size=md no-ripple')

                with ui.row().classes('w-full items-center gap-1.5 mt-auto pt-2').style('border-top: 1px solid #16100d;'):
                    today_static_label = ui.label(t('main_today_label')).classes('text-xs uppercase tracking-wider frappe-dark')
                    today_label = ui.label('0h 0m').classes('text-xs frappe-light')

                skip_btn = ui.label(t('main_skip_break')).on('click', lambda: (focus_timer.skip(), update_display())).classes('absolute bottom-2 right-4 cursor-pointer text-xs uppercase tracking-wider transition-colors skip-btn-custom')

    update_clock()
    update_display()
