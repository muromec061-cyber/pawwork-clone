// ===========================================================
//   PawWork Clone — Твой личный AI агент 24/7
//   Multi-provider: Groq · GitHub Models · CF AI · Gemini · Colab
//   Telegram · Файлы · Код · Деплой
// ===========================================================

// ── ПРОВАЙДЕРЫ ──────────────────────────────────────────────
// Все бесплатные, без карты. Заполни свои API ключи в env
const PROVIDERS = {
  groq: {
    base: 'https://api.groq.com/openai/v1/chat/completions',
    model: 'llama-3.3-70b-versatile',
    // Альтернативы: 'qwen-3-32b', 'llama-3.1-8b-instant'
    key: () => env('GROQ_API_KEY'),
    headers: (k) => ({ 'Authorization': `Bearer ${k}`, 'Content-Type': 'application/json' }),
    parse: (d) => d?.choices?.[0]?.message?.content || null,
  },
  github: {
    base: 'https://models.github.ai/inference/chat/completions',
    model: 'gpt-4o',
    // Альтернативы: 'Llama-4-Scout-17B-16E', 'DeepSeek-R1'
    key: () => env('GITHUB_TOKEN'),
    headers: (k) => ({ 'Authorization': `Bearer ${k}`, 'Content-Type': 'application/json' }),
    parse: (d) => d?.choices?.[0]?.message?.content || null,
  },
  cf: {
    // Cloudflare Workers AI — нужен account_id + API токен
    base: (env) => `https://api.cloudflare.com/client/v4/accounts/${env('CF_ACCOUNT')}/ai/run/@cf/qwen/qwen1.5-7b-chat-awq`,
    key: () => env('CF_API_TOKEN'),
    headers: (k) => ({ 'Authorization': `Bearer ${k}`, 'Content-Type': 'application/json' }),
    parse: (d) => d?.result?.response || d?.result?.choices?.[0]?.message?.content || null,
  },
  gemini: {
    base: (env) => `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${env('GEMINI_API_KEY')}`,
    key: () => 'unused',
    model: null, // не нужен, в URL
    headers: () => ({ 'Content-Type': 'application/json' }),
    body: (msgs) => ({ contents: msgs.map(m => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })) }),
    parse: (d) => d?.candidates?.[0]?.content?.parts?.[0]?.text || null,
  },
  colab: {
    // Твои GGUF модели через Colab + ngrok (опционально)
    base: () => env('COLAB_URL') || null,
    model: null,
    key: () => env('COLAB_KEY') || 'sk-colab',
    headers: (k) => ({ 'Authorization': `Bearer ${k}`, 'Content-Type': 'application/json' }),
    parse: (d) => d?.response || d?.choices?.[0]?.message?.content || null,
  },
};

const PROVIDER_ORDER = ['groq', 'github', 'cf', 'gemini', 'colab'];

// ── СИСТЕМНЫЙ ПРОМПТ ────────────────────────────────────────
const SYSTEM = `Ты — PawWork Clone, персональный AI-агент пользователя.

ТЫ УМЕЕШЬ:
1. Писать любой код (Python, JS, HTML, C++, Go, Rust, — всё)
2. Создавать приложения (веб, телеграм-боты, CLI, API)
3. Отправлять файлы (через Telegram)
4. Деплоить на GitHub (репозитории, Pages, Actions)
5. Искать в интернете, анализировать данные
6. Работать с файловой системой (читать, писать, редактировать)
7. Запоминать контекст между сессиями

ОТВЕЧАЙ НА РУССКОМ.
Будь полезным, конкретным, пиши код сразу.`;

