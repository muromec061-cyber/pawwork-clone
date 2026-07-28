#!/usr/bin/env bash
# ============================================================================
# 🚀 PawWork VPS ULTIMATE DEPLOY — v1.0
# ============================================================================
# Разворачивает ПОЛНОЕ окружение на свежем VPS с root:
#   ✓ Docker + Portainer (веб-панель)
#   ✓ Ollama + GGUF модели (qwen2, Moonlight, kimi-vl)
#   ✓ OpenClaw (384k⭐) — личный AI ассистент
#   ✓ CrewAI (56k⭐) — мульти-агентная оркестрация
#   ✓ Eliza OS (19k⭐) — агентная ОС
#   ✓ Telegram бот с генерацией изображений
#   ✓ Nginx Proxy Manager (веб-панель)
#   ✓ Uptime Kuma (мониторинг 24/7)
#   ✓ Firewall + авто-старт
# ============================================================================
# ИСПОЛЬЗОВАНИЕ:
#   curl -fsSL https://raw.githubusercontent.com/muromec061-cyber/pawwork-clone/master/deploy-vps.sh | bash
#
#   Или сохранить и запустить:
#   chmod +x deploy-vps.sh && sudo ./deploy-vps.sh
# ============================================================================

set -euo pipefail

# ─── Цвета ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${CYAN}[i]${NC} $1"; }
header() { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ─── Проверка root ───────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    warn "Запуск без root — некоторые шаги могут не сработать"
    warn "Лучше запусти с sudo: sudo curl -fsSL ... | sudo bash"
fi

# ─── Конфигурация ────────────────────────────────────────────────────────────
REPO_URL="https://github.com/muromec061-cyber/pawwork-clone.git"
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-8961572816:AAHYo4_gGmBHbrUiFokHl7UJJzGifh61_aU}"
GITHUB_TOKEN="${GITHUB_TOKEN:-ghp_Lx7AjHH4ZqMYLa3WUE7N78KOGgnF2q3OFAJo}"
DOMAIN="${DOMAIN:-}"  # Если есть домен — укажи, например pawwork.lobster

OPENCLAW_DIR="/opt/openclaw"
CREWAI_DIR="/opt/crewai"
ELIZA_DIR="/opt/eliza"
PAWWORK_DIR="/opt/pawwork"
DOCKER_DIR="/opt/docker-stacks"
OLLAMA_DIR="/opt/ollama-models"

# ─── 1. БАЗОВАЯ НАСТРОЙКА ────────────────────────────────────────────────────
header "📦 Базовая настройка системы"

# Определяем ОС
if command -v apt &>/dev/null; then
    PKG_MANAGER="apt"
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"
elif command -v yum &>/dev/null; then
    PKG_MANAGER="yum"
elif command -v apk &>/dev/null; then
    PKG_MANAGER="apk"
else
    err "Неизвестный пакетный менеджер. Поддерживаются: apt, dnf, yum, apk"
    exit 1
fi

log "Пакетный менеджер: $PKG_MANAGER"

# Обновление + базовые пакеты
info "Обновление пакетов..."
case $PKG_MANAGER in
    apt)
        apt-get update -qq && apt-get install -y -qq curl wget git unzip gnupg lsb-release ca-certificates software-properties-common ufw python3 python3-pip nodejs npm 2>/dev/null
        ;;
    dnf|yum)
        $PKG_MANAGER install -y curl wget git unzip gnupg ca-certificates python3 python3-pip nodejs npm ufw 2>/dev/null
        ;;
    apk)
        apk add --no-cache curl wget git unzip gnupg python3 py3-pip nodejs npm 2>/dev/null
        ;;
esac
log "Базовые пакеты установлены"

# ─── 2. DOCKER + DOCKER COMPOSE ──────────────────────────────────────────────
header "🐳 Docker + Docker Compose + Portainer"

if ! command -v docker &>/dev/null; then
    info "Установка Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker 2>/dev/null || true
    log "Docker установлен"
else
    log "Docker уже установлен"
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
    info "Установка Docker Compose..."
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    log "Docker Compose установлен"
fi

# Portainer — веб-панель управления Docker
docker volume create portainer_data 2>/dev/null || true
docker run -d --restart=always --name portainer -p 9000:9000 -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:latest 2>/dev/null && log "Portainer запущен на порту 9000" || warn "Portainer уже запущен"

# ─── 3. OLLAMA + МОДЕЛИ ─────────────────────────────────────────────────────
header "🤖 Ollama + GGUF модели"

if ! command -v ollama &>/dev/null; then
    info "Установка Ollama..."
    curl -fsSL https://ollama.com/install.sh | bash
    log "Ollama установлен"
