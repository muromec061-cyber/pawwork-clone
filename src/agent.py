#!/usr/bin/env python3
"""
PawWork Clone — GitHub Actions Agent.
Бесплатный AI агент 24/7 на чистом GitHub.

Как работает:
1. GitHub Actions запускает этот скрипт каждые 5 минут
2. Он проверяет Telegram на новые сообщения
3. Обрабатывает их через GitHub Models API (бесплатно)
4. Создаёт файлы, код, деплоит — всё через GitHub API
5. Отвечает в Telegram
"""

import os, sys, json, time, re, urllib.request, urllib.parse, urllib.error, base64
from datetime import datetime

# ── КОНФИГУРАЦИЯ (через secrets GitHub) ──────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
# GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")  # раскомментировать если будет Groq ключ
API_KEY = os.environ.get("PAWWORK_API_KEY", "sk-pawwork-demo")
STORAGE_REPO = os.environ.get("STORAGE_REPO", "muromec061-cyber/pawwork-clone")
OWNER, REPO = STORAGE_REPO.split("/") if "/" in STORAGE_REPO else ("muromec061-cyber", "pawwork-clone")

# ── HELPERS ───────────────────────────────────────────────────

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
    except:
        return {"ok": False}

def send_message(chat_id, text, parse_mode="HTML"):
    """Отправить сообщение в Telegram."""
    return tg_api("sendMessage", {
        "chat_id": chat_id,
        "text": text[:4000],
        "parse_mode": parse_mode,
    })

def edit_message(chat_id, msg_id, text):
    """Редактировать сообщение."""
    return tg_api("editMessageText", {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text[:4000],
        "parse_mode": "HTML",
    })

# ── AI INFERENCE ──────────────────────────────────────────────

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
    # Сначала пробуем Groq (быстрее)
    result = ask_groq(messages)
    if result and not result.startswith("[") :
        return result, "groq"
    # Fallback на GitHub Models
    result = ask_github_models(messages)
    return result, "github-models"

# ── ХРАНИЛИЩЕ (GitHub Repo как база данных) ──────────────────

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

# ── АГЕНТ ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """Ты — PawWork Clone, персональный AI-агент пользователя.

ТЫ МОЖЕШЬ:
1. Писать код на любом языке (Python, JS, HTML, C++, Go, Rust)
2. Создавать приложения (веб, Telegram боты, CLI, API)
3. Создавать файлы с кодом и сохранять их
4. Деплоить на GitHub Pages
5. Искать информацию в интернете
6. Анализировать данные

Отвечай НА РУССКОМ. Будь полезным, конкретным.
Если нужно создать код — пиши полный рабочий код сразу.
Используй инструменты когда нужно."""

TOOLS_DESC = """
ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
1. create_file(path, content) — создать файл с кодом в GitHub репозитории
2. web_search(query) — поиск в интернете
3. get_time() — текущее время
4. run_python(code) — выполнить Python код
5. memory_get(key) — прочитать из памяти
6. memory_set(key=value) — записать в память
7. finish(answer) — завершить