// ── МОДЕЛЬ ДАННЫХ ──────────────────────────────────────────
// chat_id → { history: [...], files: {...}, projects: {...} }

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') return json(200);

    try {
      // ── Telegram webhook ──
      if (path === '/webhook' || path === '/telegram') {
        const body = await request.json();
        if (body?.message) return handleTelegram(body.message, env);
        if (body?.callback_query) return handleCallback(body.callback_query, env);
        return json({ ok: true });
      }

      // ── Set Telegram webhook ──
      if (path === '/set-webhook') {
        const tgToken = env('TELEGRAM_BOT_TOKEN');
        const webhookUrl = url.searchParams.get('url') || `${url.origin}/webhook`;
        const r = await fetch(`https://api.telegram.org/bot${tgToken}/setWebhook?url=${webhookUrl}`);
        const d = await r.json();
        return json(d);
      }

      // ── API (с авторизацией) ──
      const auth = request.headers.get('Authorization') || '';
      const userKey = auth.replace('Bearer ', '');
      const validKey = env('PAWWORK_API_KEY');
      if (validKey && userKey !== validKey) {
        return json({ error: 'Unauthorized' }, 401);
      }

      switch (path) {
        case '/': return json({ name: 'PawWork Clone', version: '3.0', providers: PROVIDER_ORDER });
        case '/v1/chat': return handleChat(request, env);
        case '/v1/agent': return handleAgent(request, env);
        case '/v1/code': return handleCode(request, env);
        case '/v1/file': return handleFile(request, env);
        case '/v1/deploy': return handleDeploy(request, env);
        case '/v1/memory': return handleMemory(request, env);
        case '/v1/providers': return json({ providers: PROVIDER_ORDER, active: PROVIDER_ORDER.filter(p => PROVIDERS[p].key()(env)) });
        case '/v1/models': return json({ groq: 'llama-3.3-70b-versatile,qwen-3-32b', github: 'gpt-4o,llama-4,deepseek-r1', cf: 'qwen1.5-7b,llama-3.3-70b', gemini: 'gemini-2.5-flash' });
        default: return json({ error: 'Not found' }, 404);
      }
    } catch (e) {
      return json({ error: e.message }, 500);
    }
  }
};

// ======================== HELPER ========================
function env(key) {
  // В Cloudflare Worker env — это свойства env объекта
  try { return globalThis[key] || ''; } catch { return ''; }
}

function json(data, status = 200) {
  return new Response(typeof data === 'string' ? data : JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
  });
}

async function kvGet(env, key) {
  try { return await env.MEMORY_KV?.get(key); } catch { return null; }
}
async function kvSet(env, key, val, ttl) {
  try { await env.MEMORY_KV?.put(key, val, ttl ? { expirationTtl: ttl } : {}); } catch {}
}

