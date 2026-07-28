/**
 * PawWork Bot v8 — FULL 24/7 Telegram Bot on Cloudflare Workers
 * 
 * Работает 24/7 бесплатно. Codespaces просыпается только для тяжёлых агентов.
 * 
 * Переменные окружения (Settings → Variables):
 *   TELEGRAM_TOKEN    — токен @Gptzloy_bot
 *   GITHUB_TOKEN      — ghp_... (GitHub Models, API)
 *   GROQ_API_KEY      — опционально (быстрый Llama)
 *   GEMINI_API_KEY    — опционально (Google Gemini)
 *   HF_TOKEN          — опционально (Hugging Face)
 *   CODESPACE_NAME    — имя codespace для автозапуска (опционально)
 *   GH_USERNAME       — muromec061-cyber (для старта codespace)
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors() });
    
    // --- Webhook ---
    if (path === '/webhook' || path === '/') {
      if (request.method === 'GET') return new Response('PawWork v8 24/7', { status: 200 });
      const body = await request.json().catch(() => ({}));
      if (body?.message) { ctx.waitUntil(handleMessage(body.message, env)); return json({ ok: true }); }
      if (body?.callback_query) { ctx.waitUntil(handleCallback(body.callback_query, env)); return json({ ok: true }); }
      return json({ ok: true });
    }
    
    // --- API ---
    if (path === '/set-webhook') {
      const whUrl = url.searchParams.get('url') || `${url.origin}/webhook`;
      return json(await tg(env.TELEGRAM_TOKEN, 'setWebhook', { url: whUrl, allowed_updates: ['message', 'callback_query'] }));
    }
    if (path === '/health') return json({ status: 'ok', version: '8.0', uptime: Date.now() - START_TIME });
    
    return json({ error: 'Not found' }, 404);
  },
};

// ═══════════════════════════════ CONSTS ═════════════════════════
const START_TIME = Date.now();
const TEXT_PROVIDERS = [
  { name: 'github', url: 'https://models.github.ai/inference/chat/completions', model: 'gpt-4o',
    key: (env) => env.GITHUB_TOKEN || '', parse: (d) => d?.choices?.[0]?.message?.content || null },
  { name: 'groq', url: 'https://api.groq.com/openai/v1/chat/completions', model: 'llama-3.3-70b-versatile',
    key: (env) => env.GROQ_API_KEY || '', parse: (d) => d?.choices?.[0]?.message?.content || null },
  { name: 'gemini', url: (env) => `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${env.GEMINI_API_KEY || ''}`,
    key: (env) => env.GEMINI_API_KEY || '', parse: (d) => d?.candidates?.[0]?.content?.parts?.[0]?.text || null,
    body: (msgs) => ({ contents: msgs.map(m => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })) }) },
];

// ═══════════════════════ ALL 30+ AGENTS ═════════════════════════
const AGENTS = {
  // Python Frameworks
  crewai: { desc: 'Ролевые AI-агенты', cat: 'python', needsCode: true },
  autogen: { desc: 'Multi-agent (Microsoft)', cat: 'python', needsCode: true },
  ag2: { desc: 'AG2 (форк AutoGen)', cat: 'python', needsCode: true },
  langgraph: { desc: 'Графовые агенты', cat: 'python', needsCode: true },
  llamaindex: { desc: 'RAG фреймворк', cat: 'python', needsCode: true },
  haystack: { desc: 'NLP пайплайны', cat: 'python', needsCode: true },
  pydanticai: { desc: 'Типизированные AI', cat: 'python', needsCode: true },
  smolagents: { desc: 'Агенты HuggingFace', cat: 'python', needsCode: true },
  camel: { desc: 'CAMEL-AI ролевые', cat: 'python', needsCode: true },
  metagpt: { desc: 'AI команда разработки', cat: 'python', needsCode: true },
  'semantic-kernel': { desc: 'Microsoft Semantic Kernel', cat: 'python', needsCode: true },
  superagi: { desc: 'SuperAGI автономные', cat: 'python', needsCode: true },
  babyagi: { desc: 'BabyAGI', cat: 'python', needsCode: true },
  swarms: { desc: 'Стаи агентов', cat: 'python', needsCode: true },
  phidata: { desc: 'AI ассистенты', cat: 'python', needsCode: true },
  'open-interpreter': { desc: 'AI интерпретатор', cat: 'python', needsCode: true },
  aider: { desc: 'AI парный программист', cat: 'python', needsCode: true },
  'gpt-researcher': { desc: 'AI исследователь', cat: 'python', needsCode: true },
  devika: { desc: 'AI разработчик', cat: 'python', needsCode: true },
  forge: { desc: 'Forge агенты', cat: 'python', needsCode: true },
  // CLI / Node
  openclaw: { desc: 'OpenClaw CLI (384k⭐)', cat: 'node', needsCode: true },
  autoclaw: { desc: 'AutoClaw CLI', cat: 'node', needsCode: true },
  claudeclaw: { desc: 'Claude Code CLI', cat: 'node', needsCode: true },
  goose: { desc: 'Goose AI CLI', cat: 'node', needsCode: true },
  lightagent: { desc: 'LightAgent CLI', cat: 'node', needsCode: true },
  // Heavy
  openhands: { desc: 'OpenHands AI Developer', cat: 'heavy', needsCode: true },
  opendevin: { desc: 'OpenDevin', cat: 'heavy', needsCode: true },
  agentgpt: { desc: 'AgentGPT', cat: 'heavy', needsCode: true },
  // Built-in (no codespace needed)
  'ai': { desc: 'Умный AI (GPT-4o)', cat: 'builtin', needsCode: false },
  'image': { desc: 'Генерация картинок', cat: 'builtin', needsCode: false },
  'gold': { desc: 'GitHub Gold Miner', cat: 'builtin', needsCode: false },
  'search': { desc: 'Веб-поиск', cat: 'builtin', needsCode: false },
};
const AGENT_NAMES = Object.keys(AGENTS);
const CODESPACE_AGENTS = AGENT_NAMES.filter(n => AGENTS[n].needsCode);

// ═══════════════════════ TELEGRAM HELPERS ═══════════════════════
async function tg(token, method, payload) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.json();
}

function h(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

async function send(token, chatId, text, extra = {}) {
  for (const mode of ['HTML', undefined]) {
    const p = { chat_id: chatId, text: String(text).slice(0, 4096), parse_mode: mode, disable_web_page_preview: true, ...extra };
    const r = await tg(token, 'sendMessage', p);
    if (r.ok) return r;
  }
}

async function sendMD(token, chatId, text, extra = {}) {
  return tg(token, 'sendMessage', { chat_id: chatId, text: String(text).slice(0, 4096), parse_mode: 'Markdown', ...extra });
}

async function sendPhoto(token, chatId, photoUrl, caption, extra = {}) {
  const r = await tg(token, 'sendPhoto', { chat_id: chatId, photo: photoUrl, caption: String(caption).slice(0, 1024), parse_mode: 'HTML', ...extra });
  if (r.ok) return r;
  // Fallback: download + multipart upload
  try {
    const img = await fetch(photoUrl);
    if (!img.ok) throw new Error('fetch failed');
    const blob = await img.blob();
    const fd = new FormData();
    fd.append('chat_id', String(chatId));
    fd.append('photo', blob, 'img.png');
    fd.append('caption', String(caption).slice(0, 1024));
    fd.append('parse_mode', 'HTML');
    return tg(token, 'sendPhoto', fd);
  } catch {
    return send(token, chatId, `🎨 <a href="${photoUrl}">Картинка</a>\n${caption}`);
  }
}

function kb(buttons) {
  return { inline_keyboard: buttons.map(row => row.map(b => ({ text: b[0], callback_data: b[1] }))) };
}

function menuKb() {
  return kb([
    [('⚔️ Агенты', '/agents'), ('🎨 Картинка', '/image ')],
    [('⛏ Gold Miner', '/gold'), ('🤖 AI', '/ai ')],
    [('ℹ️ Статус', '/status'), ('❓ Help', '/help')],
  ]);
}

// ═══════════════════════ AI & TOOLS ═════════════════════════════
async function askAI(messages, env) {
  for (const p of TEXT_PROVIDERS) {
    const key = p.key(env);
    if (!key) continue;
    try {
      const url = typeof p.url === 'function' ? p.url(env) : p.url;
      const hdrs = p.headers ? p.headers() : { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' };
      const body = p.body ? p.body(messages) : { model: p.model, messages, max_tokens: 4096 };
      const res = await fetch(url, { method: 'POST', headers: hdrs, body: JSON.stringify(body) });
      if (!res.ok) continue;
      const text = p.parse(await res.json());
      if (text) return { text, provider: p.name };
    } catch { continue; }
  }
  return { text: '⚠️ AI провайдеры недоступны', provider: 'none' };
}

function genImage(prompt, style = 'flux') {
  const models = { flux: 'flux', anime: 'flux-anime', real: 'flux-realism', '3d': 'flux-3d' };
  return `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt + ', masterpiece, high quality')}?width=1024&height=1024&model=${models[style] || 'flux'}&nologo=true`;
}

async function goldMiner(lang = '', env) {
  const days = 7;
  const since = new Date(Date.now() - days * 86400000).toISOString().split('T')[0];
  let q = `created:>${since}+stars:>100`;
  if (lang) q += `+language:${lang}`;
  const headers = { 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'PawWork' };
  if (env.GITHUB_TOKEN) headers['Authorization'] = `token ${env.GITHUB_TOKEN}`;
  try {
    const res = await fetch(`https://api.github.com/search/repositories?q=${encodeURIComponent(q)}&sort=stars&order=desc&per_page=10`, { headers });
    if (!res.ok) return `❌ GitHub API: ${res.status}`;
    const data = await res.json();
    if (!data.items?.length) return '❌ Ничего не найдено';
    return '🔥 <b>GitHub Gold Miner</b>\n— Топ проектов —\n\n' + data.items.map((item, i) =>
      `${i+1}. <b>${h(item.full_name)}</b>\n   ⭐ ${item.stargazers_count.toLocaleString()} | 🛠 ${h(item.language || '?')}\n   ${h((item.description || '').slice(0, 120))}\n   <a href="${item.html_url}">Открыть</a>`
    ).join('\n');
  } catch (e) { return `❌ Ошибка: ${h(e.message)}`; }
}

async function checkCodespace(env) {
  if (!env.CODESPACE_NAME) return 'stopped';
  const headers = { 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'PawWork' };
  if (env.GITHUB_TOKEN) headers['Authorization'] = `token ${env.GITHUB_TOKEN}`;
  try {
    const res = await fetch(`https://api.github.com/user/codespaces/${env.CODESPACE_NAME}`, { headers });
    if (!res.ok) return 'unknown';
    const cs = await res.json();
    return cs.state || 'unknown';
  } catch { return 'unknown'; }
}

async function startCodespace(env) {
  if (!env.CODESPACE_NAME || !env.GITHUB_TOKEN) return false;
  try {
    const res = await fetch(`https://api.github.com/user/codespaces/${env.CODESPACE_NAME}/start`, {
      method: 'POST', headers: { 'Authorization': `token ${env.GITHUB_TOKEN}`, 'Accept': 'application/vnd.github.v3+json' }
    });
    return res.ok;
  } catch { return false; }
}

// ═══════════════════════ COMMAND HANDLER ═════════════════════════
async function handleMessage(msg, env) {
  const chatId = msg.chat?.id;
  const text = (msg.text || '').trim();
  if (!chatId || !text) return;

  const cmd = text.split(' ')[0].toLowerCase();
  const args = text.includes(' ') ? text.slice(text.indexOf(' ') + 1) : '';
  const token = env.TELEGRAM_TOKEN;

  // ── /start /status ──
  if (['/start', '/status', '/info'].includes(cmd)) {
    const csState = await checkCodespace(env);
    const statusIcon = { 'available': '✅', 'starting': '🔄', 'stopped': '💤', 'unknown': '❓' };
    
    return send(token, chatId,
      `🤖 <b>PawWork Ultimate v8 — 24/7</b>\n` +
      `📍 Cloudflare Workers (всегда включён)\n` +
      `🔮 Всего агентов: <b>${AGENT_NAMES.length}</b>\n` +
      `⚡ Встроенных: <b>${AGENT_NAMES.filter(n => !AGENTS[n].needsCode).length}</b>\n` +
      `🖥 Codespaces: ${statusIcon[csState] || '❓'} ${csState}\n\n` +
      `<b>⚡ Команды:</b>\n` +
      `/ai <i>запрос</i> — умный AI (GPT-4o, 24/7)\n` +
      `/agents — список всех агентов\n` +
      `/crewai <i>запрос</i> — CrewAI (через Codespace)\n` +
      `/image <i>запрос</i> — картинка (AI)\n` +
      `/gold — GitHub Gold Miner\n` +
      `/help — справка`,
      { reply_markup: menuKb() }
    );
  }

  // ── /agents ──
  if (cmd === '/agents') {
    const cats = {};
    for (const [name, info] of Object.entries(AGENTS)) {
      if (!cats[info.cat]) cats[info.cat] = [];
      cats[info.cat].push({ name, ...info });
    }
    const catNames = { python: '🐍 Python', node: '🟢 Node.js', heavy: '🏗 Тяжёлые', builtin: '⚡ Встроенные (24/7)' };
    let resp = '🤖 <b>PawWork Arsenal — 30+ AI Агентов</b>\n\n';
    for (const [cat, agents] of Object.entries(cats)) {
      resp += `<b>${catNames[cat] || cat}</b>\n`;
      for (const a of agents) {
        const mark = a.needsCode ? ' 🖥' : ' ✅';
        resp += `  /${a.name} — ${a.desc}${mark}\n`;
      }
      resp += '\n';
    }
    resp += '✅ = работает 24/7 | 🖥 = через Codespace (может спать)\n';
    resp += '💡 <code>/ai &lt;запрос&gt;</code> — авто-выбор агента';
    return send(token, chatId, resp);
  }

  // ── AGENT COMMANDS ──
  for (const agentName of AGENT_NAMES) {
    const agentCmd = `/${agentName}`;
    if (cmd === agentCmd) {
      const info = AGENTS[agentName];
      if (!args) return send(token, chatId, `🤖 <b>${agentName}</b> — ${info.desc}\nИспользование: <code>/${agentName} запрос</code>\nКатегория: ${info.cat}\nСтатус: ${info.needsCode ? '🖥 через Codespace' : '✅ 24/7'}`);
      
      if (!info.needsCode) {
        // Built-in agents
        if (agentName === 'ai') {
          const { text: aiText } = await askAI([{ role: 'system', content: 'Отвечай полезно, кратко, на русском.' }, { role: 'user', content: args }], env);
          return sendMD(token, chatId, aiText.slice(0, 4000));
        }
        if (agentName === 'image') {
          const style = args.includes('--') ? args.split(' --')[1].split(' ')[0] : 'flux';
          const prompt = args.replace(/ --\w+/g, '').trim();
          const url = genImage(prompt, style);
          return sendPhoto(token, chatId, url, `🎨 ${h(prompt)}\nСтиль: <b>${style}</b>`);
        }
        if (agentName === 'gold') return send(token, chatId, await goldMiner(args, env));
        if (agentName === 'search') {
          const { text: r } = await askAI([{ role: 'system', content: 'Ты поисковик. Найди информацию.' }, { role: 'user', content: args }], env);
          return sendMD(token, chatId, r.slice(0, 4000));
        }
      }
      
      // Codespace agents — check and proxy
      const csState = await checkCodespace(env);
      if (csState === 'stopped' || csState === 'unknown') {
        await send(token, chatId, `🖥 <b>${agentName}</b> требует Codespace (сейчас спит).\n🔄 Пробуждаю... это займёт ~30 секунд.`);
        if (await startCodespace(env)) {
          return send(token, chatId, `✅ Codespace запускается. Попробуй через минуту:\n<code>/${agentName} ${h(args)}</code>`);
        }
        return send(token, chatId, `❌ Не удалось запустить Codespace.\nПока доступен <code>/ai ${h(args)}</code>`);
      }
      
      await send(token, chatId, `🤖 Перенаправляю запрос к <b>${agentName}</b> на Codespace...`);
      try {
        const res = await fetch(`https://${env.CODESPACE_NAME}-8080.app.github.dev/api/agent`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent: agentName, prompt: args }),
          signal: AbortSignal.timeout(30000),
        });
        if (res.ok) {
          const data = await res.json();
          return sendMD(token, chatId, (data.result || '✅ Выполнено').slice(0, 4000));
        }
      } catch {}
      return send(token, chatId, `⚠️ ${agentName} временно недоступен. Используй <code>/ai ${h(args)}</code>`);
    }
  }

  // ── /ai — авто-выбор ──
  if (cmd === '/ai' && args) {
    const { text: aiText } = await askAI([
      { role: 'system', content: 'Ты — PawWork AI. Отвечай полезно, кратко, на русском. Если нужен код — пиши код.' },
      { role: 'user', content: args }
    ], env);
    return sendMD(token, chatId, aiText.slice(0, 4000));
  }

  // ── /image ──
  if (['/image', '/img'].includes(cmd)) {
    if (!args) return send(token, chatId, 'Укажи промпт: /image кот в космосе');
    const style = args.includes('--') ? args.split(' --')[1].split(' ')[0] : 'flux';
    const prompt = args.replace(/ --\w+/g, '').trim();
    const url = genImage(prompt, style);
    return sendPhoto(token, chatId, url, `🎨 ${h(prompt)}\nСтиль: <b>${style}</b>`, { reply_markup: kb([[('🎨 Ещё', `/image ${prompt}`)]]) });
  }

  // ── /gold ──
  if (cmd === '/gold') return send(token, chatId, await goldMiner(args, env));

  // ── /help ──
  if (cmd === '/help') {
    return send(token, chatId,
      `🤖 <b>PawWork Ultimate v8 — 24/7</b>\n\n` +
      `<b>🤖 AI (24/7, без засыпания):</b>\n` +
      `<code>/ai объясни квантовые компьютеры</code>\n\n` +
      `<b>🎨 Изображения:</b>\n` +
      `<code>/image кот в космосе</code>\n` +
      `<code>/image дракон --anime</code> (стили: anime, real, 3d)\n\n` +
      `<b>⚔️ Все 30+ агентов:</b>\n` +
      `<code>/agents</code> — полный список\n` +
      `<code>/crewai создай команду</code> — через Codespace\n` +
      `<code>/openclaw напиши код</code> — через Codespace\n\n` +
      `<b>⛏ GitHub Gold Miner:</b>\n` +
      `<code>/gold</code> — топ проектов\n` +
      `<code>/gold python</code> — Python топ\n\n` +
      `<b>ℹ️ Система:</b>\n` +
      `<code>/status</code> — статус\n` +
      `<code>/start</code> — меню\n\n` +
      `⚡ Работает 24/7 на Cloudflare Workers\n` +
      `🖥 Codespaces для тяжёлых агентов`,
      { reply_markup: menuKb() }
    );
  }

  // ── Image by keyword ──
  const imgWords = ['нарисуй', 'картинк', 'изображен', 'сгенерируй', 'создай картинк'];
  for (const kw of imgWords) {
    if (text.toLowerCase().includes(kw)) {
      const idx = text.toLowerCase().indexOf(kw);
      let p = text.slice(idx + kw.length).replace(/^[:,\s]+/, '').trim() || text;
      const url = genImage(p);
      return sendPhoto(token, chatId, url, `🎨 ${h(p)}`);
    }
  }

  // ── Default: AI ──
  const { text: reply } = await askAI([
    { role: 'system', content: 'Ты PawWork AI. Отвечай полезно, кратко, на русском.' },
    { role: 'user', content: text }
  ], env);
  return sendMD(token, chatId, reply.slice(0, 4000));
}

// ═══════════════════════ CALLBACKS ═══════════════════════════════
async function handleCallback(cb, env) {
  const data = cb.data || '';
  const chatId = cb.message?.chat?.id;
  const msgId = cb.message?.message_id;
  await tg(env.TELEGRAM_TOKEN, 'answerCallbackQuery', { callback_query_id: cb.id, text: '✅' });
  if (!chatId || !msgId) return;

  // Execute command
  if (data.startsWith('/')) {
    const fakeMsg = { chat: { id: chatId }, text: data, from: { id: 0 } };
    await handleMessage(fakeMsg, env);
  }
}

function cors() {
  return { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization' };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', ...cors() } });
}
