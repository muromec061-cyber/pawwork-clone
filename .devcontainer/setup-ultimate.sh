#!/usr/bin/env bash
# ============================================================================
# 🚀 PawWork Ultimate — Codespaces Deploy
# ============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${CYAN}[i]${NC} $1"; }
header() { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-8961572816:AAHYo4_gGmBHbrUiFokHl7UJJzGifh61_aU}"
GITHUB_TOKEN="${GITHUB_TOKEN:-ghp_Lx7AjHH4ZqMYLa3WUE7N78KOGgnF2q3OFAJo}"
CODESPACE_NAME=$(hostname)
CODESPACE_DOMAIN="${CODESPACE_NAME}-8080.preview.app.github.dev"

# ─── 1. Python + Pip ─────────────────────────────────────────────────────────
header "🐍 Python + Pip"
sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv ufw 2>/dev/null
log "Python готов"

# ─── 2. Ollama (уже стоит из setup-ollama.sh) ────────────────────────────────
header "🤖 Ollama + Модели"
if command -v ollama &>/dev/null; then
    log "Ollama уже установлен"
    # Качаем дополнительные модели если есть RAM
    TOTAL_RAM=$(free -m | awk '/Mem:/{print $2}')
    ollama pull llama3.2:3b 2>/dev/null && log "✓ llama3.2:3b" || true
fi

# ─── 3. OpenClaw 384k⭐ ──────────────────────────────────────────────────────
header "🦞 OpenClaw — AI Assistant (384k⭐)"
if command -v pnpm &>/dev/null && [[ ! -d /workspaces/pawwork-clone/openclaw ]]; then
    cd /workspaces/pawwork-clone
    info "Клонирование OpenClaw..."
    git clone --depth 1 https://github.com/openclaw/openclaw.git ./openclaw 2>/dev/null || warn "OpenClaw clone failed"
    cd openclaw
    pnpm install --no-frozen-lockfile 2>/dev/null && log "OpenClaw deps установлены" || warn "pnpm install failed"
    # Не билдим — слишком долго, бинарник можно скачать
    log "OpenClaw исходники готовы"
    cd /workspaces/pawwork-clone
fi

# ─── 4. CrewAI 56k⭐ ─────────────────────────────────────────────────────────
header "👥 CrewAI — Multi-Agent (56k⭐)"
pip3 install crewai crewai-tools 2>/dev/null && log "CrewAI установлен" || warn "CrewAI не установился"

# ─── 5. Eliza OS 19k⭐ ───────────────────────────────────────────────────────
header "🤖 Eliza OS (19k⭐)"
if [[ ! -d /workspaces/pawwork-clone/eliza ]]; then
    cd /workspaces/pawwork-clone
    git clone --depth 1 https://github.com/elizaOS/eliza.git ./eliza 2>/dev/null && log "Eliza склонирована" || warn "Eliza clone failed"
    cd eliza && npm install 2>/dev/null && log "Eliza deps установлены" || warn "Eliza npm install failed"
    cd /workspaces/pawwork-clone
fi

# ─── 6. Telegram Bot с генерацией изображений ────────────────────────────────
header "🤖 Telegram Bot + Image Generation"

BOT_DIR="/workspaces/pawwork-clone/bot"
mkdir -p "$BOT_DIR"

cat > "$BOT_DIR/bot.py" << 'PYTHON'
#!/usr/bin/env python3
"""PawWork Telegram Bot — Codespaces edition"""
import os, json, logging, urllib.request, urllib.parse, http.server, subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('pawwork')

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
HOSTNAME = os.environ.get('CODESPACE_NAME', 'localhost')
BOT_PORT = int(os.environ.get('BOT_PORT', 8080))