else
    log "Ollama уже установлен"
fi

# Убедимся что Ollama запущен
systemctl enable ollama 2>/dev/null || true
systemctl start ollama 2>/dev/null || ollama serve &>/dev/null &

# Ждём запуск
sleep 3

# Качаем модели
info "Загрузка моделей (первые 2 — обязательные, остальные — опционально)..."
ollama pull qwen2:0.5b 2>/dev/null && log "✓ qwen2:0.5b (352 MB)" || warn "qwen2:0.5b не загрузилась"

# Остальные модели — если хватает места
TOTAL_RAM=$(free -m | awk '/Mem:/{print $2}')
if [[ $TOTAL_RAM -gt 3000 ]]; then
    ollama pull llama3.2:3b 2>/dev/null && log "✓ llama3.2:3b" || warn "llama3.2:3b пропущена"
fi
if [[ $TOTAL_RAM -gt 7000 ]]; then
    ollama pull llama3.1:8b 2>/dev/null && log "✓ llama3.1:8b" || warn "llama3.1:8b пропущена"
fi
if [[ $TOTAL_RAM -gt 15000 ]]; then
    ollama pull moonlight-16b-a3b 2>/dev/null && log "✓ Moonlight-16B-A3B" || warn "Moonlight пропущена"
fi

log "Ollama готов: http://localhost:11434"

# ─── 4. OPENCLAW (384k⭐) ────────────────────────────────────────────────────
header "🦞 OpenClaw — AI Assistant (384k⭐)"

if [[ ! -d "$OPENCLAW_DIR" ]]; then
    # Устанавливаем pnpm
    if ! command -v pnpm &>/dev/null; then
        info "Установка pnpm..."
        npm install -g pnpm 2>/dev/null
    fi
    
    info "Клонирование OpenClaw (384k⭐)..."
    git clone --depth 1 https://github.com/openclaw/openclaw.git "$OPENCLAW_DIR" 2>/dev/null || {
        warn "Git clone не удался, пробуем через зеркало"
        git clone --depth 1 https://gitclone.com/github.com/openclaw/openclaw.git "$OPENCLAW_DIR" 2>/dev/null || {
            warn "OpenClaw не склонировался — пропускаем"
            OPENCLAW_DIR=""
        }
    }
    
    if [[ -n "$OPENCLAW_DIR" && -d "$OPENCLAW_DIR" ]]; then
        cd "$OPENCLAW_DIR"
        info "Установка зависимостей OpenClaw (может занять 5-10 мин)..."
        pnpm install --no-frozen-lockfile 2>/dev/null || warn "pnpm install не удался"
        pnpm build 2>/dev/null || warn "pnpm build не удался"
        
        # Создаём systemd сервис
        cat > /etc/systemd/system/openclaw.service << 'SERVICE'
[Unit]
Description=OpenClaw AI Assistant
After=network.target ollama.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/openclaw
ExecStart=/usr/bin/pnpm openclaw gateway start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE
        systemctl daemon-reload
        systemctl enable openclaw 2>/dev/null || true
        log "OpenClaw установлен в $OPENCLAW_DIR"
    fi
else
    log "OpenClaw уже установлен"
fi

# ─── 5. CREWAI (56k⭐) ───────────────────────────────────────────────────────
header "👥 CrewAI — Multi-Agent Framework (56k⭐)"

if [[ ! -d "$CREWAI_DIR" ]]; then
    mkdir -p "$CREWAI_DIR"
    cd "$CREWAI_DIR"
    
    # Устанавливаем CrewAI через pip
    info "Установка CrewAI..."
    pip3 install crewai crewai-tools 2>/dev/null && log "CrewAI установлен" || warn "CrewAI pip install не удался"
    
    # Создаём тестовый проект
    cat > "$CREWAI_DIR/example.py" << 'PYTHON'
from crewai import Agent, Task, Crew, Process

class PawWorkCrew:
    """Тестовый мульти-агентный Crew"""
    
    @staticmethod
    def run(task_description: str) -> str:
        researcher = Agent(
            role='Исследователь',
            goal='Находить точную информацию',
            backstory='Ты опытный исследователь данных',
            verbose=True,
        )
        
        writer = Agent(
            role='Писатель',
            goal='Создавать понятные тексты',
            backstory='Ты профессиональный копирайтер',
            verbose=True,
        )
        
        research = Task(
            description=task_description,
            agent=researcher,
        )
        
        write = Task(
            description='Оформи найденную информацию в красивый отчёт',
            agent=writer,
        )
        
        crew = Crew(
            agents=[researcher, writer],
            tasks=[research, write],
            process=Process.sequential,
        )
        
        return crew.kickoff()

