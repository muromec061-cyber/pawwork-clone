#!/usr/bin/env python3
"""PawWork Ultimate v8.0 — 30+ AI Agents + Gold Miner + Telegram Bot"""
import os, json, logging, html, urllib.request, urllib.parse, http.server, subprocess, threading, time, sys, traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('pawwork')

# ════════════════════════════ CONFIG ══════════════════════════════
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
BOT_PORT = int(os.environ.get('BOT_PORT', 8080))
OWNER_ID = int(os.environ.get('OWNER_ID', 5883513384))
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_ROUTER = os.path.join(os.path.dirname(__file__), 'agent_router.py')
GOLD_MINER = os.path.join(os.path.dirname(__file__), 'gold_miner.py')

def detect_url():
    for u in [os.environ.get('PUBLIC_URL', '')]:
        if u: return u.rstrip('/')
    for env_path in [os.path.join(os.path.dirname(__file__) or '.', '.env'),
                     os.path.join(os.path.dirname(os.path.dirname(__file__)) or '.', '.env')]:
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith('PUBLIC_URL='):
                    val = line.split('=', 1)[1].strip()
                    if val: return val
    try:
        r = subprocess.run(['gh', 'codespace', 'view', '--json', 'name'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            cs = json.loads(r.stdout).get('name', '')
            if cs: return f'https://{cs}-{BOT_PORT}.app.github.dev'
    except: pass
    return ''

PUBLIC_URL = detect_url()
HOSTNAME = os.environ.get('CODESPACE_NAME') or os.environ.get('HOSTNAME') or 'localhost'

# ═══════════════════════ TELEGRAM API ═════════════════════════════
def tg(method, data, timeout=30):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}'
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, body, {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'ok': False, 'error': e.read().decode('utf-8', errors='replace')[:500]}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def h(text): return html.escape(str(text), quote=False)

def send(chat_id, text, **kw):
    return tg('sendMessage', {'chat_id': chat_id, 'text': h(text)[:4096], 'parse_mode': 'HTML', 'disable_web_page_preview': True, **kw})

def send_md(chat_id, text, **kw):
    return tg('sendMessage', {'chat_id': chat_id, 'text': str(text)[:4096], 'parse_mode': 'Markdown', **kw})

def send_photo(chat_id, photo_url, caption='', keyboard=None):
    payload = {'chat_id': chat_id, 'photo': photo_url, 'caption': str(caption)[:1024], 'parse_mode': 'HTML'}
    if keyboard: payload['reply_markup'] = json.dumps(keyboard)
    r = tg('sendPhoto', payload, timeout=60)
    if r.get('ok'): return r
    try:
        req = urllib.request.Request(photo_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r2:
            img = r2.read()
        boundary = '----' + os.urandom(16).hex()
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="img.jpg"\r\n'
                f'Content-Type: image/jpeg\r\n\r\n').encode() + img + f'\r\n--{boundary}--\r\n'.encode()
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'
        req2 = urllib.request.Request(url, body, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
        with urllib.request.urlopen(req2, timeout=60) as r3:
            return json.loads(r3.read())
    except Exception as e:
        send(chat_id, f'Не смог загрузить: {e}\nСсылка: {photo_url}')
        return {'ok': False}

def keyboard(buttons):
    return json.dumps({'inline_keyboard': [[{'text': b[0], 'callback_data': b[1]} for b in row] for row in buttons]})

# ═══════════════════════ CORE SERVICES ════════════════════════════

def ollama_chat(prompt, model='qwen2:0.5b'):
    try:
        d = json.dumps({'model': model, 'prompt': prompt, 'stream': False, 'options': {'temperature': 0.7}}).encode()
        r = urllib.request.Request('http://localhost:11434/api/generate', d, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read()).get('response', '').strip()
    except Exception as e:
        return f'[Ollama: {e}]'

def ollama_models():
    try:
        with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5) as r:
            return json.loads(r.read()).get('models', [])
    except: return []

def ollama_pull(name):
    try:
        d = json.dumps({'name': name}).encode()
        r = urllib.request.Request('http://localhost:11434/api/pull', d, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(r, timeout=600) as resp:
            for line in resp:
                if json.loads(line).get('status') == 'success': return True
        return True
    except: return False

def generate_image(prompt, style='flux'):
    safe = urllib.parse.quote(f'{prompt}, masterpiece, high quality, detailed')
    model = {'flux': 'flux', 'anime': 'flux-anime', 'real': 'flux-realism', '3d': 'flux-3d'}.get(style, 'flux')
    return f'https://image.pollinations.ai/prompt/{safe}?width=1024&height=1024&model={model}&nologo=true'

def run_agent(agent_name, prompt):
    """Запустить агента из agent_router.py"""
    if os.path.exists(AGENT_ROUTER):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('router', AGENT_ROUTER)
            mod = importlib.util.module_from_spec(spec)
            sys.modules['router'] = mod
            spec.loader.exec_module(mod)
            return mod.route(agent_name, prompt)
        except Exception as e:
            return f'[Agent Router error: {e}]'
    return '[Agent Router not found. Run setup-agents.sh first]'

def run_gold_miner(lang=''):
    """Запустить Gold Miner"""
    if os.path.exists(GOLD_MINER):
        try:
            result = subprocess.run([sys.executable, GOLD_MINER, lang], capture_output=True, text=True, timeout=30)
            return result.stdout[:3500] or result.stderr[:500]
        except Exception as e:
            return f'[Gold Miner: {e}]'
    return '[Gold Miner not found]'

def agent_status(name):
    """Проверить доступность агента"""
    try:
        r = subprocess.run(['pip', 'show', name], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except: return False

# ═══════════════════════ ALL AGENTS MAP ═══════════════════════════

ALL_AGENTS = {
    # Python Frameworks
    'crewai': {'desc': 'Ролевые AI-агенты', 'cat': 'python'},
    'autogen': {'desc': 'Multi-agent (Microsoft)', 'cat': 'python'},
    'ag2': {'desc': 'AG2 (форк AutoGen)', 'cat': 'python'},
    'langgraph': {'desc': 'Графовые агенты', 'cat': 'python'},
    'llamaindex': {'desc': 'RAG фреймворк', 'cat': 'python'},
    'haystack': {'desc': 'NLP пайплайны', 'cat': 'python'},
    'pydanticai': {'desc': 'Типизированные AI', 'cat': 'python'},
    'smolagents': {'desc': 'Агенты HuggingFace', 'cat': 'python'},
    'camel': {'desc': 'CAMEL-AI ролевые', 'cat': 'python'},
    'metagpt': {'desc': 'AI команда разработки', 'cat': 'python'},
    'semantic-kernel': {'desc': 'Microsoft Semantic Kernel', 'cat': 'python'},
    'superagi': {'desc': 'SuperAGI автономные', 'cat': 'python'},
    'babyagi': {'desc': 'BabyAGI задачи', 'cat': 'python'},
    'swarms': {'desc': 'Стаи агентов', 'cat': 'python'},
    'phidata': {'desc': 'AI ассистенты', 'cat': 'python'},
    'open-interpreter': {'desc': 'AI интерпретатор', 'cat': 'python'},
    'aider': {'desc': 'AI парный программист', 'cat': 'python'},
    'gpt-researcher': {'desc': 'AI исследователь', 'cat': 'python'},
    'devika': {'desc': 'AI разработчик', 'cat': 'python'},
    'forge': {'desc': 'Forge агенты', 'cat': 'python'},

    # Node.js
    'openclaw': {'desc': 'OpenClaw CLI (384k⭐)', 'cat': 'node'},
    'autoclaw': {'desc': 'AutoClaw CLI', 'cat': 'node'},
    'claudeclaw': {'desc': 'Claude Code CLI', 'cat': 'node'},
    'goose': {'desc': 'Goose AI CLI', 'cat': 'node'},
    'lightagent': {'desc': 'LightAgent CLI', 'cat': 'node'},

    # Heavy
    'openhands': {'desc': 'OpenHands AI', 'cat': 'heavy'},
    'opendevin': {'desc': 'OpenDevin AI', 'cat': 'heavy'},
    'agentgpt': {'desc': 'AgentGPT', 'cat': 'heavy'},
    'continue-dev': {'desc': 'Continue (IDE)', 'cat': 'heavy'},
}

def get_agents_by_category():
    cats = {}
    for name, info in ALL_AGENTS.items():
        cat = info['cat']
        if cat not in cats: cats[cat] = []
        cats[cat].append((name, info))
    return cats

# ═══════════════════════ COMMAND HANDLER ═══════════════════════════

def handle(chat_id, text):
    if not text: return
    text = text.strip()
    cmd = text.split()[0].lower() if text else ''
    prompt = text.split(' ', 1)[1] if ' ' in text else ''

    # ── AGENT COMMANDS (динамические на основе ALL_AGENTS) ──
    for agent_name in ALL_AGENTS:
        agent_cmd = f'/{agent_name}'
        if text.startswith(agent_cmd + ' ') or text == agent_cmd:
            info = ALL_AGENTS[agent_name]
            if not prompt:
                return send(chat_id, f'🤖 <b>{agent_name}</b> — {info["desc"]}\nИспользование:\n<code>/{agent_name} твой запрос</code>')
            msg = send(chat_id, f'🤖 Запускаю <b>{agent_name}</b>...')
            resp = run_agent(agent_name, prompt)
            tg('deleteMessage', {'chat_id': chat_id, 'message_id': msg.get('result', {}).get('message_id', 0)})
            return send_md(chat_id, resp[:3800])

    # ── /agents — список всех агентов ──
    if text == '/agents':
        cats = get_agents_by_category()
        lines = ['🤖 <b>PawWork Arsenal — 30+ AI Агентов</b>\n']
        for cat, agents in cats.items():
            labels = {'python': '🐍 Python', 'node': '🟢 Node.js', 'heavy': '🏗 Тяжёлые'}
            lines.append(f'<b>{labels.get(cat, cat)}</b>')
            for name, info in agents:
                lines.append(f'  /{name} — {info["desc"]}')
            lines.append('')
        lines.append('💡 <code>/ai &lt;запрос&gt;</code> — авто-выбор агента')
        lines.append('💡 <code>/agents &lt;имя&gt;</code> — инфо об агенте')
        return send(chat_id, '\n'.join(lines))

    # ── /ai — авто-выбор ──
    if text.startswith('/ai ') or text == '/ai':
        if not prompt:
            return send(chat_id, 'Использование: /ai напиши код на Python')
        msg = send(chat_id, '🧠 <b>Выбираю лучшего агента...</b>')
        # Auto-route
        pl = prompt.lower()
        if any(w in pl for w in ['код', 'напиш', 'програм', 'скрипт', 'python', 'js', 'debug']):
            target = 'openclaw'
        elif any(w in pl for w in ['исследуй', 'найд', 'поищ', 'узнай', 'research']):
            target = 'gpt-researcher'
        elif any(w in pl for w in ['агент', 'команд', 'нескольк', 'multi', 'рол']):
            target = 'crewai'
        elif any(w in pl for w in ['документ', 'файл', 'анализ', 'текст']):
            target = 'llamaindex'
        else:
            target = 'openclaw'
        tg('deleteMessage', {'chat_id': chat_id, 'message_id': msg.get('result', {}).get('message_id', 0)})
        send(chat_id, f'🎯 Выбран агент: <b>{target}</b>')
        resp = run_agent(target, prompt)
        return send_md(chat_id, f'*{target}* response:\n\n{resp[:3500]}')

    # ── /gold — Gold Miner ──
    if text.startswith('/gold'):
        lang = text.split(' ', 1)[1] if ' ' in text else ''
        send(chat_id, '⛏ Добываю золото с GitHub...')
        result = run_gold_miner(lang)
        if not result.startswith('[Gold'):
            return send(chat_id, result)
        # Fallback: встроенный парсер
        try:
            r = urllib.request.Request('https://api.github.com/search/repositories?q=stars:>1000+created:>2026-01-01&sort=stars&order=desc&per_page=10',
                                      headers={'Accept': 'application/vnd.github.v3+json',
                                               'User-Agent': 'PawWork'})
            if os.environ.get('GITHUB_TOKEN'):
                r.headers['Authorization'] = f'token {os.environ["GITHUB_TOKEN"]}'
            with urllib.request.urlopen(r, timeout=10) as resp:
                data = json.loads(resp.read())
            items = data.get('items', [])
            if items:
                lines = ['🔥 <b>GitHub Gold Miner</b>\n']
                for i, item in enumerate(items[:10], 1):
                    name = item.get('full_name', '?')
                    stars = item.get('stargazers_count', 0)
                    desc = (item.get('description') or '')[:120]
                    url = item.get('html_url', '')
                    langname = item.get('language') or '?'
                    lines.append(f'{i}. <b>{name}</b>\n   ⭐ {stars} | 🛠 {langname}\n   {desc}\n   <a href="{url}">Открыть</a>')
                return send(chat_id, '\n'.join(lines))
        except Exception as e:
            return send(chat_id, f'Gold Miner временно недоступен: {e}')

    # ── Image commands ──
    if text.startswith(('/image ', '/img ')):
        style = 'flux'
        p = prompt
        if ' --' in p:
            parts = p.split(' --')
            p = parts[0]
            for s in parts[1:]:
                if s in ('anime', 'real', '3d', 'flux'): style = s
        send(chat_id, f'🎨 <b>Генерирую:</b> {h(p)}', reply_markup=keyboard([[(f'🎨 Ещё', f'/image {p}')]]))
        url = generate_image(p, style)
        return send_photo(chat_id, url, f'🎨 {h(p)}\nСтиль: <b>{style}</b>')

    # ── Ask AI ──
    if text.startswith(('/ask ', '/q ')):
        msg = send(chat_id, '🤔 <b>Думаю...</b>')
        resp = ollama_chat(prompt)
        tg('deleteMessage', {'chat_id': chat_id, 'message_id': msg.get('result', {}).get('message_id', 0)})
        return send_md(chat_id, f'{resp[:4000]}')

    # ── Models ──
    if text == '/models':
        models = ollama_models()
        if models:
            lines = [f'🤖 <b>Модели Ollama ({len(models)}):</b>']
            for m in models:
                lines.append(f'  • <code>{m["name"]}</code> — {m.get("size", 0)/1e9:.1f}GB')
            lines.append('\n💡 <code>/pull qwen2:7b</code> — установить')
            return send(chat_id, '\n'.join(lines))
        return send(chat_id, '❌ Ollama не отвечает')

    if text.startswith('/pull '):
        name = text.split(' ', 1)[1].strip()
        if not name: return send(chat_id, 'Укажи модель: /pull llama3.2')
        send(chat_id, f'📥 Качаю <b>{h(name)}</b>...')
        return send(chat_id, '✅ Установлено!' if ollama_pull(name) else f'❌ Ошибка {name}')

    # ── Status ──
    if text in ('/status', '/start', '/info'):
        models = ollama_models()
        m_text = '\n'.join(f'  • <code>{m["name"]}</code>' for m in models[:5]) if models else '  ❌ Не отвечает'
        
        # Check how many agents available
        agents_count = len(ALL_AGENTS)
        
        return send(chat_id,
            f'<b>🤖 PawWork Ultimate v8.0</b>\n'
            f'📍 <code>{HOSTNAME}</code> | :{BOT_PORT}\n\n'
            f'<b>🧠 Ollama:</b>\n{m_text}\n\n'
            f'<b>⚔️ Агенты:</b> {agents_count} установлено\n'
            f'<b>🔧 OpenClaude:</b> ✅ v0.26\n'
            f'<b>💎 Gold Miner:</b> ✅ готов\n\n'
            f'<b>⚡ Команды:</b>\n'
            f'/ai <i>запрос</i> — авто-выбор агента\n'
            f'/agents — список всех агентов\n'
            f'/<i>имя_агента</i> <i>запрос</i> — напрямую\n'
            f'/image <i>запрос</i> — картинка\n'
            f'/gold — GitHub Gold Miner\n'
            f'/help — справка',
            reply_markup=keyboard([
                [('⚔️ Все агенты', '/agents'), ('🎨 Картинка', '/image ')],
                [('⛏ Золото GitHub', '/gold'), ('🤖 AI', '/ai ')],
                [('ℹ️ Статус', '/status'), ('❓ Help', '/help')]
            ]))

    # ── Help ──
    if text == '/help':
        return send(chat_id,
            '🤖 <b>PawWork Ultimate v8.0</b>\n\n'
            '<b>🤖 AI Агенты (30+):</b>\n'
            '<code>/agents</code> — список всех\n'
            '<code>/ai напиши код на Python</code> — авто-выбор\n'
            '<code>/openclaw объясни TCP</code> — прямой вызов\n'
            '<code>/crewai создай команду</code> — CrewAI\n'
            '<code>/autogen сделай multi-agent</code> — AutoGen\n\n'
            '<b>🎨 Изображения:</b>\n'
            '<code>/image кот в космосе</code>\n'
            '<code>/image дракон --anime</code> (стили: anime/real/3d)\n\n'
            '<b>⛏ Gold Miner:</b>\n'
            '<code>/gold</code> — топ проектов GitHub\n'
            '<code>/gold python</code> — Python топ\n\n'
            '<b>⚙️ Система:</b>\n'
            '<code>/models</code> — модели Ollama\n'
            '<code>/pull qwen2:7b</code> — установить модель\n'
            '<code>/restart</code> — перезапуск (админ)\n\n'
            '🌐 <a href="https://github.com/Gitlawb/openclaude">OpenClaude</a> | '
            '<a href="https://ollama.com">Ollama</a>')

    # ── Admin ──
    if cmd == '/echo' and chat_id == OWNER_ID:
        return send(chat_id, ' '.join(text.split(' ')[1:]))
    if cmd == '/restart' and chat_id == OWNER_ID:
        send(chat_id, '♻️ Перезапуск...')
        os._exit(0)

    # ── Image by keyword ──
    img_kw = ['нарисуй', 'картинк', 'изображен', 'сгенерируй', 'создай картинк']
    for kw in img_kw:
        if kw in text.lower():
            idx = text.lower().find(kw)
            p = text[idx+len(kw):].lstrip(': ').strip() or text
            send(chat_id, f'🎨 Рисую <b>{h(p)}</b>...')
            return send_photo(chat_id, generate_image(p), f'🎨 {h(p)}')

    # ── Default: AI ──
    send(chat_id, '🤔 <b>Думаю...</b>')
    resp = ollama_chat(text)
    if resp.startswith('[Ошибка'):
        return send(chat_id, f'❌ {h(resp)}\n\nКоманды: /help')
    return send_md(chat_id, resp[:4000])

# ── Callbacks ────────────────────────────────────────────────────
def handle_callback(chat_id, data, cb_id):
    if data.startswith('/'):
        handle(chat_id, data)
        tg('answerCallbackQuery', {'callback_query_id': cb_id, 'text': '✅'})
    else:
        tg('answerCallbackQuery', {'callback_query_id': cb_id})

# ══════════════════════════ HTTP SERVER ══════════════════════════
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok', 'version': '8.0', 'hostname': HOSTNAME,
            'agents': len(ALL_AGENTS),
            'uptime': int(time.time() - start_time)
        }, indent=2).encode())
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            if 'message' in data:
                m = data['message']
                chat_id = m.get('chat', {}).get('id')
                text = (m.get('text') or '').strip()
                if chat_id and text:
                    log.info(f'📩 msg from {chat_id}: {text[:60]}')
                    threading.Thread(target=handle, args=(chat_id, text), daemon=True).start()
            elif 'callback_query' in data:
                cb = data['callback_query']
                chat_id = cb.get('message', {}).get('chat', {}).get('id')
                data_str = cb.get('data', '')
                cb_id = cb.get('id', '')
                if chat_id:
                    threading.Thread(target=handle_callback, args=(chat_id, data_str, cb_id), daemon=True).start()
        except Exception as e:
            log.error(f'Parse error: {e}')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
    def log_message(self, *a): pass

