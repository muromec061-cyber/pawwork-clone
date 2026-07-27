#!/usr/bin/env python3
"""
PawWork Clone v4.0  —  GitHub Actions Agent с многолетним дизайном.
Вдохновлён архитектурой «三省六部» (edict): многоагентное мышление,
ролевая обработка задач, разделение полномочий.

Архитектура агентов (edict-style):
  👑 ТЫ (пользователь) → 太子(Маршрутизация) → 中书省(Планирование)
  → 门下省(Проверка) → 六部(Исполнение) → Ответ

Как работает:
  1. GitHub Actions запускает скрипт каждые 5 минут
  2. Проверяет Telegram на новые сообщения
  3. Маршрутизирует запрос через систему агентов
  4. Создаёт файлы, код, деплоит через GitHub API
  5. Отвечает в Telegram с красивыми инлайн-кнопками
"""

import os, sys, json, time, re, urllib.request, urllib.parse, urllib.error, base64
from datetime import datetime
import html as html_mod  # для экранирования HTML в AI-ответах

# ── КОНФИГУРАЦИЯ ───────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
API_KEY = os.environ.get("PAWWORK_API_KEY", "sk-pawwork-demo")
STORAGE_REPO = os.environ.get("STORAGE_REPO", "muromec061-cyber/pawwork-clone")
OWNER, REPO = STORAGE_REPO.split("/") if "/" in STORAGE_REPO else ("muromec061-cyber", "pawwork-clone")
BOT_USERNAME = "@Gptzloy_bot"  # Токен: 8961572816:AAHYo4_gGmBHbrUiFokHl7UJJzGifh61_aU

# ── СТИЛИ ──────────────────────────────────────────────────────
STYLES = {
    "header": "🤖",
    "agent": "⚔️",
    "done": "✅",
    "code": "💻",
    "search": "🔍",
    "file": "📁",
    "brain": "🧠",
    "settings": "⚙️",
    "help": "❓",
    "warning": "⚠️",
    "error": "❌",
    "star": "⭐",
}

# ── HELPERS ─────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def gh_api(method, path, body=None):
    """Вызов GitHub API."""
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "pawwork-clone",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return json.loads(err)
        except:
            return {"error": err, "status": e.code}
    except Exception as e:
        return {"error": str(e)}

def tg_api(method, payload):
    """Вызов Telegram API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"tg_api error: {e}")
        return {"ok": False}

def html_escape(text):
    """Экранировать HTML-символы для безопасной отправки в Telegram parse_mode=HTML."""
    return html_mod.escape(text, quote=False)

def send_message(chat_id, text, parse_mode="HTML", reply_markup=None):
    """Отправить сообщение в Telegram с опциональными кнопками."""
    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = tg_api("sendMessage", payload)
    if not result.get("ok"):
        # Если HTML не прошёл, пробуем без разметки
        if parse_mode == "HTML":
            payload["text"] = html_escape(text[:4000])
            payload["parse_mode"] = "HTML"
            result = tg_api("sendMessage", payload)
            if not result.get("ok"):
                # Если всё ещё не работает — plain text
                payload.pop("parse_mode", None)
                result = tg_api("sendMessage", payload)
    return result

def edit_message(chat_id, msg_id, text, parse_mode="HTML", reply_markup=None):
    """Редактировать сообщение."""
    payload = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text[:4000],
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_api("editMessageText", payload)

def answer_callback(callback_id, text):
    """Ответить на callback (убирает "часики" на кнопке)."""
    return tg_api("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": False,
    })

# ── КНОПКИ ──────────────────────────────────────────────────────

def main_menu():
    """Главное меню с инлайн-кнопками."""
    return {
        "inline_keyboard": [
            [
                {"text": "💬 Чат с AI", "callback_data": "mode_chat"},
                {"text": "💻 Создать код", "callback_data": "mode_code"},
            ],
            [
                {"text": "🔍 Поиск", "callback_data": "mode_search"},
                {"text": "📁 Файлы", "callback_data": "mode_files"},
            ],
            [
                {"text": "⚔️ Агенты", "callback_data": "mode_agents"},
                {"text": "❓ Помощь", "callback_data": "mode_help"},
            ],
            [
                {"text": "⚙️ Настройки", "callback_data": "mode_settings"},
            ],
        ]
    }

def mode_menu(mode_name, mode_emoji):
    """Меню для конкретного режима."""
    return {
        "inline_keyboard": [
            [
                {"text": "🏠 Главное меню", "callback_data": "menu_main"},
                {"text": "❓ Помощь", "callback_data": "mode_help"},
            ],
            [
                {"text": "📝 Новый запрос", "callback_data": f"mode_{mode_name}"},
                {"text": "🔄 Очистить историю", "callback_data": "action_clear"},
            ],
        ]
    }

def agents_menu():
    """Меню мульти-агентной системы."""
    return {
        "inline_keyboard": [
            [
                {"text": "👑 Маршрутизатор", "callback_data": "agent_router"},
                {"text": "📜 Планировщик", "callback_data": "agent_planner"},
            ],
            [
                {"text": "🔍 Проверяющий", "callback_data": "agent_reviewer"},
                {"text": "💻 Исполнитель", "callback_data": "agent_executor"},
            ],
            [
                {"text": "🏠 Главное меню", "callback_data": "menu_main"},
            ],
        ]
    }

# ── AI INFERENCE ───────────────────────────────────────────────

def ask_github_models(messages):
    """Запрос к GitHub Models API (бесплатно, через GitHub токен)."""
    url = "https://models.github.ai/inference/chat/completions"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }
    body = json.dumps({
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3,
    }).encode()
    
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"[GitHub Models Error: {e}]"

def ask_groq(messages):
    """Запрос к Groq API (если есть ключ)."""
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3,
    }).encode()
    
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except:
        return None

def ask_ai(messages):
    """AI с авто-fallback: Groq → GitHub Models."""
    result = ask_groq(messages)
    if result and not result.startswith("["):
        return result, "groq"
    result = ask_github_models(messages)
    return result, "github-models"

# ── МНОГОАГЕНТНАЯ СИСТЕМА (вдохновлено edict 三省六部) ────────

AGENT_SYSTEM_PROMPT = """Ты — PawWork Clone v4, многоагентная AI-система в стиле «三省六部».

