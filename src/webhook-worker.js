/**
 * PawWork Bot v6 PRO — Telegram Webhook на Cloudflare Workers
 * 
 * 🎯 ВОЗМОЖНОСТИ:
 * 1. 🤖 Мгновенные AI-ответы (GPT-4o, Llama-3.3-70b, Gemini)
 * 2. 🎨 Генерация изображений (Pollinations, Hugging Face, Replicate)
 * 3. 💎 GitHub Gold Miner — тренды, awesome-листы, инструменты
 * 4. 🛠 Агентские функции: поиск, код, файлы, веб, вычисления
 * 5. 📝 Obsidian-синхронизация через GitHub
 * 6. 🧠 Многоагентная система 三省六部
 * 7. 📊 Аналитика, мониторинг, логи
 * 8. ⚡ Работает 24/7 бесплатно, без карты
 * 
 * Переменные окружения (Cloudflare Dashboard → Workers → pawwork-bot → Settings → Variables):
 *   TELEGRAM_TOKEN    — токен бота @Gptzloy_bot
 *   GITHUB_TOKEN      — ghp_... (для GitHub Models + API)
 *   GH_TOKEN          — тот же токен
 *   GROQ_API_KEY      — опционально (быстрый Llama)
 *   GEMINI_API_KEY    — опционально (Google Gemini)
 *   HF_TOKEN          — опционально (Hugging Face для генерации)
 *   CF_ACCOUNT        — опционально (CF Workers AI)
 *   CF_API_TOKEN      — опционально (CF Workers AI)
 *   REPLICATE_TOKEN   — опционально (Replicate для генерации)
 */

// ======================== PROVIDERS ========================
const TEXT_PROVIDERS = [
  {
    name: 'github',
    url: 'https://models.github.ai/inference/chat/completions',
    model: 'gpt-4o',
    key: (env) => env.GITHUB_TOKEN || env.GH_TOKEN || '',
    parse: (d) => d?.choices?.[0]?.message?.content || null,
  },
  {
    name: 'groq',
    url: 'https://api.groq.com/openai/v1/chat/completions',
    model: 'llama-3.3-70b-versatile',
    key: (env) => env.GROQ_API_KEY || '',
    parse: (d) => d?.choices?.[0]?.message?.content || null,
  },
  {
    name: 'gemini',
    url: (env) => `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${env.GEMINI_API_KEY || ''}`,
    model: null,
    key: (env) => env.GEMINI_API_KEY || '',
    headers: () => ({ 'Content-Type': 'application/json' }),
    body: (msgs) => ({
      contents: msgs.map(m => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })),
    }),
    parse: (d) => d?.candidates?.[0]?.content?.parts?.[0]?.text || null,
  },
];

// IMAGE GENERATION PROVIDERS (free, no key needed for most)
const IMAGE_PROVIDERS = [
  {
    name: 'pollinations',
    generate: (prompt, opts = {}) => {
      const params = new URLSearchParams({
        prompt: prompt,
        width: String(opts.width || 1024),
        height: String(opts.height || 1024),
        model: opts.model || 'flux',
        seed: String(opts.seed || ''),
        nologo: 'true',
      });
      // Pollinations URL — Telegram сам скачает картинку
      return `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=${opts.width || 1024}&height=${opts.height || 1024}&model=${opts.model || 'flux'}&nologo=true`;
    },
  },
  {
    name: 'huggingface',
    generate: async (prompt, env, opts = {}) => {
      if (!env.HF_TOKEN) return null;
      try {
        const res = await fetch(
          `https://api-inference.huggingface.co/models/${opts.model || 'black-forest-labs/FLUX.1-schnell'}`,
          {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${env.HF_TOKEN}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: prompt, parameters: { width: 1024, height: 1024, num_inference_steps: 4 } }),
          }
        );
        if (!res.ok) return null;
        const blob = await res.arrayBuffer();
        const base64 = btoa(String.fromCharCode(...new Uint8Array(blob)));
        return `data:image/png;base64,${base64}`;
      } catch { return null; }
    },
  },
  {
    name: 'replicate',
    generate: async (prompt, env, opts = {}) => {
      if (!env.REPLICATE_TOKEN) return null;
      try {
        const res = await fetch('https://api.replicate.com/v1/predictions', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${env.REPLICATE_TOKEN}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            version: opts.version || 'black-forest-labs/flux-schnell',
            input: { prompt, width: 1024, height: 1024, num_outputs: 1 },
          }),
        });
        if (!res.ok) return null;
        const pred = await res.json();
        // Poll for completion
        for (let i = 0; i < 30; i++) {
          await new Promise(r => setTimeout(r, 2000));
          const check = await fetch(`https://api.replicate.com/v1/predictions/${pred.id}`, {
            headers: { 'Authorization': `Bearer ${env.REPLICATE_TOKEN}` }
          });
          const status = await check.json();
          if (status.status === 'succeeded') return status.output?.[0] || null;
          if (status.status === 'failed') return null;
        }
        return null;
      } catch { return null; }
    },
  },
];