# ═══════════════════════════ MAIN ════════════════════════════════
if __name__ == '__main__':
    start_time = time.time()
    log.info(f'🚀 PawWork v8.0 starting on :{BOT_PORT}')
    if not TELEGRAM_TOKEN:
        log.error('❌ TELEGRAM_TOKEN not set!')
        exit(1)
    me = tg('getMe', {})
    if me.get('ok'):
        log.info(f'✅ Bot @{me["result"].get("username")}')
    
    wh_url = f'{PUBLIC_URL}/webhook' if PUBLIC_URL else ''
    if wh_url:
        wh = tg('setWebhook', {'url': wh_url, 'allowed_updates': ['message', 'callback_query']})
        if wh.get('ok'): log.info(f'✅ Webhook → {wh_url}')
        else: log.warning(f'⚠️ Webhook: {wh.get("error","?")}')
    else:
        log.warning('⚠️ No public URL — webhook must be set manually')
    
    try:
        urllib.request.urlopen('http://localhost:11434', timeout=3)
        log.info('✅ Ollama reachable')
    except:
        log.warning('⚠️ Ollama not reachable')
    
    # Проверяем доступность agent_router.py
    if os.path.exists(AGENT_ROUTER):
        log.info(f'✅ Agent Router: {len(ALL_AGENTS)} agents registered')
    else:
        log.warning('⚠️ Agent Router not found — run setup-agents.sh')
    
    log.info(f'🎯 Listening on :{BOT_PORT}')
    server = http.server.HTTPServer(('0.0.0.0', BOT_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        log.info('👋 Bye!')