АРХИТЕКТУРА АГЕНТОВ:
  👑 太子 (Taizi)     — Маршрутизация: определяет тип запроса
  📜 中书省 (Zhongshu) — Планирование: разбивает задачу на шаги
  🔍 门下省 (Menxia)   — Проверка: оценивает качество и риски
  💻 六部 (Liubu)      — Исполнение: создаёт код, файлы, ищет информацию
  📮 尚书省 (Shangshu) — Сборка: собирает ответ и отправляет пользователю

ПРОЦЕСС ОБРАБОТКИ:
  1. 太子 получает запрос и определяет его тип:
     - chat → обычный диалог (ответ сразу)
     - code → задача на код (→中书省)
     - search → поиск информации (→六部)
     - task → сложная задача (→中书省→门下省→六部)
  2. 中书省 разбивает задачу на шаги
  3. 门下省 проверяет план
  4. 六部 выполняет работу
  5. 尚书省 собирает ответ

ОТВЕЧАЙ В ЭТОМ ФОРМАТЕ:
━━━━━━━━━━━━━━━━━━━━━━━━
👑 [太子] → chat/code/search/task
📜 [План] → шаги выполнения
━━━━━━━━━━━━━━━━━━━━━━━━
[ОСНОВНОЙ ОТВЕТ]
━━━━━━━━━━━━━━━━━━━━━━━━
⚡ GitHub Models | 🕐 время

ВАЖНО:
- Отвечай НА РУССКОМ
- Всегда показывай какой агент обрабатывает
- Если нужно создать файл → используй ACTION: create_file
- Если нужно искать → используй ACTION: web_search
- Будь конкретным, давай готовые решения"""

TOOLS_DESC = """
ИНСТРУМЕНТЫ:
create_file(path, content) — создать файл в GitHub
web_search(query) — поиск в интернете
get_time() — текущее время
run_python(code) — выполнить Python код
memory_get(key) — прочитать из памяти
memory_set(key=value) — записать в память
finish(answer) — завершить