ФОРМАТ:
THOUGHT: что думаешь
ACTION: инструмент
ACTION_INPUT: аргументы
"""

def process_message(chat_id, text, history):
    """Обработать одно сообщение через AI агента."""
    log(f"Processing: {text[:50]}...")
    
    # Отправляем "печатает..."
    tg_api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
    
    # Формируем промпт
    messages = [{"role": "system", "content": SYSTEM_PROMPT + TOOLS_DESC}]
    
    # Добавляем историю (последние 6 сообщений)
    for msg in history[-6:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": text})
    
    # Запускаем агента
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
            
            # Очищаем от ``` и markdown
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
            
            url = create_file(path, content)
            response += f"\n\n✅ Файл создан: {url}"
        
        elif action == "web_search":
            search_result = web_search(action_input)
            # Отправляем результат обратно агенту для обработки
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Результаты поиска: {search_result[:2000]}\n\nОбработай результаты и ответь пользователю. ACTION: finish"})
            response, _ = ask_ai(messages)
        
        elif action == "get_time":
            response += f"\n\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        
        elif action == "run_python":
            try:
                # Очищаем код от markdown
                code = re.sub(r'^```\w*\n?', '', action_input)
                code = re.sub(r'\n?```$', '', code)
                local_vars = {}
                exec(code, {"__builtins__": __builtins__}, local_vars)
                output = str(local_vars.get("result", "Код выполнен"))
                response += f"\n\n💻 Результат: {output[:500]}"
            except Exception as e:
                response += f"\n\n❌ Ошибка: {e}"
        
        elif action == "memory_get":
            key = action_input.strip()
            val = history_store.get(key, "(пусто)")
            response += f"\n\n📝 {key}: {val}"
        
        elif action == "memory_set":
            parts = action_input.split("=", 1)
            if len(parts) == 2:
                history_store[parts[0].strip()] = parts[1].strip()
                response += "\n\n✅ Сохранено"
    
    # Добавляем футер с источником
    if "github" in provider:
        response += "\n\n<small>⚡ GitHub Models</small>"
    else:
        response += f"\n\n<small>⚡ {provider}</small>"
    
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

# ── POLLING LOOP ──────────────────────────────────────────────

def poll_telegram():
    """Проверить новые сообщения в Telegram и обработать."""
    log("🔍 Polling Telegram...")
    
    # Загружаем последний обработанный update_id
    state, state_sha = load_json("agent_state.json")
    last_update_id = state.get("last_update_id", 0)
    
    # Получаем новые сообщения
    result = tg_api("getUpdates", {
        "offset": last_update_id + 1,
        "timeout": 10,
        "allowed_updates": ["message"],
    })
    
    if not result.get("ok"):
        log(f"❌ Telegram API error: {result}")
        return
    
    updates = result.get("result", [])
    if not updates:
        log("⏳ Нет новых сообщений")
        return
    
    log(f"📨 Получено {len(updates)} новых сообщений")
    
    # Загружаем историю
    chat_history, _ = load_json("chat_history.json")
    if not chat_history:
        chat_history = {}
    
    for update in updates:
        update_id = update["update_id"]
        msg = update.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()
        
        if not chat_id or not text:
            continue
        
        # Пропускаем команды
        if text.startswith("/"):
            if text == "/start":
                send_message(chat_id, 
                    "🧠 <b>PawWork Clone</b> — твой личный AI агент\n\n"
                    "Работает 24/7 на GitHub Actions + GitHub Models (бесплатно).\n"
                    "Просто напиши, что нужно сделать.")
            continue
        
        # Инициализируем историю для этого чата
        if str(chat_id) not in chat_history:
            chat_history[str(chat_id)] = []
        
        # Обрабатываем сообщение
        response = process_message(chat_id, text, chat_history[str(chat_id)])
        
        # Сохраняем в историю
        chat_history[str(chat_id)].append({"role": "user", "content": text})
        chat_history[str(chat_id)].append({"role": "assistant", "content": response[:500]})
        
        # Обрезаем историю
        if len(chat_history[str(chat_id)]) > 20:
            chat_history[str(chat_id)] = chat_history[str(chat_id)][-20:]
        
        # Отправляем ответ
        send_message(chat_id, response)
        log(f"✅ Ответ отправлен в чат {chat_id}")
        
        # Обновляем last_update_id
        state["last_update_id"] = update_id
    
    # Сохраняем состояние и историю
    save_json("agent_state.json", state, state_sha)
    save_json("chat_history.json", chat_history)
    log("💾 Состояние сохранено")

# ── MAIN ──────────────────────────────────────────────────────

if __name__ == "__main__":
    log("🐾 PawWork Clone Agent v3.0")
    log(f"   Storage: {OWNER}/{REPO}")
    
    # Проверяем ключи
    if not TELEGRAM_TOKEN:
        log("❌ TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    if not GITHUB_TOKEN:
        log("❌ GITHUB_TOKEN не задан!")
        sys.exit(1)
    
    # Глобальное хранилище для memory_get/set
    history_store = {}
    
    # Поллинг
    poll_telegram()
    
    log("🏁 Готово")