if __name__ == '__main__':
    result = PawWorkCrew.run('Расскажи про OpenClaw')
    print(result)
PYTHON
    log "CrewAI установлен + пример проекта"
else
    log "CrewAI уже установлен"
fi

# ─── 6. ELIZA OS (19k⭐) ─────────────────────────────────────────────────────
header "🤖 Eliza OS — Agentic Operating System (19k⭐)"

if [[ ! -d "$ELIZA_DIR" ]]; then
    info "Установка Eliza OS..."
    git clone --depth 1 https://github.com/elizaOS/eliza.git "$ELIZA_DIR" 2>/dev/null || {
        warn "Eliza OS не склонировалась — пропускаем"
        ELIZA_DIR=""
    }
    
    if [[ -n "$ELIZA_DIR" && -d "$ELIZA_DIR" ]]; then
        cd "$ELIZA_DIR"
        npm install 2>/dev/null && log "Eliza OS установлена" || warn "Eliza OS npm install не удался"
    fi
else
    log "Eliza OS уже установлена"
fi

# ─── 7. TELEGRAM BOT ─────────────────────────────────────────────────────────
header "🤖 Telegram Bot + Image Generation"

mkdir -p "$PAWWORK_DIR"
cd "$PAWWORK_DIR"

# Клонируем репозиторий
if [[ ! -d "$PAWWORK_DIR/pawwork-clone" ]]; then
    git clone --depth 1 "$REPO_URL" "$PAWWORK_DIR/pawwork-clone" 2>/dev/null || {
        warn "Не удалось склонировать pawwork-clone"
    }
fi

# Создаём простой Python Telegram бот с генерацией изображений
cat > "$PAWWORK_DIR/bot.py" << 'PYTHON'
#!/usr/bin/env python3
"""PawWork Telegram Bot — VPS версия с реальной генерацией изображений"""
import os, json, io, logging, urllib.request, urllib.parse, http.server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('pawwork-vps')

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', f'http://{os.uname().nodename}:8080/webhook')
OLLAMA_URL = 'http://localhost:11434/api/generate'
POLLINATIONS_URL = 'https://image.pollinations.ai/prompt'

def tg_call(method, data):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}'
    req = urllib.request.Request(url, json.dumps(data).encode(), {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f'TG {method}: {e}')
        return {'ok': False}

def send_message(chat_id, text, **kw):
    return tg_call('sendMessage', {'chat_id': chat_id, 'text': str(text)[:4096], 'parse_mode': 'HTML', **kw})

def send_photo(chat_id, url, caption=''):
    payload = {'chat_id': chat_id, 'photo': url, 'caption': str(caption)[:1024], 'parse_mode': 'HTML'}
    # Попытка 1: URL
    result = tg_call('sendPhoto', payload)
    if result.get('ok'): return result
    # Попытка 2: скачать и отправить multipart
    try:
        img = urllib.request.urlopen(url, timeout=30).read()
        boundary = b'----Boundary7MA4YW'
        body = []
        def add(k, v, is_file=False):
            body.append(b'--' + boundary)
            if is_file:
                body.append(f'Content-Disposition: form-data; name="{k}"; filename="image.jpg"\r\nContent-Type: image/jpeg\r\n'.encode())
                body.append(b'\r\n' + v + b'\r\n')
            else:
                body.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        add(b'chat_id', str(chat_id).encode())
        add(b'photo', img, is_file=True)
        add(b'caption', str(caption)[:1024].encode())
        add(b'parse_mode', b'HTML')
        body.append(b'--' + boundary + b'--\r\n')
        
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto',
            b''.join(body),
            {'Content-Type': b'multipart/form-data; boundary=' + boundary}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f'Multipart error: {e}')
    # Попытка 3: ссылка текстом
    return send_message(chat_id, f'🎨 <a href="{url}">Картинка</a>\n{caption}')

def generate_image(prompt):
    """Генерация через Pollinations.ai"""
    safe = urllib.parse.quote(prompt)
    url = f'{POLLINATIONS_URL}/{safe}?width=1024&height=1024&model=flux&nologo=true'
    # Проверяем что картинка реально генерируется
    try:
        test = urllib.request.urlopen(url, timeout=10)
        if test.status == 200 and int(test.headers.get('Content-Length', 1000)) > 1000:
            return url, True
    except:
        pass
    return url, False