ФОРМАТ ИНСТРУМЕНТОВ:
THOUGHT: что думаешь
ACTION: create_file
ACTION_INPUT: путь/к/файлу.py
содержимое файла
"""

# ── ХРАНИЛИЩЕ ──────────────────────────────────────────────────

def load_json(path):
    """Загрузить JSON из файла в репозитории."""
    result = gh_api("GET", f"/repos/{OWNER}/{REPO}/contents/{path}")
    if "content" in result:
        try:
            content = base64.b64decode(result["content"]).decode()
            return json.loads(content), result["sha"]
        except:
            return {}, None
    return {}, None

def save_json(path, data, sha=None):
    """Сохранить JSON в файл в репозитории."""
    content = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
    body = {"message": f"Update {path}", "content": content}
    if sha:
        body["sha"] = sha
    result = gh_api("PUT", f"/repos/{OWNER}/{REPO}/contents/{path}", body)
    return "content" in result

def create_file(path, content):
    """Создать файл в репозитории."""
    b64 = base64.b64encode(content.encode()).decode()
    result = gh_api("PUT", f"/repos/{OWNER}/{REPO}/contents/{path}", {
        "message": f"Create {path} via PawWork Agent",
        "content": b64,
    })
    return result.get("content", {}).get("html_url", path)

def list_files():
    """Список файлов в корне репозитория."""
    result = gh_api("GET", f"/repos/{OWNER}/{REPO}/contents/")
    if isinstance(result, list):
        return [f["name"] for f in result if f["type"] == "file"]
    return []

# ── ОБРАБОТКА СООБЩЕНИЙ ───────────────────────────────────────

def process_message(chat_id, text, history, mode="auto"):
    """Обработать сообщение через AI с учётом режима."""
    log(f"Processing [{mode}]: {text[:50]}...")
    
    # Печатает...
    tg_api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
    
    # Промпт в зависимости от режима
    if mode == "code":
        system_prompt = AGENT_SYSTEM_PROMPT.replace(
            "обычный диалог (ответ сразу)",
            "создание кода (приоритет)"
        )
        system_prompt += "\n\nСЕЙЧАС РЕЖИМ: 💻 СОЗДАНИЕ КОДА\nПиши полный, рабочий код с нуля."
    elif mode == "search":
        system_prompt = AGENT_SYSTEM_PROMPT
        system_prompt += "\n\nСЕЙЧАС РЕЖИМ: 🔍 ПОИСК\nИспользуй web_search для поиска, потом обработай результаты."
    elif mode == "agent":
        system_prompt = AGENT_SYSTEM_PROMPT
        system_prompt += "\n\nСЕЙЧАС РЕЖИМ: ⚔️ АГЕНТЫ\nПодробно опиши какой агент выполняет каждый шаг."
    else:
        system_prompt = AGENT_SYSTEM_PROMPT
    
    # Формируем сообщения
    messages = [{"role": "system", "content": system_prompt + TOOLS_DESC}]
    
    for msg in history[-8:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": text})
    
    # Запускаем AI
    response, provider = ask_ai(messages)
    
    if not response:
        return "Извини, все AI провайдеры временно недоступны. Попробуй позже."
    
    # Парсим действия агента
    action_match = re.search(r'ACTION:\s*(\w+)', response)
    action_input_match = re.search(r'ACTION_INPUT:\s*(.*?)(?:\n|$)', response)
    
    if action_match:
        action = action_match.group(1).strip().lower()
        action_input = action_input_match.group(1).strip() if action_input_match else ""
        
        if action == "create_file":
            lines = action_input.split("\n", 1)
            path = lines[0].strip() if lines else "output.txt"
            content = lines[1] if len(lines) > 1 else ""
            
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
            
            url = create_file(path, content)
            response += f"\n\n{STYLES['done']} Файл создан: <code>{path}</code>\n<a href='{url}'>Открыть на GitHub</a>"
        
        elif action == "web_search":
            search_result = web_search(action_input)
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Результаты поиска по запросу '{action_input}':\n{search_result[:2000]}\n\nОбработай результаты и ответь пользователю."})
            response, _ = ask_ai(messages)
        
        elif action == "get_time":
            response += f"\n\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        
        elif action == "run_python":
            try:
                code = re.sub(r'^```\w*\n?', '', action_input)
                code = re.sub(r'\n?```$', '', code)
                local_vars = {}
                exec(code, {"__builtins__": __builtins__}, local_vars)
                output = str(local_vars.get("result", "Код выполнен"))
                response += f"\n\n{STYLES['code']} Результат: <code>{output[:500]}</code>"
            except Exception as e:
                response += f"\n\n{STYLES['error']} Ошибка: {e}"
        
        elif action == "memory_get":
            key = action_input.strip()
            val = history_store.get(key, "(пусто)")
            response += f"\n\n📝 {key}: {val}"
        
        elif action == "memory_set":
            parts = action_input.split("=", 1)
            if len(parts) == 2:
                history_store[parts[0].strip()] = parts[1].strip()
                response += "\n\n✅ Сохранено"
    
    # Футер
    provider_icon = "⚡" if "github" in provider else "⚡"
    response += f"\n\n<small>{provider_icon} {provider} · 🕐 {datetime.now().strftime('%H:%M')}</small>"
    
    return response

def web_search(query):
    """Поиск в DuckDuckGo."""
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode()
            results = re.findall(r'<a[^>]*class="result-link"[^>]*>(.*?)</a>', html)
            return "\n".join(r.strip() for r in results[:5])[:2000] or "Нет результатов"
    except Exception as e:
        return f"Ошибка поиска: {e}"

# ── ОБРАБОТЧИКИ РЕЖИМОВ ────────────────────────────────────────

def get_welcome_message():
    """Приветственное сообщение с меню."""
    return (
        f"{STYLES['brain']} <b>PawWork Clone v4.0</b>\n"
        f"Многоагентная AI-система в стиле «三省六部»\n\n"
        f"{STYLES['agent']} <b>Архитектура агентов:</b>\n"
        f"👑 太子 → 📜 中书省 → 🔍 门下省 → 💻 六部\n\n"
        f"Работает 24/7 • Бесплатно • GitHub Models\n"
        f"Выбери режим ниже:"
    )

def get_help_text():
    """Справка по командам."""
    return (
        f"{STYLES['help']} <b>Помощь по PawWork Clone</b>\n\n"
        f"<b>Режимы:</b>\n"
        f"💬 <b>Чат с AI</b> — обычный диалог\n"
        f"💻 <b>Создать код</b> — написать программу\n"
        f"🔍 <b>Поиск</b> — найти информацию\n"
        f"📁 <b>Файлы</b> — управление файлами\n"
        f"⚔️ <b>Агенты</b> — многоагентная система\n\n"
        f"<b>Команды:</b>\n"
        f"/start — главное меню\n"
        f"/help — эта справка\n"
        f"/chat — режим чата\n"
        f"/code — режим кода\n"
        f"/search — режим поиска\n"
        f"/agents — режим агентов\n"
        f"/clear — очистить историю\n\n"
        f"<b>Бот:</b> {BOT_USERNAME}\n"
        f"<b>Провайдер:</b> GitHub Models (GPT-4o бесплатно)"
    )

def get_agents_text():
    """Описание многоагентной системы."""
    return (
        f"{STYLES['agent']} <b>Многоагентная система «三省六部»</b>\n\n"
        f"<b>👑 太子 (Taizi)</b> — Маршрутизация\n"
        f"Определяет тип запроса и направляет нужному агенту\n\n"
        f"<b>📜 中书省 (Zhongshu)</b> — Планирование\n"
        f"Разбивает сложные задачи на выполнимые шаги\n\n"
        f"<b>🔍 门下省 (Menxia)</b> — Проверка\n"
        f"Оценивает качество плана, может отправить на доработку\n\n"
        f"<b>💻 六部 (Liubu)</b> — Исполнение\n"
        f"Пишет код, создаёт файлы, ищет информацию\n\n"
        f"<b>📮 尚书省 (Shangshu)</b> — Сборка\n"
        f"Собирает результаты в готовый ответ\n\n"
        f"<i>Вдохновлено проектом edict (github.com/cft0808/edict)</i>"
    )

def get_files_text():
    """Список файлов в репозитории."""
    files = list_files()
    if not files:
        return f"{STYLES['file']} <b>Файлы в репозитории</b>\n\n(нет файлов или ошибка доступа)"
    
    text = f"{STYLES['file']} <b>Файлы в репозитории:</b>\n\n"
    for f in files[:30]:
        text += f"📄 <code>{f}</code>\n"
    text += f"\nВсего: {len(files)} файлов"
    return text

def get_settings_text(chat_id):
    """Настройки пользователя."""
    user_settings = settings_store.get(str(chat_id), {})
    mode = user_settings.get("mode", "auto")
    return (
        f"{STYLES['settings']} <b>Настройки</b>\n\n"
        f"Режим по умолчанию: <b>{mode}</b>\n"
        f"Провайдер: <b>GitHub Models</b> (GPT-4o)\n"
        f"Хранилище: <b>{OWNER}/{REPO}</b>\n"
        f"Бот: {BOT_USERNAME}\n\n"
        f"Используй кнопки меню для смены режима."
    )

# ── ОБРАБОТКА КНОПОК ──────────────────────────────────────────

def handle_callback(callback):
    """Обработать нажатие инлайн-кнопки."""
    cb_data = callback.get("data", "")
    cb_id = callback.get("id", "")
    msg = callback.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")
    user = callback.get("from", {})
    user_id = user.get("id")
    username = user.get("first_name", "Пользователь")
    
    log(f"🔘 Callback: {cb_data} от {username}")
    
    # Ответ на callback (убираем часики)
    answer_callback(cb_id, f"→ {cb_data}")
    
    if cb_data == "menu_main":
        edit_message(chat_id, msg_id, get_welcome_message(), reply_markup=main_menu())
        
    elif cb_data == "mode_help":
        edit_message(chat_id, msg_id, get_help_text(), reply_markup=mode_menu("help", STYLES["help"]))
    
    elif cb_data == "mode_chat":
        edit_message(chat_id, msg_id,
            f"{STYLES['brain']} <b>Режим: Чат с AI</b>\n\n"
            f"Просто напиши сообщение — я отвечу как AI-ассистент.\n"
            f"Работает через многоагентную систему 三省六部.",
            reply_markup=mode_menu("chat", STYLES["brain"]))
        # Устанавливаем режим
        if str(chat_id) not in settings_store:
            settings_store[str(chat_id)] = {}
        settings_store[str(chat_id)]["mode"] = "chat"
    
    elif cb_data == "mode_code":
        edit_message(chat_id, msg_id,
            f"{STYLES['code']} <b>Режим: Создание кода</b>\n\n"
            f"Опиши, что нужно написать. Я создам:\n"
            f"• Python, JS, HTML, C++, Go, Rust\n"
            f"• Telegram ботов, веб-приложения, CLI\n"
            f"• Скрипты, утилиты, API\n\n"
            f"Файлы сохраняются в GitHub репозиторий.",
            reply_markup=mode_menu("code", STYLES["code"]))
        if str(chat_id) not in settings_store:
            settings_store[str(chat_id)] = {}
        settings_store[str(chat_id)]["mode"] = "code"
    
    elif cb_data == "mode_search":
        edit_message(chat_id, msg_id,
            f"{STYLES['search']} <b>Режим: Поиск</b>\n\n"
            f"Напиши поисковый запрос — я найду информацию "
            f"в интернете и обработаю результаты.",
            reply_markup=mode_menu("search", STYLES["search"]))
        if str(chat_id) not in settings_store:
            settings_store[str(chat_id)] = {}
        settings_store[str(chat_id)]["mode"] = "search"
    
    elif cb_data == "mode_files":
        text = get_files_text()
        edit_message(chat_id, msg_id, text, reply_markup=mode_menu("files", STYLES["file"]))
    
    elif cb_data == "mode_agents":
        edit_message(chat_id, msg_id, get_agents_text(), reply_markup=agents_menu())
    
    elif cb_data == "mode_settings":
        text = get_settings_text(chat_id)
        edit_message(chat_id, msg_id, text, reply_markup={
            "inline_keyboard": [
                [{"text": "🔄 Сбросить режим", "callback_data": "action_reset_mode"}],
                [{"text": "🏠 Главное меню", "callback_data": "menu_main"}],
            ]
        })
    
    elif cb_data == "action_clear":
        if str(chat_id) in chat_history:
            chat_history[str(chat_id)] = []
        edit_message(chat_id, msg_id,
            f"{STYLES['done']} История очищена!",
            reply_markup=mode_menu("chat", STYLES["brain"]))
    
    elif cb_data == "action_reset_mode":
        if str(chat_id) in settings_store:
            settings_store[str(chat_id)]["mode"] = "auto"
        edit_message(chat_id, msg_id,
            f"{STYLES['done']} Режим сброшен на автоматический.",
            reply_markup=main_menu())
    
    elif cb_data == "agent_router":
        edit_message(chat_id, msg_id,
            f"👑 <b>太子 (Taizi) — Маршрутизатор</b>\n\n"
            f"Определяет тип запроса:\n"
            f"• 💬 Вопрос → отправляет в чат\n"
            f"• 💻 Код → отправляет 中书省\n"
            f"• 🔍 Поиск → отправляет 六部\n"
            f"• 📋 Задача → запускает полный цикл\n\n"
            f"<i>Напиши сообщение — 太子 обработает его автоматически.</i>",
            reply_markup=agents_menu())
    
    elif cb_data == "agent_planner":
        edit_message(chat_id, msg_id,
            f"📜 <b>中书省 (Zhongshu) — Планировщик</b>\n\n"
            f"Разбивает сложные задачи на шаги:\n"
            f"1. Анализ требований\n"
            f"2. Декомпозиция на подзадачи\n"
            f"3. Определение порядка выполнения\n"
            f"4. Оценка ресурсов\n\n"
            f"<i>Используется автоматически для сложных задач.</i>",
            reply_markup=agents_menu())
    
    elif cb_data == "agent_reviewer":
        edit_message(chat_id, msg_id,
            f"🔍 <b>门下省 (Menxia) — Проверяющий</b>\n\n"
            f"Оценивает качество:\n"
            f"• Проверка плана на полноту\n"
            f"• Выявление рисков\n"
            f"• Контроль качества кода\n"
            f"• Отправка на доработку при необходимости\n\n"
            f"<i>Это архитектурный слой контроля, работающий автоматически.</i>",
            reply_markup=agents_menu())
    
    elif cb_data == "agent_executor":
        edit_message(chat_id, msg_id,
            f"💻 <b>六部 (Liubu) — Исполнитель</b>\n\n"
            f"Выполняет работу:\n"
            f"• 💰 户部 — данные и ресурсы\n"
            f"• 📝 礼部 — документация\n"
            f"• ⚔️ 兵部 — код и инженерия\n"
            f"• ⚖️ 刑部 — безопасность\n"
            f"• 🔧 工部 — инфраструктура\n\n"
            f"<i>Напиши задачу — и агенты приступят к работе.</i>",
            reply_markup=agents_menu())

# ── POLLING LOOP (мгновенные ответы) ─────────────────────────

POLL_DURATION = 280  # секунд активного long polling (5 мин - запас на коммит)

def poll_telegram():
    """
    Long-polling цикл с мгновенными ответами.
    Вместо одного быстрого опроса — висит ~5 минут с Telegram long polling (timeout=30).
    Когда приходит сообщение — отвечает МГНОВЕННО (Telegram присылает его сразу).
    """
    log("🔍 Запуск long-polling на 5 минут...")
    
    # Загружаем начальное состояние
    state, state_sha = load_json("agent_state.json")
    offset = state.get("last_update_id", 0) + 1
    
    global chat_history, settings_store, history_store
    chat_history, _ = load_json("chat_history.json")
    settings_store, _ = load_json("settings.json")
    history_store = {}
    
    if not chat_history:
        chat_history = {}
    if not settings_store:
        settings_store = {}
    
    deadline = time.time() + POLL_DURATION
    poll_count = 0
    
    while time.time() < deadline:
        remaining = int(deadline - time.time())
        poll_timeout = min(45, max(10, remaining))
        poll_count += 1
        
        # Long polling: запрос висит до 45 секунд, ждёт сообщение
        result = tg_api("getUpdates", {
            "offset": offset,
            "timeout": poll_timeout,
            "allowed_updates": ["message", "callback_query"],
        })
        
        if not result.get("ok"):
            log(f"❌ Telegram API error: {result}")
            time.sleep(5)
            continue
        
        updates = result.get("result", [])
        
        if not updates:
            continue  # просто таймаут, идём дальше
        
        # Сообщения пришли — обрабатываем мгновенно
        for update in updates:
            update_id = update["update_id"]
            offset = update_id + 1
            state["last_update_id"] = update_id
            
            # Callback (нажатие кнопки)
            if "callback_query" in update:
                handle_callback(update["callback_query"])
                continue
            
            # Текстовое сообщение
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "").strip()
            
            if not chat_id or not text:
                continue
            
            log(f"📨 Сообщение от {chat_id}: {text[:50]}...")
            
            # Команды
            if text.startswith("/"):
                cmd = text.split()[0].lower()
                log(f"📋 Команда: {cmd}")
                sent = False
                
                if cmd == "/start":
                    sent = send_message(chat_id, get_welcome_message(), reply_markup=main_menu()).get("ok", False)
                elif cmd == "/help":
                    sent = send_message(chat_id, get_help_text(), reply_markup=mode_menu("help", STYLES["help"])).get("ok", False)
                elif cmd == "/chat":
                    settings_store.setdefault(str(chat_id), {})["mode"] = "chat"
                    sent = send_message(chat_id, f"{STYLES['brain']} <b>Режим: Чат</b>\nНапиши что-нибудь!", reply_markup=mode_menu("chat", STYLES["brain"])).get("ok", False)
                elif cmd == "/code":
                    settings_store.setdefault(str(chat_id), {})["mode"] = "code"
                    sent = send_message(chat_id, f"{STYLES['code']} <b>Режим: Код</b>\nОпиши, что нужно создать.", reply_markup=mode_menu("code", STYLES["code"])).get("ok", False)
                elif cmd == "/search":
                    settings_store.setdefault(str(chat_id), {})["mode"] = "search"
                    sent = send_message(chat_id, f"{STYLES['search']} <b>Режим: Поиск</b>\nНапиши запрос.", reply_markup=mode_menu("search", STYLES["search"])).get("ok", False)
                elif cmd == "/agents":
                    sent = send_message(chat_id, get_agents_text(), reply_markup=agents_menu()).get("ok", False)
                elif cmd == "/clear":
                    chat_history[str(chat_id)] = []
                    sent = send_message(chat_id, f"{STYLES['done']} История очищена!", reply_markup=mode_menu("chat", STYLES["brain"])).get("ok", False)
                elif cmd == "/settings":
                    sent = send_message(chat_id, get_settings_text(chat_id), reply_markup={"inline_keyboard": [[{"text": "🔄 Сбросить режим", "callback_data": "action_reset_mode"}], [{"text": "🏠 Главное меню", "callback_data": "menu_main"}]]}).get("ok", False)
                else:
                    sent = send_message(chat_id, f"{STYLES['warning']} Неизвестная команда. Используй /help", reply_markup=main_menu()).get("ok", False)
                
                log(f"📨 Ответ: {'✅' if sent else '❌'}")
                continue
            
            # Обычное сообщение — через AI
            mode = settings_store.get(str(chat_id), {}).get("mode", "auto")
            
            if str(chat_id) not in chat_history:
                chat_history[str(chat_id)] = []
            
            # Авто-определение режима
            if mode == "auto":
                if any(kw in text.lower() for kw in ["напиши код", "создай", "напиши программу", "сделай сайт", "напиши бота", "напиши скрипт", "создай файл", "напиши функцию"]):
                    mode = "code"
                elif any(kw in text.lower() for kw in ["найди", "поищи", "поиск", "найти", "сколько", "кто такой", "что такое"]):
                    mode = "search"
                elif any(kw in text.lower() for kw in ["агент", "многоагент", "三省六部", "edict"]):
                    mode = "agent"
            
            response = process_message(chat_id, text, chat_history[str(chat_id)], mode)
            
            chat_history[str(chat_id)].append({"role": "user", "content": text})
            chat_history[str(chat_id)].append({"role": "assistant", "content": response[:500]})
            
            if len(chat_history[str(chat_id)]) > 20:
                chat_history[str(chat_id)] = chat_history[str(chat_id)][-20:]
            
            send_message(chat_id, response, reply_markup={
                "inline_keyboard": [[{"text": "🏠 Главное меню", "callback_data": "menu_main"}]]
            })
            log(f"✅ Ответ отправлен")
        
        # Сохраняем состояние после каждой пачки обновлений
        save_json("agent_state.json", state, state_sha)
        save_json("chat_history.json", chat_history)
        save_json("settings.json", settings_store)
        # Обновляем sha после записи
        state, state_sha = load_json("agent_state.json")
        
        log(f"💾 Состояние сохранено (итерация {poll_count})")
    
    # Финальное сохранение
    save_json("agent_state.json", state, state_sha)
    save_json("chat_history.json", chat_history)
    save_json("settings.json", settings_store)
    log(f"🏁 Long-polling завершён ({poll_count} итераций)")

# ── MAIN ──────────────────────────────────────────────────────

if __name__ == "__main__":
    log("🐾 PawWork Clone Agent v4.0 — 三省六部")
    log(f"   Storage: {OWNER}/{REPO}")
    log(f"   Bot: {BOT_USERNAME}")
    
    if not TELEGRAM_TOKEN:
        log("❌ TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    if not GITHUB_TOKEN:
        log("❌ GITHUB_TOKEN не задан!")
        sys.exit(1)
    
    # Глобальные хранилища
    chat_history = {}
    settings_store = {}
    history_store = {}
    
    poll_telegram()
    
    log("🏁 Готово")