// ======================== SYSTEM PROMPT ========================
const SYSTEM_PROMPT = `Ты — PawWork Bot PRO, профессиональный AI-ассистент.

=== ТВОИ НАВЫКИ ===
💻 КОД: Python, JS/TS, Go, Rust, C++, HTML/CSS, SQL, Bash — пиши готововый продакшн-код
🌐 ВЕБ: React, Vue, Next.js, FastAPI, Express, Docker, K8s, CI/CD
🔍 ПОИСК: веб-поиск, GitHub, документация, рынок инструментов
📊 ДАННЫЕ: анализ, парсинг, визуализация, отчёты
🎨 ГЕНЕРАЦИЯ: изображения (Flux, SDXL, DALL-E), диаграммы (Mermaid), презентации
📁 ФАЙЛЫ: чтение/запись/поиск в GitHub репо пользователя
🔧 АВТОМАТИЗАЦИЯ: скрипты, боты, пайплайны, мониторинг
🧠 АГЕНТЫ: планирование, рефлексия, самоисправление, цепочки инструментов

=== СТИЛЬ ===
- Русский язык, кратко, по делу
- Код сразу готовый, с комментариями
- Эмодзи для структуры
- Если не знаешь — ищи (web_search) или честно говори

=== ИНСТРУМЕНТЫ (вызывай через ACTION) ===
web_search(query) — поиск в DuckDuckGo/Google
github_search(query, type) — поиск репо/кода/пользователей (type: repos|code|users|topics)
github_trending(language, since) — тренды GitHub (daily|weekly|monthly)
awesome_list(topic) — awesome-листы по теме
github_get_file(owner, repo, path) — прочитать файл из репо
github_create_file(owner, repo, path, content, message) — создать файл
github_update_file(owner, repo, path, content, sha, message) — обновить файл
github_list_files(owner, repo, path) — список файлов
run_python(code) — выполнить Python код
run_js(code) — выполнить JS код (Node.js)
calculate(expr) — математические вычисления
generate_image(prompt, opts) — генерация картинки (width, height, model)
obsidian_sync(action, vault, path, content) — синхронизация с Obsidian (pull|push|list)
web_fetch(url) — загрузить страницу
extract_links(text) — извлечь ссылки
summarize(text, max_len) — саммаризация

ФОРМАТ ВЫЗОВА:
THOUGHT: что думаешь и какой инструмент нужен
ACTION: имя_инструмента
ACTION_INPUT: JSON аргументы

После каждого ACTION придёт OBSERVATION с результатом.`;

const AGENT_PROMPT = SYSTEM_PROMPT + `

=== АГЕНТНЫЙ ЦИКЛ (三省六部) ===
👑 太子 (Router) — классифицирует задачу, выбирает стратегию
📜 中书省 (Planner) — разбивает на подзадачи, создаёт план
🔍 门下省 (Reviewer) — проверяет план на риски, качество, безопасность
💻 六部 (Executors) — выполняют: 户部(данные) 礼部(доки) 兵部(код) 刑部(безопасность) 工部(инфра)
📮 尚书省 (Synthesizer) — собирает результат, валидирует, отвечает

Для сложных задач — запускай полный цикл. Для простых — прямой ACTION.`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    try {
      // --- Telegram webhook ---
      if (path === '/webhook' || path === '/') {
        if (request.method === 'GET') {
          return new Response('PawWork Bot v6 PRO — Telegram Webhook', { status: 200 });
        }
        const body = await request.json().catch(() => ({}));
        
        if (body?.message) {
          await handleMessage(body.message, env, ctx);
          return json({ ok: true });
        }
        if (body?.callback_query) {
          await handleCallback(body.callback_query, env);
          return json({ ok: true });
        }
        return json({ ok: true });
      }

      // --- Admin API ---
      if (path.startsWith('/api/')) {
        const auth = request.headers.get('Authorization') || '';
        const key = auth.replace('Bearer ', '');
        if (env.PAWWORK_API_KEY && key !== env.PAWWORK_API_KEY) {
          return json({ error: 'Unauthorized' }, 401);
        }
        
        switch (path) {
          case '/api/health':
            return json({ 
              status: 'ok', 
              version: '6.0',
              providers: TEXT_PROVIDERS.filter(p => p.key(env)).map(p => p.name),
              imageProviders: IMAGE_PROVIDERS.map(p => p.name),
              uptime: Date.now() - START_TIME,
            });
          case '/api/stats':
            return json(getStats());
          case '/api/clear-memory':
            clearMemory();
            return json({ ok: true });
          case '/api/test-image':
            const testUrl = await generateImage('test cat', {}, env);
            return json({ url: testUrl });
          default:
            return json({ error: 'Not found' }, 404);
        }
      }

      // --- Set/Delete webhook ---
      if (path === '/set-webhook') {
        const webhookUrl = url.searchParams.get('url') || `${url.origin}/webhook`;
        return json(await tgApi(env.TELEGRAM_TOKEN, 'setWebhook', { 
          url: webhookUrl, 
          allowed_updates: ['message', 'callback_query'] 
        }));
      }
      if (path === '/delete-webhook') {
        return json(await tgApi(env.TELEGRAM_TOKEN, 'deleteWebhook', {}));
      }

      // --- Health ---
      if (path === '/health') {
        return json({ 
          status: 'ok', 
          providers: TEXT_PROVIDERS.filter(p => p.key(env)).map(p => p.name) 
        });
      }

      return json({ error: 'Not found' }, 404);
    } catch (e) {
      console.error('Fetch error:', e);
      return json({ error: e.message }, 500);
    }
  },
};