def tg(method, data):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}'
    req = urllib.request.Request(url, json.dumps(data).encode(), {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f'TG {method}: {e}')
        return {'ok': False}

def send(chat_id, text, **kw):
    return tg('sendMessage', {'chat_id': chat_id, 'text': str(text)[:4096], 'parse_mode': 'HTML', **kw})

def send_photo(chat_id, url, caption=''):
    tg('sendPhoto', {'chat_id': chat_id, 'photo': url, 'caption': str(caption)[:1024], 'parse_mode': 'HTML'})
    send(chat_id, f'🎨 <a href="{url}">{caption}</a>')

def generate(prompt):
    safe = urllib.parse.quote(f'{prompt}, masterpiece, high quality')
    url = f'https://image.pollinations.ai/prompt/{safe}?width=1024&height=1024&model=flux&nologo=true'
    return url

def ollama_chat(prompt, model='qwen2:0.5b'):
    try:
        data = json.dumps({'model': model, 'prompt': prompt, 'stream': False}).encode()
        req = urllib.request.Request('http://localhost:11434/api/generate', data, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get('response', '')
    except Exception as e:
        return f'Ollama error: {e}'

def handle(chat_id, text):
    if not text: return
    
    # /image command
    if text.startswith('/image ') or text.startswith('/img '):
        prompt = text.split(' ', 1)[1]
        send(chat_id, f'🎨 Генерирую <b>{prompt}</b>...')
        url = generate(prompt)
        return send_photo(chat_id, url, f'🎨 {prompt}')
    
    # /ask command
    if text.startswith('/ask '):
        prompt = text.split(' ', 1)[1]
        send(chat_id, '💬 Думаю...')
        resp = ollama_chat(prompt)
        return send(chat_id, resp[:4000])
    
    # /status
    if text == '/status' or text == '/start':
        try:
            r = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3)
            models = json.loads(r.read()).get('models', [])
            m_text = '\n'.join(f'• {m["name"]}' for m in models[:5])
        except:
            m_text = 'Ollama не отвечает'
        
        return send(chat_id,
            f'🤖 <b>PawWork Ultimate</b>\n'
            f'📍 Codespaces: {HOSTNAME}\n'
            f'📡 Bot: :{BOT_PORT}\n\n'
            f'<b>Модели Ollama:</b>\n{m_text}\n\n'
            f'🎨 <b>Команды:</b>\n'
            f'/image &lt;prompt&gt; — картинка\n'
            f'/ask &lt;вопрос&gt; — спроси AI\n'
            f'Или просто: нарисуй ...')
    
    # Keywords
    img_kw = ['нарисуй', 'картинк', 'изображен']
    if any(k in text.lower() for k in img_kw):
        prompt = text
        for k in img_kw:
            i = text.lower().find(k)
            if i >= 0:
                p = text[i+len(k):].lstrip(': ').strip()
                if p: prompt = p; break
        send(chat_id, f'🎨 Рисую <b>{prompt}</b>...')
        url = generate(prompt)
        return send_photo(chat_id, url, f'🎨 {prompt}')
    
    # Default — Ollama
    send(chat_id, '💬 Думаю...')
    resp = ollama_chat(text)
    send(chat_id, resp[:4000])

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'hostname': HOSTNAME}).encode())
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
                    handle(chat_id, text)
        except Exception as e:
            log.error(f'Error: {e}')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
    def log_message(self, *a): pass

if __name__ == '__main__':
    log.info(f'Starting bot on :{BOT_PORT}')
    
    # Set webhook
    public_url = f'https://{HOSTNAME}-{BOT_PORT}.preview.app.github.dev/webhook'
    log.info(f'Webhook URL: {public_url}')
    tg('setWebhook', {'url': public_url})
    
    server = http.server.HTTPServer(('0.0.0.0', BOT_PORT), Handler)
    server.serve_forever()
PYTHON

# Запускаем бота в фоне
log "Запуск Telegram бота..."
nohup python3 "$BOT_DIR/bot.py" > "$BOT_DIR/bot.log" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$BOT_DIR/bot.pid"
log "Бот запущен (PID: $BOT_PID) на порту 8080"

# ─── 7. Portainer ────────────────────────────────────────────────────────────
header "🐳 Portainer"
docker run -d --restart=always --name portainer -p 9000:9000 -v /var/run/docker.sock:/var/run/docker.sock portainer/portainer-ce:latest 2>/dev/null && log "Portainer :9000" || warn "Portainer не запустился"

# ─── 8. Заключение ───────────────────────────────────────────────────────────
header "✅ ГОТОВО!"

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         🚀 PAWWORK ULTIMATE — CODESPACES READY              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo -e "║  🤖 Telegram Bot:    ${CYAN}https://t.me/Gptzloy_bot${NC}           ║"
echo -e "║  🐳 Portainer:       ${CYAN}http://localhost:9000${NC}              ║"
echo -e "║  🦞 OpenClaw:        ${CYAN}/workspaces/pawwork-clone/openclaw${NC} ║"
echo -e "║  👥 CrewAI:          ${CYAN}pip install crewai${NC}                 ║"
echo -e "║  🐍 Ollama:          ${CYAN}http://localhost:11434${NC}             ║"
echo "║                                                              ║"
echo -e "║  📡 Public Bot URL:${NC}                                       ║"
echo -e "║    ${CYAN}https://${CODESPACE_NAME}-8080.preview.app.github.dev${NC}   ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "\n${YELLOW}📌 Логи бота:${NC} cat $BOT_DIR/bot.log"
echo -e "${YELLOW}📌 Перезапуск бота:${NC} kill \$(cat $BOT_DIR/bot.pid) && python3 $BOT_DIR/bot.py &"
echo -e "${YELLOW}📌 Команды Telegram:${NC} /image кот, /ask вопрос, /status"