def ollama_chat(prompt, model='qwen2:0.5b'):
    """Чат через локальную Ollama"""
    data = json.dumps({'model': model, 'prompt': prompt, 'stream': False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get('response', '')
    except Exception as e:
        return f'Ollama error: {e}'

def handle_message(chat_id, text):
    if not text: return
    
    # Команды
    if text.startswith('/'):
        parts = text.split()
        cmd = parts[0].lower()
        args = ' '.join(parts[1:])
        
        if cmd == '/start':
            return send_message(chat_id,
                '🤖 <b>PawWork VPS Ultimate</b>\n\n'
                '🎨 /image &lt;prompt&gt; — генерация картинки\n'
                '💬 /ask &lt;вопрос&gt; — спросить Ollama\n'
                '📊 /ollama — статус Ollama\n'
                '🌐 /portainer — ссылка на Portainer\n'
                '🦞 /openclaw — статус OpenClaw\n'
                '❓ /help — помощь\n\n'
                'Или просто напиши "нарисуй ..."')
        
        if cmd == '/image' and args:
            send_message(chat_id, f'🎨 Генерирую <b>{args}</b>...')
            url, ok = generate_image(args)
            if ok:
                return send_photo(chat_id, url, f'🎨 {args}')
            else:
                return send_message(chat_id, f'🎨 <a href="{url}">{args}</a>')
        
        if cmd == '/ask' and args:
            send_message(chat_id, f'💬 Думаю...')
            response = ollama_chat(args)
            return send_message(chat_id, response[:4000])
        
        if cmd == '/ollama':
            try:
                r = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5)
                models = json.loads(r.read()).get('models', [])
                text = '📊 <b>Ollama модели:</b>\n' + '\n'.join(f'• {m["name"]} ({m["size"]//1e9}GB)' for m in models[:10])
                return send_message(chat_id, text)
            except:
                return send_message(chat_id, '❌ Ollama не отвечает')
        
        if cmd in ['/portainer', '/kuma']:
            return send_message(chat_id, f'🌐 <b>Панели управления:</b>\n'
                f'• Portainer: http://{urllib.request.urlopen("http://ifconfig.me").read().decode().strip()}:9000\n'
                f'• OpenClaw: http://localhost:3737')
        
        if cmd == '/help':
            return send_message(chat_id,
                '❓ <b>Команды:</b>\n'
                '/image &lt;prompt&gt; — картинка\n'
                '/ask &lt;вопрос&gt; — спроси AI\n'
                '/ollama — список моделей\n'
                '/portainer — панель Docker\n'
                '/openclaw — статус\n\n'
                '🎨 Просто напиши "нарисуй ..."')
        
        return send_message(chat_id, '❓ /help')
    
    # Прямое распознавание картинок
    img_kw = ['нарисуй', 'картинк', 'изображен']
    if any(k in text.lower() for k in img_kw):
        prompt = text
        for k in img_kw:
            i = text.lower().find(k)
            if i >= 0:
                p = text[i+len(k):].lstrip(': ').strip()
                if p: prompt = p; break
        send_message(chat_id, f'🎨 Рисую <b>{prompt}</b>...')
        url, ok = generate_image(prompt)
        return send_photo(chat_id, url, f'🎨 {prompt}') if ok else send_message(chat_id, f'🎨 <a href="{url}">{prompt}</a>')
    
    # Всё остальное — Ollama
    send_message(chat_id, f'💬 Думаю...')
    response = ollama_chat(text)
    send_message(chat_id, response[:4000])

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'pawwork-vps'}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            if 'message' in data:
                chat_id = data['message'].get('chat', {}).get('id')
                text = (data['message'].get('text') or '').strip()
                if chat_id and text:
                    handle_message(chat_id, text)
        except Exception as e:
            log.error(f'Webhook error: {e}')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
    def log_message(self, *a): pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    log.info(f'PawWork VPS Bot starting on :{port}')
    
    # Set webhook
    wh_url = os.environ.get('WEBHOOK_URL', f'http://{urllib.request.urlopen("http://ifconfig.me").read().decode().strip()}:{port}/webhook')
    r = tg_call('setWebhook', {'url': wh_url})
    log.info(f'Webhook set: {r}')
    
    server = http.server.HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()
PYTHON

# Systemd сервис для бота
cat > /etc/systemd/system/pawwork-bot.service << 'SERVICE'
[Unit]
Description=PawWork Telegram Bot
After=network.target ollama.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pawwork
ExecStart=/usr/bin/python3 /opt/pawwork/bot.py
Restart=always
RestartSec=10
Environment=TELEGRAM_TOKEN=PLACEHOLDER

[Install]
WantedBy=multi-user.target
SERVICE