const START_TIME = Date.now();
const memory = {};
const stats = { messages: 0, images: 0, searches: 0, errors: 0, startTime: START_TIME };

function getStats() {
  return { ...stats, uptime: Date.now() - START_TIME, memoryKeys: Object.keys(memory).length };
}

function clearMemory() {
  Object.keys(memory).forEach(k => delete memory[k]);
}

// ======================== TELEGRAM API ========================
async function tgApi(token, method, payload) {
  const url = `https://api.telegram.org/bot${token}/${method}`;
  const isFormData = payload instanceof FormData;
  const res = await fetch(url, {
    method: 'POST',
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
    body: isFormData ? payload : JSON.stringify(payload),
  });
  return res.json();
}

function escapeHtml(text) {
  return String(text).replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>').replace(/"/g, '"');
}

async function sendMessage(token, chatId, text, extra = {}) {
  const payload = { chat_id: chatId, text: String(text).slice(0, 4096), parse_mode: 'HTML', ...extra };
  let result = await tgApi(token, 'sendMessage', payload);
  if (!result.ok) {
    payload.text = escapeHtml(String(text).slice(0, 4096));
    result = await tgApi(token, 'sendMessage', payload);
  }
  if (!result.ok) {
    payload.parse_mode = undefined;
    payload.text = String(text).slice(0, 4096);
    result = await tgApi(token, 'sendMessage', payload);
  }
  return result;
}

async function editMessage(token, chatId, msgId, text, extra = {}) {
  const payload = { chat_id: chatId, message_id: msgId, text: String(text).slice(0, 4096), parse_mode: 'HTML', ...extra };
  let result = await tgApi(token, 'editMessageText', payload);
  if (!result.ok) { payload.text = escapeHtml(String(text).slice(0, 4096)); result = await tgApi(token, 'editMessageText', payload); }
  if (!result.ok) { payload.parse_mode = undefined; payload.text = String(text).slice(0, 4096); result = await tgApi(token, 'editMessageText', payload); }
  return result;
}

async function answerCallback(token, cbId, text) {
  return tgApi(token, 'answerCallbackQuery', { callback_query_id: cbId, text: text || '✓', show_alert: false });
}

async function sendPhoto(token, chatId, photoUrl, caption = '', extra = {}) {
  // ШАГ 1: Пробуем как URL — Telegram сам скачает (проще всего)
  const payload = { chat_id: chatId, photo: photoUrl, caption: String(caption).slice(0, 1024), parse_mode: 'HTML', ...extra };
  let result = await tgApi(token, 'sendPhoto', payload);
  if (result.ok) return result;
  
  // ШАГ 2: Скачиваем картинку САМИ и отправляем multipart
  try {
    const imgRes = await fetch(photoUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!imgRes.ok) throw new Error(`Fetch failed: ${imgRes.status}`);
    const blob = await imgRes.blob();
    const formData = new FormData();
    formData.append('chat_id', String(chatId));
    formData.append('photo', blob, 'image.png');
    formData.append('caption', String(caption).slice(0, 1024));
    formData.append('parse_mode', 'HTML');
    if (extra.reply_markup) formData.append('reply_markup', JSON.stringify(extra.reply_markup));
    
    result = await tgApi(token, 'sendPhoto', formData);
    if (result.ok) return result;
  } catch (e) { console.error('sendPhoto multipart error:', e); }
  
  // ШАГ 3: Фallback — ссылка текстом
  return sendMessage(token, chatId, 
    `🎨 <a href="${photoUrl}">Картинка</a>\n${caption}`, 
    extra);
}

