#!/usr/bin/env python3
"""PawWork Ultimate Telegram Bot v7.0 — Codespace / VPS edition"""
import os, json, logging, html, urllib.request, urllib.parse, http.server, subprocess, threading, time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('pawwork')

# ── Config ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
BOT_PORT = int(os.environ.get('BOT_PORT', 8080))
OWNER_ID = int(os.environ.get('OWNER_ID', 5883513384))  # @Dollarkiil

# Определяем публичный URL — пробуем несколько источников
def detect_url():
    # 1. Явная PUBLIC_URL
    u = os.environ.get('PUBLIC_URL', '')
    if u: return u.rstrip('/')
    # 2. .env файл (проверяем bot/.env и рядом с ботом /.env)
    for env_path in [os.path.join(os.path.dirname(__file__) or '.', '.env'),
                     os.path.join(os.path.dirname(os.path.dirname(__file__)) or '.', '.env')]:
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith('PUBLIC_URL='):
                    val = line.split('=', 1)[1].strip()
                    if val: return val
    # 3. gh codespace CLI
    try:
        import subprocess
        r = subprocess.run(['gh', 'codespace', 'view', '--json', 'name'],
                         capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            cs = json.loads(r.stdout).get('name', '')
            if cs: return f'https://{cs}-{BOT_PORT}.app.github.dev'
    except:
        pass
    return ''

PUBLIC_URL = detect_url()
HOSTNAME = os.environ.get('CODESPACE_NAME') or os.environ.get('HOSTNAME') or 'localhost'

# ── Telegram API helpers ──────────────────────────────────────────────

# ── Telegram API helpers ──────────────────────────────────────────────
def tg(method, data, timeout=30):
    """Call Telegram Bot API"""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}'
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, body, {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')[:500]
        log.error(f'TG {method} HTTP {e.code}: {err_body}')
        return {'ok': False, 'error': err_body}
    except Exception as e:
        log.error(f'TG {method}: {e}')
        return {'ok': False, 'error': str(e)}

def h(text):
    """Escape HTML for Telegram parse_mode"""
    return html.escape(str(text), quote=False)

def send(chat_id, text, **kw):
    """Send HTML message"""
    return tg('sendMessage', {
        'chat_id': chat_id,
        'text': h(text)[:4096],
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
        **kw
    })

def send_md(chat_id, text, **kw):
    """Send Markdown message (for code blocks)"""
    return tg('sendMessage', {
        'chat_id': chat_id,
        'text': str(text)[:4096],
        'parse_mode': 'Markdown',
        **kw
    })

def send_photo(chat_id, photo_url, caption='', keyboard=None):
    """Send photo — 2-level fallback: URL → multipart download"""
    payload = {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': str(caption)[:1024],
        'parse_mode': 'HTML'
    }
    if keyboard:
        payload['reply_markup'] = json.dumps(keyboard)
    result = tg('sendPhoto', payload, timeout=60)
    if not result.get('ok'):
        # Fallback: download + upload
        try:
            import tempfile
            req = urllib.request.Request(photo_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                img_data = r.read()
            # multipart upload
            boundary = '----WebKitFormBoundary' + os.urandom(16).hex()
            body = b''
            body += f'--{boundary}\r\n'.encode()
            body += f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode()
            body += f'--{boundary}\r\n'.encode()
            body += f'Content-Disposition: form-data; name="photo"; filename="image.jpg"\r\n'.encode()
            body += b'Content-Type: image/jpeg\r\n\r\n'
            body += img_data
            body += f'\r\n--{boundary}--\r\n'.encode()
            url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'
            req2 = urllib.request.Request(url, body, {
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            })
            with urllib.request.urlopen(req2, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            send(chat_id, f'Не смог загрузить картинку: {e}\nПрямая ссылка: {photo_url}')
            return {'ok': False}
    return result

def keyboard(buttons, resize=True):
    """Build reply markup with inline buttons"""
    return json.dumps({
        'inline_keyboard': [[{'text': b[0], 'callback_data': b[1]} for b in row]
                           for row in buttons]
    })

def delete_after(chat_id, msg_id, delay=5):
    """Auto-delete message after delay"""
    def _del():
        time.sleep(delay)
        tg('deleteMessage', {'chat_id': chat_id, 'message_id': msg_id})
    threading.Thread(target=_del, daemon=True).start()

# ── AI / Services ─────────────────────────────────────────────────────

def ollama_chat(prompt, model='qwen2:0.5b'):
    """Ask Ollama (local)"""
    try:
        data = json.dumps({'model': model, 'prompt': prompt, 'stream': False, 'options': {'temperature': 0.7}}).encode()
        req = urllib.request.Request('http://localhost:11434/api/generate', data, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
            return result.get('response', '').strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return f'[Ошибка Ollama HTTP {e.code}: {body}]'
    except Exception as e:
        return f'[Ошибка Ollama: {e}]'

def ollama_models():
    """Get available Ollama models"""
    try:
        req = urllib.request.Request('http://localhost:11434/api/tags')
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return data.get('models', [])
    except:
        return []

def ollama_pull(name):
    """Pull a model (async)"""
    try:
        data = json.dumps({'name': name}).encode()
        req = urllib.request.Request('http://localhost:11434/api/pull', data, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=600) as r:
            for line in r:
                status = json.loads(line)
                if status.get('status') == 'success':
                    return True
        return True
    except:
        return False

def generate_image(prompt, style='flux'):
    """Generate image via Pollinations"""
    safe = urllib.parse.quote(f'{prompt}, masterpiece, high quality, detailed')
    model = {'flux': 'flux', 'anime': 'flux-anime', 'real': 'flux-realism', '3d': 'flux-3d'}.get(style, 'flux')
    return f'https://image.pollinations.ai/prompt/{safe}?width=1024&height=1024&model={model}&nologo=true'

def openclaude_query(task):
    """Call OpenClaude CLI if installed"""
    try:
        result = subprocess.run(
            ['npx', '@gitlawb/openclaude', '--prelude', 'no', '--print', task],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, 'OPENCLAUDE_HEADLESS': '1'}
        )
        return result.stdout.strip() or result.stderr.strip() or '[пусто]'
    except FileNotFoundError:
        return None  # OpenClaude not installed
    except subprocess.TimeoutExpired:
        return '[Таймаут OpenClaude]'
    except Exception as e:
        return f'[OpenClaude: {e}]'

# ── Command handlers ──────────────────────────────────────────────────

def handle(chat_id, text):
    if not text:
        return
    text = text.strip()

    # ── Image commands ──
    if text.startswith(('/image ', '/img ')):
        prompt = text.split(' ', 1)[1]
        style = 'flux'
        if ' --' in prompt:
            parts = prompt.split(' --')
            prompt = parts[0]
            for p in parts[1:]:
                if p in ('anime', 'real', '3d', 'flux'):
                    style = p
        msg = send(chat_id, f'🎨 <b>Генерирую:</b> {h(prompt)}', 
                    reply_markup=keyboard([[(f'🎨 Ещё {prompt[:20]}', f'/image {prompt}')]]))
        url = generate_image(prompt, style)
        return send_photo(chat_id, url, f'🎨 {h(prompt)}\nСтиль: <b>{style}</b> | <a href="{url}">Открыть</a>')

    # ── Ask AI ──
    if text.startswith(('/ask ', '/ai ', '/q ')):
        prompt = text.split(' ', 1)[1]
        msg = send(chat_id, '🤔 <b>Думаю...</b>')
        resp = ollama_chat(prompt)
        if resp.startswith('[Ошибка'):
            return send(chat_id, f'❌ {h(resp)}\n\nПопробуй /models чтобы проверить модели.')
        # Delete thinking message
        tg('deleteMessage', {'chat_id': chat_id, 'message_id': msg.get('result', {}).get('message_id', 0)})
        return send_md(chat_id, f'*{h(prompt)[:100]}*\n\n{resp[:3800]}')

    # ── Models ──
    if text == '/models':
        models = ollama_models()
        if models:
            lines = [f'🤖 <b>Модели Ollama ({len(models)}):</b>']
            for m in models:
                name = m.get('name', '?')
                size_gb = m.get('size', 0) / 1e9
                modified = m.get('modified_at', '')[:10]
                lines.append(f'  • <code>{name}</code> — {size_gb:.1f}GB ({modified})')
            lines.append(f'\n💡 <code>/pull qwen2:7b</code> — установить новую')
            return send(chat_id, '\n'.join(lines))
        else:
            return send(chat_id, '❌ Ollama не отвечает.\nПроверь: <code>curl localhost:11434</code>')

    # ── Pull model ──
    if text.startswith('/pull '):
        name = text.split(' ', 1)[1].strip()
        if not name:
            return send(chat_id, 'Укажи имя модели: /pull llama3.2:3b')
        send(chat_id, f'📥 Качаю <b>{h(name)}</b>... это может занять несколько минут.')
        ok = ollama_pull(name)
        if ok:
            return send(chat_id, f'✅ Модель <b>{h(name)}</b> установлена! Используй /ask {h(name)} как?')
        else:
            return send(chat_id, f'❌ Не удалось установить {h(name)}')

    # ── Code via OpenClaude ──
    if text.startswith(('/code ', '/hack ', '/c ')):
        task = text.split(' ', 1)[1]
        msg = send(chat_id, '🧠 <b>Отправляю задачу OpenClaude...</b>\nЭто может занять до 30 секунд.')
        resp = openclaude_query(task)
        tg('deleteMessage', {'chat_id': chat_id, 'message_id': msg.get('result', {}).get('message_id', 0)})
        if resp is None:
            return send(chat_id, '❌ OpenClaude не установлен. Набери /setup_openclaude')
        return send_md(chat_id, f'*OpenClaude:*\n{resp[:3800]}')

    # ── Setup OpenClaude ──
    if text == '/setup_openclaude':
        send(chat_id, '📦 <b>Устанавливаю OpenClaude...</b>\nЭто займёт ~1-2 минуты.')
        try:
            result = subprocess.run(['npm', 'install', '-g', '@gitlawb/openclaude'],
                                  capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                return send(chat_id, '✅ OpenClaude установлен!\nТеперь работает /code')
            return send(chat_id, f'❌ Ошибка: {result.stderr[:500]}')
        except Exception as e:
            return send(chat_id, f'❌ {e}')

    # ── Status ──
    if text in ('/status', '/start', '/info'):
        models = ollama_models()
        m_text = '\n'.join(f'  • <code>{m["name"]}</code>' for m in models[:8]) if models else '  ❌ Не отвечает'
        # Check OpenClaude
        oc = '✅ Установлен' if openclaude_query('echo test') is not None else '❌ Не установлен'
        
        return send(chat_id,
            f'🤖 <b>PawWork Ultimate v7</b>\n'
            f'📍 <code>{HOSTNAME}</code> | :{BOT_PORT}\n'
            f'🔗 <code>{PUBLIC_URL or "не задан"}</code>\n\n'
            f'<b>🧠 Ollama:</b>\n{m_text}\n\n'
            f'<b>🔧 OpenClaude:</b> {oc}\n\n'
            f'<b>⚡ Команды:</b>\n'
            f'/ask <i>текст</i> — спросить AI (Ollama)\n'
            f'/image <i>запрос</i> — картинка (AI)\n'
            f'/code <i>задача</i> — написать код (OpenClaude)\n'
            f'/models — список моделей Ollama\n'
            f'/help — подробная справка',
            reply_markup=keyboard([
                [('🎨 Сгенерировать', '/image '), ('🤖 Спросить', '/ask ')],
                [('💻 Написать код', '/code '), ('📋 Модели', '/models')],
                [('ℹ️ Статус', '/status'), ('❓ Помощь', '/help')]
            ]))

    # ── Help ──
    if text == '/help':
        return send(chat_id,
            f'🤖 <b>PawWork Ultimate Bot</b>\n\n'
            f'<b>🎨 Изображения</b>\n'
            f'<code>/image кот в космосе</code>\n'
            f'<code>/image дракон --anime</code> (стили: anime, real, 3d)\n'
            f'Или просто: <code>нарисуй кот</code>\n\n'
            f'<b>🧠 AI (Ollama локально)</b>\n'
            f'<code>/ask что такое квантовый компьютер</code>\n'
            f'<code>/q объясни простыми словами</code>\n\n'
            f'<b>💻 Код (OpenClaude)</b>\n'
            f'<code>/code напиши скрипт парсинга</code>\n'
            f'<code>/hack объясни код на Python</code>\n'
            f'<code>/setup_openclaude</code> — установить OpenClaude\n\n'
            f'<b>⚙️ Система</b>\n'
            f'<code>/status</code> — состояние сервера\n'
            f'<code>/models</code> — список моделей\n'
            f'<code>/pull qwen2:1.5b</code> — установить модель\n\n'
            f'<b>🔗 Ссылки</b>\n'
            f'<a href="https://github.com/Gitlawb/openclaude">OpenClaude</a> | '
            f'<a href="https://ollama.com">Ollama</a>')

    # ── Echo (admin) ──
    if text.startswith('/echo ') and chat_id == OWNER_ID:
        return send(chat_id, text.split(' ', 1)[1])

    # ── Restart ──
    if text == '/restart' and chat_id == OWNER_ID:
        send(chat_id, '♻️ Перезапускаюсь...')
        os._exit(0)

    # ── Image by keyword ──
    img_keywords = ['нарисуй', 'картинк', 'изображен', 'сгенерируй', 'создай картинк']
    for kw in img_keywords:
        if kw in text.lower():
            prompt = text
            idx = text.lower().find(kw)
            after = text[idx+len(kw):].lstrip(': ').strip()
            if after:
                prompt = after
            send(chat_id, f'🎨 Рисую <b>{h(prompt)}</b>...')
            url = generate_image(prompt)
            return send_photo(chat_id, url, f'🎨 {h(prompt)}')

    # ── Default: AI ──
    send(chat_id, '🤔 <b>Думаю...</b>')
    resp = ollama_chat(text)
    if resp.startswith('[Ошибка'):
        return send(chat_id, f'❌ {h(resp)}\n\nКоманды: /help')
    return send_md(chat_id, f'{resp[:4000]}')

# ── Callback query handler ────────────────────────────────────────────
def handle_callback(chat_id, data, msg_id):
    """Handle inline button presses"""
    if data.startswith('/'):
        # Execute as command
        handle(chat_id, data)
        tg('answerCallbackQuery', {'callback_query_id': msg_id, 'text': '✅'})
    else:
        tg('answerCallbackQuery', {'callback_query_id': msg_id})

# ── HTTP Server ───────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'hostname': HOSTNAME,
            'version': '7.0',
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
                log.info(f'📩 msg from {chat_id}: {text[:60]}')
                if chat_id and text:
                    # Async handling so webhook responds fast
                    threading.Thread(target=handle, args=(chat_id, text), daemon=True).start()
            elif 'callback_query' in data:
                cb = data['callback_query']
                chat_id = cb.get('message', {}).get('chat', {}).get('id')
                data_str = cb.get('data', '')
                cb_id = cb.get('id', '')
                log.info(f'🔘 callback from {chat_id}: {data_str}')
                if chat_id:
                    threading.Thread(target=handle_callback, args=(chat_id, data_str, cb_id), daemon=True).start()
        except Exception as e:
            log.error(f'Parse error: {e}')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *a): pass

# ── Main ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    start_time = time.time()
    log.info(f'🚀 PawWork Bot v7.0 starting on :{BOT_PORT}')
    
    if not TELEGRAM_TOKEN:
        log.error('❌ TELEGRAM_TOKEN not set!')
        exit(1)
    
    # Check me
    me = tg('getMe', {})
    if me.get('ok'):
        bot_user = me.get('result', {})
        log.info(f'✅ Bot @{bot_user.get("username")} — {bot_user.get("first_name")}')
    else:
        log.warning(f'⚠️ Cannot verify bot identity')
    
    # Set webhook
    wh_url = f'{PUBLIC_URL}/webhook' if PUBLIC_URL else ''
    if wh_url:
        log.info(f'📡 Webhook URL computed: {wh_url}')
        wh = tg('setWebhook', {'url': wh_url})
        if wh.get('ok'):
            log.info(f'✅ Webhook set → {wh_url}')
        else:
            log.warning(f'⚠️ Webhook auto-set failed: {wh.get("error", "?")}')
    else:
        log.warning(f'⚠️ No public URL — webhook must be set manually')
        log.info(f'➡️  Use: tg setWebhook?url=https://YOUR-URL.app.github.dev/webhook')
    
    # Check Ollama
    try:
        urllib.request.urlopen('http://localhost:11434', timeout=3)
        log.info('✅ Ollama reachable')
    except:
        log.warning('⚠️ Ollama not reachable')
    
    server = http.server.HTTPServer(('0.0.0.0', BOT_PORT), Handler)
    log.info(f'🎯 Listening on :{BOT_PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        log.info('👋 Bye!')