# Подставляем токен
sed -i "s/PLACEHOLDER/$TELEGRAM_TOKEN/" /etc/systemd/system/pawwork-bot.service

systemctl daemon-reload
systemctl enable pawwork-bot 2>/dev/null || true
log "Telegram бот установлен в /opt/pawwork/bot.py"

# ─── 8. NGINX PROXY MANAGER ──────────────────────────────────────────────────
header "🌐 Nginx Proxy Manager + Мониторинг"

mkdir -p "$DOCKER_DIR/npm"
cat > "$DOCKER_DIR/npm/docker-compose.yml" << 'YML'
version: '3'
services:
  nginx-proxy-manager:
    image: 'jc21/nginx-proxy-manager:latest'
    restart: always
    ports:
      - '80:80'
      - '443:443'
      - '81:81'
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
YML

cd "$DOCKER_DIR/npm"
docker-compose up -d 2>/dev/null && log "NPM запущен :81" || warn "NPM не запустился"

# Uptime Kuma — мониторинг
mkdir -p "$DOCKER_DIR/kuma"
cat > "$DOCKER_DIR/kuma/docker-compose.yml" << 'YML'
version: '3'
services:
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    restart: always
    ports:
      - '3001:3001'
    volumes:
      - ./data:/app/data
YML

cd "$DOCKER_DIR/kuma"
docker-compose up -d 2>/dev/null && log "Uptime Kuma запущен :3001" || warn "Kuma не запустился"

# ─── 9. FIREWALL ──────────────────────────────────────────────────────────────
header "🔒 Firewall + Безопасность"

if command -v ufw &>/dev/null; then
    ufw --force reset 2>/dev/null || true
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8080/tcp
    ufw allow 9000/tcp   # Portainer
    ufw allow 3001/tcp   # Kuma
    ufw allow 81/tcp     # NPM
    ufw allow 11434/tcp  # Ollama
    ufw --force enable 2>/dev/null && log "Firewall настроен" || warn "Firewall не включился"
fi

# ─── 10. АВТО-СТАРТ ───────────────────────────────────────────────────────────
header "⏰ Настройка автозапуска"

systemctl daemon-reload 2>/dev/null || true
for svc in docker ollama openclaw pawwork-bot; do
    systemctl enable "$svc" 2>/dev/null || true
done

# ─── 11. ВЫВОД ─────────────────────────────────────────────────────────────────
header "✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО!"

# Получаем внешний IP
EXTERNAL_IP=$(curl -fsSL http://ifconfig.me 2>/dev/null || curl -fsSL https://api.ipify.org 2>/dev/null || echo "unknown")

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              🚀 PAWWORK VPS ULTIMATE READY                  ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo -e "║  🌐 Внешний IP:      ${CYAN}$EXTERNAL_IP${NC}                 ║"
echo "║                                                              ║"
echo -e "║  📊 Portainer:       ${CYAN}http://$EXTERNAL_IP:9000${NC}        ║"
echo -e "║  📈 Uptime Kuma:     ${CYAN}http://$EXTERNAL_IP:3001${NC}        ║"
echo -e "║  🌐 NPM:             ${CYAN}http://$EXTERNAL_IP:81${NC}          ║"
echo -e "║  🤖 Telegram Bot:    ${CYAN}@Gptzloy_bot${NC}                  ║"
echo -e "║  🦞 OpenClaw:        ${CYAN}http://localhost:3737${NC}          ║"
echo -e "║  🐳 Ollama API:      ${CYAN}http://localhost:11434${NC}         ║"
echo "║                                                              ║"
echo "║  Папки:                                                     ║"
echo "║    OpenClaw:  $OPENCLAW_DIR                     ║"
echo "║    CrewAI:    $CREWAI_DIR                       ║"
echo "║    Eliza:     $ELIZA_DIR                        ║"
echo "║    Bot:       $PAWWORK_DIR/bot.py               ║"
echo "║    Docker:    $DOCKER_DIR                       ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

info "${YELLOW}ВАЖНО:${NC}"
info "1. Открой Portainer: http://$EXTERNAL_IP:9000 — создай пароль при первом входе"
info "2. Настрой Uptime Kuma: http://$EXTERNAL_IP:3001 — добавь мониторинг сайтов"
info "3. Для домена: настрой NPM → Proxy Hosts → твой бот"
info "4. Telegram: напиши /start @Gptzloy_bot"
info ""
info "${GREEN}Чтобы перезапустить всё сразу:${NC}"
info "  systemctl restart docker ollama openclaw pawwork-bot"
info ""
info "${YELLOW}Логи:${NC}"
info "  journalctl -u pawwork-bot -f"
info "  journalctl -u openclaw -f"