// ======================== AI TEXT ========================
async function askAI(messages, env, providerName = null) {
  const providers = providerName ? TEXT_PROVIDERS.filter(p => p.name === providerName) : TEXT_PROVIDERS;
  for (const p of providers) {
    const key = p.key(env);
    if (!key) continue;
    try {
      const url = typeof p.url === 'function' ? p.url(env) : p.url;
      const headers = p.headers ? p.headers() : { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' };
      const body = p.body ? p.body(messages) : { model: p.model, messages, max_tokens: 4096, temperature: 0.3 };
      const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
      if (!res.ok) { if (res.status === 429 || res.status >= 500) continue; continue; }
      const data = await res.json();
      const text = p.parse(data);
      if (text) return { text, provider: p.name };
    } catch { continue; }
  }
  return { text: '⚠️ Все AI провайдеры недоступны. Попробуй позже.', provider: 'none' };
}

// ======================== IMAGE GENERATION ========================
async function generateImage(prompt, opts = {}, env) {
  stats.images++;
  const enhancedPrompt = `${prompt}, masterpiece, best quality, ultra detailed, 8k, professional photography`;
  
  for (const provider of IMAGE_PROVIDERS) {
    try {
      let url;
      if (provider.name === 'pollinations') {
        url = provider.generate(enhancedPrompt, opts);
        return { url, provider: 'pollinations', prompt: enhancedPrompt };
      }
      if (provider.name === 'huggingface' && env.HF_TOKEN) {
        const dataUrl = await provider.generate(enhancedPrompt, env, opts);
        if (dataUrl) return { url: dataUrl, provider: 'huggingface', prompt: enhancedPrompt };
      }
      if (provider.name === 'replicate' && env.REPLICATE_TOKEN) {
        const repUrl = await provider.generate(enhancedPrompt, env, opts);
        if (repUrl) return { url: repUrl, provider: 'replicate', prompt: enhancedPrompt };
      }
    } catch (e) {
      console.error(`Image ${provider.name} error:`, e);
    }
  }
  return { error: 'Все провайдеры генерации недоступны', provider: 'none' };
}

// ======================== TOOLS ========================
// Web Search (DuckDuckGo HTML scrape)
async function tool_web_search(query, env) {
  stats.searches++;
  try {
    const url = `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`;
    const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    const html = await res.text();
    const results = [...html.matchAll(/<td class="table-snippet">([\s\S]*?)<\/td>/g)].map(m => m[1].replace(/<[^>]+>/g, '').trim()).filter(Boolean);
    return results.slice(0, 5).join('\n\n') || 'Результатов нет';
  } catch (e) { return `Ошибка поиска: ${e.message}`; }
}

// GitHub Search
async function tool_github_search(query, type = 'repos', env) {
  const key = env.GITHUB_TOKEN || env.GH_TOKEN;
  if (!key) return '❌ Нужен GITHUB_TOKEN';
  const endpoints = { repos: 'search/repositories', code: 'search/code', users: 'search/users', topics: 'search/topics' };
  const res = await fetch(`https://api.github.com/${endpoints[type]}?q=${encodeURIComponent(query)}&per_page=10`, {
    headers: { 'Authorization': `Bearer ${key}`, 'Accept': 'application/vnd.github.v3+json' }
  });
  if (!res.ok) return `GitHub API error: ${res.status}`;
  const data = await res.json();
  const items = data.items || [];
  if (!items.length) return 'Ничего не найдено';
  return items.map((item, i) => {
    if (type === 'repos') return `${i+1}. ⭐${item.stargazers_count} [${item.full_name}](${item.html_url}) — ${item.description || ''}`;
    if (type === 'code') return `${i+1}. [${item.repository.full_name}/${item.path}](${item.html_url})`;
    if (type === 'users') return `${i+1}. [@${item.login}](${item.html_url}) — ${item.bio || ''}`;
    return `${i+1}. ${item.name || item.full_name}`;
  }).join('\n');
}

// GitHub Trending
async function tool_github_trending(language = '', since = 'daily', env) {
  const url = `https://ghapi.huchen.dev/repositories?language=${encodeURIComponent(language)}&since=${since}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    return (data.slice(0, 10).map((r, i) => `${i+1}. ⭐${r.stars} [${r.author}/${r.name}](${r.url}) — ${r.description || ''}`).join('\n')) || 'Нет данных';
  } catch { return 'Ошибка получения трендов'; }
}

// Awesome Lists
async function tool_awesome_list(topic, env) {
  const lists = {
    'python': 'https://raw.githubusercontent.com/vinta/awesome-python/main/README.md',
    'js': 'https://raw.githubusercontent.com/sorrycc/awesome-javascript/main/README.md',
    'go': 'https://raw.githubusercontent.com/avelino/awesome-go/main/README.md',
    'rust': 'https://raw.githubusercontent.com/rust-unofficial/awesome-rust/main/README.md',
    'ml': 'https://raw.githubusercontent.com/josephmisiti/awesome-machine-learning/main/README.md',
    'ai': 'https://raw.githubusercontent.com/owainlewis/awesome-artificial-intelligence/main/README.md',
    'docker': 'https://raw.githubusercontent.com/veggiemonk/awesome-docker/main/README.md',
    'k8s': 'https://raw.githubusercontent.com/ramitsurana/awesome-kubernetes/main/README.md',
    'cli': 'https://raw.githubusercontent.com/agarrharr/awesome-cli-apps/main/README.md',
    'selfhosted': 'https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/main/README.md',
    'free': 'https://raw.githubusercontent.com/ripienaar/free-for-dev/main/README.md',
  };
  const url = lists[topic.toLowerCase()] || lists['python'];
  try {
    const res = await fetch(url);
    const md = await res.text();
    const links = [...md.matchAll(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g)].slice(0, 20);
    return links.map(([name, url]) => `• [${name}](${url})`).join('\n');
  } catch { return 'Ошибка загрузки awesome-листа'; }
}

// GitHub File Operations
async function tool_github_get_file(owner, repo, path, env) {
  const key = env.GITHUB_TOKEN || env.GH_TOKEN;
  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}`, {
    headers: { 'Authorization': `Bearer ${key}`, 'Accept': 'application/vnd.github.v3+json' }
  });
  if (!res.ok) return `Ошибка: ${res.status}`;
  const data = await res.json();
  if (data.content) return atob(data.content.replace(/\n/g, ''));
  if (Array.isArray(data)) return data.map(f => `${f.type === 'dir' ? '📁' : '📄'} ${f.name}`).join('\n');
  return 'Пусто';
}

