#!/usr/bin/env python3
"""
PawWork Bot — Telegram bot with REAL image generation
Runs on Replit 24/7 (free) with UptimeRobot pings
"""

import os
import io
import json
import logging
import asyncio
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('pawwork-replit')

# ─── Config ───────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')  # set after deploy: https://<replit-name>.<user>.repl.co/webhook
POLLINATIONS_BASE = 'https://image.pollinations.ai/prompt'
DEFAULT_MODEL = 'flux'
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024

# ─── Helpers ──────────────────────────────────────────────────────────────────

def tg_url(method):
    return f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}'

def tg_call(method, data):
    """Call Telegram Bot API"""
    import urllib.request
    req = urllib.request.Request(tg_url(method), data=json.dumps(data).encode(), 
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error(f'TG API error {method}: {e}')
        return {'ok': False}

def send_message(chat_id, text, **extra):
    payload = {'chat_id': chat_id, 'text': str(text)[:4096], 'parse_mode': 'HTML', **extra}
    return tg_call('sendMessage', payload)

def send_photo_url(chat_id, photo_url, caption=''):
    """Send photo via URL — Telegram downloads it"""
    payload = {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': str(caption)[:1024],
        'parse_mode': 'HTML'
    }
    return tg_call('sendPhoto', payload)

def send_photo_data(chat_id, image_data, caption=''):
    """Send photo as multipart upload"""
    import mimetypes
    # Build multipart form manually or use requests-like approach
    # Using telegram-upload approach via urllib
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body_parts = []
    
    def add_field(name, value):
        body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n')
    
    def add_file(name, filename, data):
        body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: image/jpeg\r\n\r\n')
        body_parts.append(data)
        body_parts.append('\r\n')
    
    add_field('chat_id', str(chat_id))
    add_file('photo', 'image.jpg', image_data)
    add_field('caption', str(caption)[:1024])
    add_field('parse_mode', 'HTML')
    body_parts.append(f'--{boundary}--\r\n')
    
    body = b''
    for part in body_parts:
        if isinstance(part, str):
            body += part.encode('utf-8')
        else:
            body += part
    
    req = urllib.request.Request(tg_url('sendPhoto'), data=body,
                                 headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error(f'sendPhoto multipart error: {e}')
        return {'ok': False}

# ─── Image Generation ─────────────────────────────────────────────────────────

def generate_pollinations(prompt):
    """Generate image via Pollinations.ai, returns (url, image_bytes or None)"""
    safe_prompt = urllib.parse.quote(prompt)
    url = f'{POLLINATIONS_BASE}/{safe_prompt}?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}&model={DEFAULT_MODEL}&nologo=true'
    
    log.info(f'Pollinations URL: {url}')
    
    # Try to download the image
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            img_data = resp.read()
            content_type = resp.headers.get('Content-Type', '')
            log.info(f'Pollinations response: {len(img_data)} bytes, type={content_type}')
            if len(img_data) > 1000 and ('image' in content_type or content_type.startswith('application/octet')):
                return url, img_data
            return url, None
    except Exception as e:
        log.error(f'Pollinations download error: {e}')
        return url, None

# ─── Message Handler ──────────────────────────────────────────────────────────

def handle_message(chat_id, text):
    """Process incoming message"""
    log.info(f'Message from {chat_id}: {text[:50]}')
    
    if not text:
        return
    
    # Commands
    if text.startswith('/'):
        parts = text.split()
        cmd = parts[0].lower()
        args = ' '.join(parts[1:])
        
        if cmd == '/start':
            return send_message(chat_id, 
                '🤖 <b>PawWork Replit Bot</b>\n\n'
                '🎨 <b>Генерация изображений</b>\n'
                '• /image кот в космосе\n'
                '• Или просто напиши: "нарисуй ..."\n\n'
                '⚡ Pollinations.ai + Telegram\n'
                '24/7 бесплатно на Replit')
        
        if cmd == '/help':
            return send_message(chat_id,
                '🎨 <b>Команды:</b>\n'
                '/image &lt;промпт&gt; — сгенерировать картинку\n'
                '• Или просто: "нарисуй ..."\n\n'
                'Примеры:\n'
                '/image киберпанк кот в космосе\n'
                'нарисуй красивый закат над морем')
        
        if cmd == '/image':
            if not args:
                return send_message(chat_id, 'Укажи промпт: /image кот в космосе')
            return generate_and_send(chat_id, args)
        
        return send_message(chat_id, 'Неизвестная команда. /help')
    
    # Keyword detection
    img_keywords = ['картинк', 'изображен', 'нарисуй', 'нарисовать']
    is_img = any(kw in text.lower() for kw in img_keywords)
    
    if is_img:
        # Extract prompt after keyword
        prompt = text
        for kw in img_keywords:
            idx = text.lower().find(kw)
            if idx >= 0:
                after = text[idx + len(kw):].lstrip(': ').strip()
                if after:
                    prompt = after
                    break
        return generate_and_send(chat_id, prompt)
    
    # Default: echo / help
    return send_message(chat_id,
        '🎨 Напиши "нарисуй ..." или используй /image\n'
        'Например: /image киберпанк кот программист')

def generate_and_send(chat_id, prompt):
    """Generate image and send to chat"""
    log.info(f'Generating: {prompt}')
    
    # Show typing
    send_message(chat_id, f'🎨 Генерирую: <b>{prompt}</b>...')
    
    url, img_data = generate_pollinations(prompt)
    
    if img_data and len(img_data) > 1000:
        # Send as multipart upload
        result = send_photo_data(chat_id, img_data, f'🎨 {prompt}')
        if result.get('ok'):
            return
        # Fallback: send URL
        result = send_photo_url(chat_id, url, f'🎨 {prompt}')
        if result.get('ok'):
            return
    else:
        # Send URL directly
        result = send_photo_url(chat_id, url, f'🎨 {prompt}')
        if result.get('ok'):
            return
    
    # Final fallback
    send_message(chat_id, f'🎨 <a href="{url}">Картинка</a>: {prompt}')

# ─── HTTP Server ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'pawwork-replit-bot'}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        
        if self.path == '/webhook':
            try:
                data = json.loads(body)
                chat_id = None
                text = None
                
                if 'message' in data:
                    chat_id = data['message'].get('chat', {}).get('id')
                    text = (data['message'].get('text') or '').strip()
                elif 'callback_query' in data:
                    cb = data['callback_query']
                    chat_id = cb.get('message', {}).get('chat', {}).get('id')
                    # Handle callback if needed
                
                if chat_id and text:
                    handle_message(chat_id, text)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())
            except Exception as e:
                log.error(f'Webhook error: {e}')
                self.send_response(200)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        log.info(f'HTTP: {format % args}')

def set_webhook():
    """Set Telegram webhook to this server"""
    if not WEBHOOK_URL:
        log.warning('WEBHOOK_URL not set, skipping webhook setup')
        return
    
    url = f'{WEBHOOK_URL.rstrip("/")}/webhook'
    result = tg_call('setWebhook', {'url': url, 'allowed_updates': ['message', 'callback_query']})
    log.info(f'Webhook set: {result}')

def run():
    port = int(os.environ.get('PORT', 8080))
    log.info(f'Starting server on port {port}')
    
    set_webhook()
    
    server = HTTPServer(('0.0.0.0', port), Handler)
    log.info(f'Server running on http://0.0.0.0:{port}')
    log.info(f'Webhook URL: {WEBHOOK_URL}/webhook')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        log.error('TELEGRAM_TOKEN not set!')
    else:
        run()