// ======================== AI INFERENCE ========================
async function ask(prompt, system, provider, env) {
  const msg = [];
  if (system) msg.push({ role: 'system', content: system });
  msg.push({ role: 'user', content: prompt });

  const providers = provider ? [provider] : PROVIDER_ORDER;

  for (const name of providers) {
    const p = PROVIDERS[name];
    if (!p) continue;
    const key = typeof p.key === 'function' ? p.key()(env) : p.key;
    if (!key && name !== 'gemini' && name !== 'colab') continue;
    if (name === 'colab' && !p.base()(env)) continue;

    try {
      const base = typeof p.base === 'function' ? p.base(env) : p.base;
      const body = p.body ? p.body(msg) : {
        model: p.model || undefined,
        messages: msg,
        max_tokens: 4096,
        temperature: 0.3,
      };

      const res = await fetch(base, {
        method: 'POST',
        headers: typeof p.headers === 'function' ? p.headers(key) : p.headers,
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        if (res.status === 429 || res.status >= 500) continue; // rate limit / error → fallback
        return `[${name}] API error: ${res.status} ${errText.slice(0, 200)}`;
      }

      const data = await res.json();
      const text = p.parse(data);
      if (text) return text;
    } catch (e) {
      continue; // fallback to next provider
    }
  }

  return 'Все провайдеры недоступны. Попробуй позже.';
}

// ======================== CHAT ========================
async function handleChat(request, env) {
  const { messages = [], max_tokens = 2048, temperature = 0.3, provider } = await request.json().catch(() => ({}));
  const lastMsg = messages.filter(m => m.role === 'user').pop();
  if (!lastMsg) return json({ error: 'no user message' }, 400);

  const text = await ask(lastMsg.content, SYSTEM, provider, env);
  return json({ choices: [{ message: { role: 'assistant', content: text } }], provider: 'auto-routed' });
}

// ======================== REACT AGENT ========================
async function handleAgent(request, env) {
  const { prompt = '', session_id = 'default', max_steps = 10 } = await request.json().catch(() => ({}));
  if (!prompt) return json({ error: 'prompt required' }, 400);

  const memKey = `agent:${session_id}`;
  const raw = await kvGet(env, memKey) || '{}';
  const data = JSON.parse(raw);

  const agentPrompt = SYSTEM + `


ТЫ — АГЕНТ С ИНСТРУМЕНТАМИ:

1. web_search(query) — поиск в интернете (DuckDuckGo)
2. calculator(expr) — математические вычисления
3. get_time() — текущее время
4. write_file(path, content) — создать или перезаписать файл (код, текст)
5. read_file(path) — прочитать файл
6. list_files() — список всех сохранённых файлов
7. create_github_repo(name, description) — создать репозиторий на GitHub
8. deploy_to_pages(repo_name, branch, dir) — деплой на GitHub Pages
9. send_telegram(chat_id, text) — отправить сообщение в Telegram
10. memory_get(key) — прочитать из памяти
11. memory_set(key=value) — записать в память
12. run_code(code, language) — выполнить код и вернуть результат
13. finish(answer) — завершить и ответить

ФОРМАТ ОТВЕТА (строго):
THOUGHT: что ты думаешь и планируешь
ACTION: имя_инструмента
ACTION_INPUT: аргументы

После каждого действия придёт OBSERVATION с результатом.
Продолжай цикл, пока не выполнишь задачу.
Когда готов ответить пользователю: ACTION: finish`;

  const messages = [{ role: 'system', content: agentPrompt }];
  if (data.history) {
    for (const m of data.history.slice(-12)) messages.push(m);
  }
  messages.push({ role: 'user', content: prompt });

  data.history = data.history || [];
  data.history.push({ role: 'user', content: prompt });
  await kvSet(env, memKey, JSON.stringify(data));

  for (let step = 0; step < max_steps; step++) {
    const resp = await PROMPT(messages, 0.3, env);

    const act = resp.match(/ACTION:\s*(\w+)/);
    const inp = resp.match(/ACTION_INPUT:\s*(.*?)(?:\n|$)/s);
    const tho = resp.match(/THOUGHT:\s*(.*?)(?:\nACTION:|$)/s);

    const action = act ? act[1].trim() : '';
    const input = inp ? inp[1].trim().replace(/^["']|["']$/g, '') : '';
    const thought = tho ? tho[1].trim() : '';

    if (action === 'finish' || !action) {
      data.history.push({ role: 'assistant', content: resp });
      await kvSet(env, memKey, JSON.stringify(data));
      return json({ response: resp, steps: step + 1, session_id });
    }

    const obs = await runTool(action, input, env);
    messages.push({ role: 'assistant', content: resp });
    messages.push({ role: 'user', content: `OBSERVATION: ${obs}\n\nПродолжай. Когда готов: ACTION: finish` });
  }

  return json({ response: 'Достигнут лимит шагов. Попробуй уточнить задачу.', incomplete: true, session_id });
}

async function PROMPT(messages, temperature, env) {
  const system = messages.find(m => m.role === 'system')?.content || '';
  const userMsg = messages.filter(m => m.role === 'user').pop()?.content || '';
  return await ask(userMsg, system, null, env);
}

// ======================== CODE ========================
async function handleCode(request, env) {
  const { task = '', language = 'python' } = await request.json().catch(() => ({}));
  if (!task) return json({ error: 'task required' }, 400);

  const code = await ask(
    `Напиши код на ${language} для задачи ниже.
Задача: ${task}

Требования:
- Рабочий код без плейсхолдеров
- Полная реализация, не фрагмент
- Если нужно — несколько файлов (раздели === filename.ext ===)

Формат ответа:
\`\`\`${language}
// код
\`\`\`
Или с разделителями для нескольких файлов:
=== index.html ===
...
=== style.css ===
...`,
    'Ты — senior-программист. Пиши production-ready код.',
    null, env
  );

  // Сохраняем в KV
  const sessionKey = `code:${Date.now()}`;
  await kvSet(env, sessionKey, JSON.stringify({ task, language, code, ts: Date.now() }));

  return json({ code, language, task, session: sessionKey });
}

// ======================== FILE OPERATIONS ========================
async function handleFile(request, env) {
  const { action = 'list', path = '', content = '' } = await request.json().catch(() => ({}));

  if (action === 'list') {
    // KV не умеет list на free, возвращаем последние файлы
    return json({ note: 'Используй read_file / write_file через агента' });
  }
  if (action === 'read') {
    const val = await kvGet(env, `file:${path}`);
    return json({ path, content: val, found: val !== null });
  }
  if (action === 'write') {
    await kvSet(env, `file:${path}`, content);
    return json({ path, saved: true, size: content.length });
  }
  if (action === 'delete') {
    try { await env.MEMORY_KV?.delete(`file:${path}`); } catch {}
    return json({ path, deleted: true });
  }
  return json({ error: 'Unknown action' }, 400);
}

// ======================== DEPLOY via GitHub ========================
async function handleDeploy(request, env) {
  const { repo_name = '', files = [], description = '', deploy_type = 'repo' } = await request.json().catch(() => ({}));
  const token = env('GITHUB_TOKEN');
  if (!token) return json({ error: 'GitHub token not configured' });

  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', 'Accept': 'application/vnd.github.v3+json' };
  const userResp = await fetch('https://api.github.com/user', { headers });
  const user = await userResp.json();
  const login = user.login;

  // Создаём репозиторий
  const repo = await fetch('https://api.github.com/user/repos', {
    method: 'POST', headers,
    body: JSON.stringify({ name: repo_name, description, private: false, auto_init: true }),
  }).then(r => r.json());

  if (repo.message) return json({ error: repo.message });

  // Создаём/обновляем файлы
  const results = [];
  for (const f of files) {
    const content = btoa(unescape(encodeURIComponent(f.content)));
    const putResp = await fetch(`https://api.github.com/repos/${login}/${repo_name}/contents/${f.path}`, {
      method: 'PUT', headers,
      body: JSON.stringify({ message: `Add ${f.path}`, content }),
    }).then(r => r.json());
    results.push({ path: f.path, status: putResp.content ? 'created' : 'error', sha: putResp.content?.sha });
  }

  // Если деплой на Pages
  let pagesUrl = null;
  if (deploy_type === 'pages') {
    await fetch(`https://api.github.com/repos/${login}/${repo_name}/pages`, {
      method: 'POST', headers,
      body: JSON.stringify({ source: { branch: 'main', path: '/' } }),
    }).catch(() => {});
    pagesUrl = `https://${login}.github.io/${repo_name}`;
  }

  return json({
    repo: repo.html_url,
    clone_url: repo.clone_url,
    pages_url: pagesUrl,
    files: results,
  });
}

// ======================== MEMORY ========================
async function handleMemory(request, env) {
  const { action = 'get', key = '', content = '' } = await request.json().catch(() => ({}));
  if (action === 'get') {
    const val = await kvGet(env, key);
    return json({ content: val, found: val !== null });
  }
  if (action === 'set') {
    await kvSet(env, key, content);
    return json({ status: 'saved' });
  }
  return json({ error: `Unknown: ${action}` }, 400);
}

// ======================== TELEGRAM ========================
async function handleTelegram(msg, env) {
  const chatId = msg.chat.id;
  const text = (msg.text || '').trim();
  const tgToken = env('TELEGRAM_BOT_TOKEN');
  const send = (t, kb) => fetch(`https://api.telegram.org/bot${tgToken}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text: t.slice(0, 4000), parse_mode: 'HTML', reply_markup: kb ? JSON.stringify({ inline_keyboard: kb }) : undefined }),
  });

  if (!text || text.startsWith('/')) {
    if (text === '/start') {
      return send(`🧠 <b>PawWork Clone</b> — твой личный AI агент

Я работаю 24/7 на бесплатных серверах.
Просто напиши, что нужно сделать:

• Написать код / приложение
• Создать файл
• Задеплоить на GitHub
• Поискать в интернете
• Любая задача

Мои модели: Qwen · Llama · GPT-4o · DeepSeek · Gemini
И твои личные GGUF (qwen2, Moonlight, kimi-vl) — ускорение через Colab`);
    }
    return send('Напиши задачу. Я сделаю.');
  }

  // Запускаем агента для каждого сообщения
  await send(`🤔 Думаю над задачей: <i>${text.slice(0, 100)}</i>`);

  const memKey = `tg:${chatId}`;
  const raw = await kvGet(env, memKey) || '{}';
  const data = JSON.parse(raw);
  data.history = data.history || [];

  const agentPrompt = SYSTEM + `\n\nКОНТЕКСТ ИСТОРИИ:\n${data.history.slice(-6).join('\n')}\n\nСООБЩЕНИЕ: ${text}

Ты — агент с инструментами. Если нужно создать файл — используй write_file.
Если нужен код — пиши полный рабочий код.
Для деплоя — create_github_repo + deploy_to_pages.
Формат действий — THOUGHT / ACTION / ACTION_INPUT.`;

  const result = await runAgentLoop(agentPrompt, env);

  data.history.push(`User: ${text}`);
  data.history.push(`Agent: ${result.response.slice(0, 500)}`);
  if (data.history.length > 20) data.history = data.history.slice(-20);
  await kvSet(env, memKey, JSON.stringify(data));

  await send(result.response.slice(0, 4000));

  return json({ ok: true });
}

async function handleCallback(cb, env) {
  // Обработка кнопок — пока пусто
  const tgToken = env('TELEGRAM_BOT_TOKEN');
  await fetch(`https://api.telegram.org/bot${tgToken}/answerCallbackQuery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ callback_query_id: cb.id, text: 'Готовлю...' }),
  });
  return json({ ok: true });
}

// ======================== AGENT LOOP ========================
async function runAgentLoop(goal, env) {
  const messages = [{ role: 'system', content: goal }];

  for (let step = 0; step < 8; step++) {
    const resp = await ask(
      messages.filter(m => m.role === 'user').pop()?.content || goal,
      messages.find(m => m.role === 'system')?.content,
      null, env
    );

    const act = resp.match(/ACTION:\s*(\w+)/);
    const inp = resp.match(/ACTION_INPUT:\s*(.*?)(?:\n|$)/s);
    const action = act ? act[1].trim() : '';
    const input = inp ? inp[1].trim().replace(/^["']|["']$/g, '') : '';

    if (action === 'finish' || !action) {
      return { response: resp, steps: step + 1 };
    }

    const obs = await runTool(action, input, env);
    messages.push({ role: 'assistant', content: resp });
    messages.push({ role: 'user', content: `OBSERVATION: ${obs}\n\nПродолжай. ACTION: finish когда готов.` });
  }

  return { response: 'Лимит шагов. Уточни задачу.', incomplete: true };
}

// ======================== TOOLS ========================
const TOOLS = {
  web_search: async (q) => {
    try {
      const r = await fetch(`https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(q)}`, {
        headers: { 'User-Agent': 'Mozilla/5.0' }
      });
      const html = await r.text();
      const links = html.match(/<a[^>]*class="result-link"[^>]*>(.*?)<\/a>/gs) || [];
      return links.map(s => s.replace(/<[^>]+>/g, '').trim()).filter(s => s.length > 10).slice(0, 5).join('\n').slice(0, 2000) || 'Нет результатов';
    } catch (e) { return `Error: ${e.message}`; }
  },
  calculator: (expr) => {
    try {
      const safe = expr.replace(/[^0-9+\-*/().,% ]/g, '');
      return String(Function(`return (${safe})`)());
    } catch (e) { return `Error: ${e.message}`; }
  },
  get_time: () => new Date().toLocaleString('ru-RU'),
  write_file: async (input, env) => {
    const lines = input.split('\n', 2);
    const path = lines[0].trim();
    const content = lines.slice(1).join('\n');
    if (!path) return 'Укажи путь в первой строке';
    await kvSet(env, `file:${path}`, content);
    return `✅ Файл ${path} создан (${content.length} символов)`;
  },
  read_file: async (key, env) => {
    return (await kvGet(env, `file:${key}`)) || 'Файл не найден';
  },
  list_files: async (_, env) => {
    return 'Для просмотра файлов используй read_file с конкретным именем';
  },
  memory_get: async (key, env) => {
    return (await kvGet(env, key)) || '(пусто)';
  },
  memory_set: async (input, env) => {
    const p = input.split('=', 2);
    if (p.length === 2) { await kvSet(env, p[0].trim(), p[1].trim()); return 'OK'; }
    return 'Формат: key=value';
  },
  create_github_repo: async (input, env) => {
    const [name, ...descParts] = input.split('\n');
    const description = descParts.join(' ').trim() || 'Created by PawWork Clone';
    const token = env('GITHUB_TOKEN');
    if (!token) return 'GitHub токен не настроен';
    const r = await fetch('https://api.github.com/user/repos', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '-'), description, private: false }),
    });
    const d = await r.json();
    return d.html_url ? `✅ Репозиторий: ${d.html_url}` : `Ошибка: ${d.message || JSON.stringify(d)}`;
  },
  deploy_to_pages: async (input, env) => {
    const token = env('GITHUB_TOKEN');
    if (!token) return 'GitHub токен не настроен';
    const repo = input.trim();
    const r = await fetch(`https://api.github.com/repos/${repo}/pages`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: { branch: 'main', path: '/' } }),
    });
    const d = await r.json();
    return d.html_url ? `✅ GitHub Pages: ${d.html_url}` : `Ошибка: ${d.message || JSON.stringify(d)}`;
  },
  send_telegram: async (input, env) => {
    const [chatId, ...textParts] = input.split('\n');
    const text = textParts.join('\n');
    const token = env('TELEGRAM_BOT_TOKEN');
    if (!token) return 'Telegram токен не настроен';
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: parseInt(chatId) || chatId, text: text.slice(0, 4000), parse_mode: 'HTML' }),
    });
    return '✅ Сообщение отправлено';
  },
  run_code: async (input, env) => {
    return 'Выполнение кода на Cloudflare Workers ограничено. Используй локальное выполнение.';
  },
  finish: (input) => input || 'Готово',
};

async function runTool(name, input, env) {
  const tool = TOOLS[name];
  if (!tool) return `Неизвестный инструмент: ${name}. Доступны: ${Object.keys(TOOLS).join(', ')}`;
  try {
    const needsEnv = ['write_file', 'read_file', 'list_files', 'memory_get', 'memory_set',
                      'create_github_repo', 'deploy_to_pages', 'send_telegram', 'run_code'];
    if (needsEnv.includes(name)) return await tool(input, env);
    return await tool(input);
  } catch (e) { return `Ошибка инструмента ${name}: ${e.message}`; }
}