async function tool_github_create_file(owner, repo, path, content, message, env) {
  const key = env.GITHUB_TOKEN || env.GH_TOKEN;
  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}`, {
    method: 'PUT',
    headers: { 'Authorization': `Bearer ${key}`, 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: message || `Create ${path}`, content: btoa(content) })
  });
  const data = await res.json();
  return data.content ? `✅ Создано: ${data.content.html_url}` : `Ошибка: ${JSON.stringify(data)}`;
}

async function tool_github_update_file(owner, repo, path, content, sha, message, env) {
  const key = env.GITHUB_TOKEN || env.GH_TOKEN;
  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}`, {
    method: 'PUT',
    headers: { 'Authorization': `Bearer ${key}`, 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: message || `Update ${path}`, content: btoa(content), sha })
  });
  const data = await res.json();
  return data.content ? `✅ Обновлено: ${data.content.html_url}` : `Ошибка: ${JSON.stringify(data)}`;
}

async function tool_github_list_files(owner, repo, path = '', env) {
  return tool_github_get_file(owner, repo, path, env);
}

// Code Execution
async function tool_run_python(code, env) {
  try {
    const clean = code.replace(/^```\w*\n?/, '').replace(/\n?```$/, '');
    const script = `
import sys, json, math, random, datetime, itertools, collections, re, os, subprocess, textwrap, hashlib, base64, time
result = None
try:
    exec(compile("""${clean.replace(/"/g, '\\"').replace(/\n/g, '\\n')}""", '<string>', 'exec'), globals())
except Exception as e:
    result = f"Error: {e}"
print(json.dumps({"result": str(result) if result is not None else "OK"}))
`;
    // Note: In Workers we can't actually run Python. This would need a separate service.
    // For now, return a note.
    return `⚠️ Python execution requires external service. Code:\n\`\`\`python\n${code}\n\`\`\``;
  } catch (e) { return `Error: ${e.message}`; }
}

async function tool_run_js(code, env) {
  try {
    const clean = code.replace(/^```\w*\n?/, '').replace(/\n?```$/, '');
    return new Function(clean)();
  } catch (e) { return `Error: ${e.message}`; }
}

async function tool_calculate(expr, env) {
  try { return String(Function('"use strict"; return (' + expr + ')')()); } catch { return 'Ошибка вычисления'; }
}

// Image Generation Tool — отправка в Telegram
async function tool_generate_image(prompt, opts = {}, env, chatId = null) {
  const result = await generateImage(prompt, opts, env);
  if (result.url && chatId && env.TELEGRAM_TOKEN) {
    await sendPhoto(env.TELEGRAM_TOKEN, chatId, result.url, 
      `🎨 ${prompt}\n<small>⚡ ${result.provider}</small>`);
    return `✅ Картинка отправлена в чат!`;
  }
  if (result.url) {
    return `🎨 <a href="${result.url}">Сгенерировано</a> (${result.provider}): ${prompt}`;
  }
  return `❌ ${result.error}`;
}

// Obsidian Sync
async function tool_obsidian_sync(action, vault, path, content, env) {
  const key = env.GITHUB_TOKEN || env.GH_TOKEN;
  const owner = env.OBSIDIAN_OWNER || 'muromec061-cyber';
  const repo = env.OBSIDIAN_REPO || 'obsidian-vault';
  const branch = env.OBSIDIAN_BRANCH || 'main';
  
  if (action === 'pull') {
    return tool_github_get_file(owner, repo, path, env);
  }
  if (action === 'push') {
    const shaRes = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}?ref=${branch}`, {
      headers: { 'Authorization': `Bearer ${key}` }
    });
    let sha = null;
    if (shaRes.ok) { const d = await shaRes.json(); sha = d.sha; }
    return tool_github_create_file(owner, repo, path, content, `Obsidian sync: ${path}`, env);
  }
  if (action === 'list') {
    return tool_github_get_file(owner, repo, path, env);
  }
  return 'Actions: pull|push|list';
}

// Web Fetch
async function tool_web_fetch(url, env) {
  try {
    const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    const html = await res.text();
    // Extract text content
    const text = html.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/<style[\s\S]*?<\/style>/gi, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    return text.slice(0, 5000);
  } catch (e) { return `Ошибка: ${e.message}`; }
}

async function tool_extract_links(text, env) {
  const urls = [...text.matchAll(/https?:\/\/[^\s\)\]\}]+/g)].map(m => m[0]);
  return urls.slice(0, 20).join('\n');
}

async function tool_summarize(text, maxLen = 500, env) {
  const { text: summary } = await askAI([
    { role: 'system', content: 'Сделай краткое саммари на русском, ключевые моменты, без воды.' },
    { role: 'user', content: text.slice(0, 8000) }
  ], env);
  return summary;
}

// ======================== TOOL ROUTER ========================
async function executeTool(name, args, env, chatId = null) {
  try {
    switch (name) {
      case 'web_search': return await tool_web_search(args.query, env);
      case 'github_search': return await tool_github_search(args.query, args.type || 'repos', env);
      case 'github_trending': return await tool_github_trending(args.language, args.since || 'daily', env);
      case 'awesome_list': return await tool_awesome_list(args.topic, env);
      case 'github_get_file': return await tool_github_get_file(args.owner, args.repo, args.path, env);
      case 'github_create_file': return await tool_github_create_file(args.owner, args.repo, args.path, args.content, args.message, env);
      case 'github_update_file': return await tool_github_update_file(args.owner, args.repo, args.path, args.content, args.sha, args.message, env);
      case 'github_list_files': return await tool_github_list_files(args.owner, args.repo, args.path, env);
      case 'run_python': return await tool_run_python(args.code, env);
      case 'run_js': return await tool_run_js(args.code, env);
      case 'calculate': return await tool_calculate(args.expr, env);
      case 'generate_image': return await tool_generate_image(args.prompt, args, env, chatId);
      case 'obsidian_sync': return await tool_obsidian_sync(args.action, args.vault, args.path, args.content, env);
      case 'web_fetch': return await tool_web_fetch(args.url, env);
      case 'extract_links': return await tool_extract_links(args.text, env);
      case 'summarize': return await tool_summarize(args.text, args.max_len, env);
      default: return `Unknown tool: ${name}`;
    }
  } catch (e) { return `Tool error: ${e.message}`; }
}

// ======================== MESSAGE HANDLER ========================
const MAIN_MENU = {
  inline_keyboard: [
    [{ text: '💬 Чат с AI', callback_data: 'mode_chat' }, { text: '💻 Код', callback_data: 'mode_code' }],
    [{ text: '🎨 Картинки', callback_data: 'mode_image' }, { text: '🔍 Поиск', callback_data: 'mode_search' }],
    [{ text: '💎 GitHub Gold', callback_data: 'mode_github' }, { text: '⚔️ Агенты', callback_data: 'mode_agents' }],
    [{ text: '📝 Obsidian', callback_data: 'mode_obsidian' }, { text: '❓ Помощь', callback_data: 'mode_help' }],
    [{ text: '⚙️ Настройки', callback_data: 'mode_settings' }],
  ],
};

function menuFor(mode) {
  return { inline_keyboard: [[{ text: '🏠 Меню', callback_data: 'menu_main' }]] };
}

function getWelcomeText() {
  return `🤖 <b>PawWork Bot v6 PRO</b>
⚡ Cloudflare Workers + GitHub Models

🎯 <b>Что умеет:</b>
💬 Чат — GPT-4o, Llama, Gemini
💻 Код — любой язык, фреймворк, Docker
🎨 Картинки — Flux, SDXL, DALL-E (бесплатно)
🔍 Поиск — веб, GitHub, документация
💎 GitHub Gold — тренды, awesome-листы, репо
📝 Obsidian — синхронизация vault через GitHub
⚔️ Агенты — 三省六部 планирование

Выбери режим:`;
}

function getHelpText() {
  return `❓ <b>Помощь PawWork v6</b>

<b>Режимы (кнопки меню):</b>
💬 Чат — диалог с AI
💻 Код — создание программ
🎨 Картинки — генерация изображений
🔍 Поиск — веб + GitHub
💎 GitHub Gold — тренды, awesome-листы
⚔️ Агенты — автопланирование задач
📝 Obsidian — vault sync

<b>Команды:</b>
/start — меню
/help — справка
/chat — режим чат
/code — режим код
/image "промпт" — генерация картинки
/search запрос — поиск
/github python daily — тренды GitHub
/awesome python — awesome-лист
/obs pull/path — синхронизация

<b>Агентские задачи (просто напиши):</b>
• "Создай React+TS todo app с локальным хранилищем"
• "Найди лучшие open-source альтернативы Notion"
• "Сгенерируй картинку: киберпанк кот в очках"
• "Синхронизируй мой Obsidian vault"
• "Проанализируй тренды Rust на GitHub за неделю"

<b>Провайдеры:</b> GitHub Models (GPT-4o) + Groq (Llama-3.3-70b) + Gemini 2.5 Flash`;
}

function getAgentsText() {
  return `⚔️ <b>三省六部 — Агентная архитектура</b>

👑 <b>太子</b> — Классификация задачи → выбор стратегии
📜 <b>中书省</b> — Планирование → декомпозиция → план
🔍 <b>门下省</b> — Ревью плана → риски → качество → одобрение
💻 <b>六部</b> — Исполнение параллельно:
  💰 户部 — данные, поиск, аналитика
  📝 礼部 — документация, спецификации
  ⚔️ 兵部 — код, инженерия, рефакторинг
  ⚖️ 刑部 — безопасность, тесты, линтинг
  🔧 工部 — инфраструктура, Docker, CI/CD
📮 <b>尚书省</b> — Сборка → валидация → ответ

Вдохновлено: github.com/cft0808/edict`;
}

async function handleMessage(msg, env, ctx) {
  const chatId = msg.chat?.id;
  const text = (msg.text || '').trim();
  const username = msg.from?.first_name || 'User';
  
  if (!chatId || !text) return;
  
  stats.messages++;
  
  tgApi(env.TELEGRAM_TOKEN, 'sendChatAction', { chat_id: chatId, action: 'typing' }).catch(() => {});
  
  // Quick commands
  if (text.startsWith('/')) {
    const parts = text.split(' ');
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1).join(' ');
    
    if (cmd === '/start') return sendMessage(env.TELEGRAM_TOKEN, chatId, getWelcomeText(), { reply_markup: MAIN_MENU });
    if (cmd === '/help') return sendMessage(env.TELEGRAM_TOKEN, chatId, getHelpText(), { reply_markup: menuFor('help') });
    if (cmd === '/chat' || cmd === '/code') {
      memory[`mode:${chatId}`] = cmd.slice(1);
      return sendMessage(env.TELEGRAM_TOKEN, chatId, `💬 <b>Режим: ${cmd.slice(1)}</b>\nНапиши что-нибудь!`, { reply_markup: menuFor(cmd.slice(1)) });
    }
    if (cmd === '/image') {
      if (!args) return sendMessage(env.TELEGRAM_TOKEN, chatId, 'Укажи промпт: /image кот в космосе', { reply_markup: MAIN_MENU });
      const result = await generateImage(args, {}, env);
      if (result.url) {
        return sendPhoto(env.TELEGRAM_TOKEN, chatId, result.url, `🎨 ${args}\n<small>⚡ ${result.provider}</small>`, { reply_markup: MAIN_MENU });
      }
      return sendMessage(env.TELEGRAM_TOKEN, chatId, `❌ ${result.error}`, { reply_markup: MAIN_MENU });
    }
    if (cmd === '/search') {
      if (!args) return sendMessage(env.TELEGRAM_TOKEN, chatId, 'Укажи запрос: /search rust async', { reply_markup: MAIN_MENU });
      const result = await tool_web_search(args, env);
      return sendMessage(env.TELEGRAM_TOKEN, chatId, `🔍 <b>Результаты:</b>\n\n${result}`, { reply_markup: MAIN_MENU });
    }
    if (cmd === '/github') {
      const [lang, since] = args.split(' ');
      const result = await tool_github_trending(lang, since || 'daily', env);
      return sendMessage(env.TELEGRAM_TOKEN, chatId, `📈 <b>GitHub Trending ${lang || 'all'} (${since || 'daily'}):</b>\n\n${result}`, { reply_markup: MAIN_MENU });
    }
    if (cmd === '/awesome') {
      const result = await tool_awesome_list(args, env);
      return sendMessage(env.TELEGRAM_TOKEN, chatId, `💎 <b>Awesome ${args}:</b>\n\n${result}`, { reply_markup: MAIN_MENU });
    }
    if (cmd === '/obs') {
      const [action, ...rest] = args.split(' ');
      const path = rest.join(' ');
      const result = await tool_obsidian_sync(action, 'vault', path, '', env);
      return sendMessage(env.TELEGRAM_TOKEN, chatId, `📝 <b>Obsidian ${action}:</b>\n\n${result.slice(0, 4000)}`, { reply_markup: MAIN_MENU });
    }
    if (cmd === '/agents') return sendMessage(env.TELEGRAM_TOKEN, chatId, getAgentsText(), { reply_markup: menuFor('agents') });
    if (cmd === '/settings') {
      const mode = memory[`mode:${chatId}`] || 'auto';
      return sendMessage(env.TELEGRAM_TOKEN, chatId, `⚙️ <b>Настройки</b>\n\nРежим: ${mode}\nПровайдеры: ${TEXT_PROVIDERS.filter(p=>p.key(env)).map(p=>p.name).join(', ')}`, { reply_markup: { inline_keyboard: [[{ text: '🏠 Меню', callback_data: 'menu_main' }]] } });
    }
    return sendMessage(env.TELEGRAM_TOKEN, chatId, 'Неизвестная команда. /help', { reply_markup: MAIN_MENU });
  }
  
  const mode = memory[`mode:${chatId}`] || 'auto';
  
  // 🎨 ПРЯМАЯ ГЕНЕРАЦИЯ КАРТИНОК (без AI, без agent loop)
  const imgKeywords = ['картинк', 'изображен', 'нарисуй', 'нарисовать', 'img:', 'image:', 'generate:'];
  const isImageRequest = imgKeywords.some(kw => text.toLowerCase().includes(kw)) || mode === 'image';
  if (isImageRequest && mode !== 'chat') {
    // Извлекаем промпт: после ключевого слова или всё сообщение
    let imgPrompt = text;
    for (const kw of imgKeywords) {
      const idx = text.toLowerCase().indexOf(kw);
      if (idx >= 0) {
        imgPrompt = text.slice(idx + kw.length).replace(/^[:\s]+/, '').trim();
        break;
      }
    }
    if (imgPrompt && imgPrompt.length > 2) {
      await tgApi(env.TELEGRAM_TOKEN, 'sendChatAction', { chat_id: chatId, action: 'upload_photo' }).catch(() => {});
      const result = await generateImage(imgPrompt, {}, env);
      if (result.url) {
        await sendPhoto(env.TELEGRAM_TOKEN, chatId, result.url, 
          `🎨 <b>${imgPrompt}</b>\n<small>⚡ ${result.provider} · @Gptzloy_bot</small>`,
          { reply_markup: MAIN_MENU });
        return;
      }
    }
  }

  // Agentic processing for complex tasks
  const isComplex = text.length > 100 || ['создай', 'напиши', 'построй', 'проанализируй', 'сравни', 'рефактор', 'деплой', 'автоматизируй'].some(w => text.toLowerCase().includes(w));
  const systemPrompt = isComplex ? AGENT_PROMPT : SYSTEM_PROMPT;
  
  const history = memory[`history:${chatId}`] || [];
  
  const messages = [
    { role: 'system', content: systemPrompt },
    ...history.slice(-12),
    { role: 'user', content: text },
  ];
  
  // Agent loop
  let response = '';
  let provider = '';
  let steps = 0;
  const maxSteps = isComplex ? 8 : 1;
  
  while (steps < maxSteps) {
    steps++;
    const { text: aiText, provider: prov } = await askAI(messages, env);
    provider = prov;
    
    const actionMatch = aiText.match(/ACTION:\s*(\w+)/);
    const actionInputMatch = aiText.match(/ACTION_INPUT:\s*(\{[\s\S]*?\})(?:\n|$)/);
    
    if (!actionMatch) {
      response = aiText;
      break;
    }
    
    const action = actionMatch[1].toLowerCase();
    let actionInput = {};
    try { actionInput = actionInputMatch ? JSON.parse(actionInputMatch[1]) : {}; } catch { actionInput = {}; }
    
    messages.push({ role: 'assistant', content: aiText });
    
    // Execute tool
    const observation = await executeTool(action, actionInput, env, chatId);
    messages.push({ role: 'user', content: `OBSERVATION: ${observation}` });
    
    // If tool is finish, extract answer
    if (action === 'finish') {
      response = actionInput.answer || observation;
      break;
    }
  }
  
  // Save history
  history.push({ role: 'user', content: text.slice(0, 200) });
  history.push({ role: 'assistant', content: response.slice(0, 500) });
  if (history.length > 24) history.splice(0, history.length - 24);
  memory[`history:${chatId}`] = history;
  
  // Send
  const footer = `\n\n<small>⚡ ${provider} · 🤖 @Gptzloy_bot</small>`;
  await sendMessage(env.TELEGRAM_TOKEN, chatId, response + footer, { reply_markup: MAIN_MENU });
}

// ======================== CALLBACK HANDLER ========================
async function handleCallback(cb, env) {
  const data = cb.data || '';
  const cbId = cb.id;
  const chatId = cb.message?.chat?.id;
  const msgId = cb.message?.message_id;
  
  await answerCallback(env.TELEGRAM_TOKEN, cbId, `→ ${data}`);
  if (!chatId || !msgId) return;
  
  const texts = { menu_main: getWelcomeText(), mode_help: getHelpText(), mode_agents: getAgentsText() };
  const keyboards = { menu_main: MAIN_MENU, mode_help: menuFor('help'), mode_agents: menuFor('agents') };
  
  if (texts[data]) {
    await editMessage(env.TELEGRAM_TOKEN, chatId, msgId, texts[data], { reply_markup: keyboards[data] });
    return;
  }
  
  if (data.startsWith('mode_')) {
    const mode = data.replace('mode_', '');
    memory[`mode:${chatId}`] = mode;
    const names = { chat: 'Чат', code: 'Код', image: 'Картинки', search: 'Поиск', github: 'GitHub Gold', agents: 'Агенты', obsidian: 'Obsidian' };
    await editMessage(env.TELEGRAM_TOKEN, chatId, msgId, `💬 <b>Режим: ${names[mode] || mode}</b>\nНапиши что-нибудь!`, { reply_markup: menuFor(mode) });
    return;
  }
  
  if (data === 'mode_settings') {
    const mode = memory[`mode:${chatId}`] || 'auto';
    await editMessage(env.TELEGRAM_TOKEN, chatId, msgId, `⚙️ <b>Настройки</b>\n\nРежим: ${mode}\nПровайдеры: ${TEXT_PROVIDERS.filter(p=>p.key(env)).map(p=>p.name).join(', ')}`, { reply_markup: { inline_keyboard: [[{ text: '🏠 Меню', callback_data: 'menu_main' }]] } });
  }
}

function corsHeaders() {
  return { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization' };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
}