/**
 * PawWork Bot v5 — Telegram Webhook на Cloudflare Workers
 * Мгновенные ответы, 24/7, бесплатно, без перерывов
 * 
 * Как работает:
 * 1. Telegram присылает сообщение на этот Worker (webhook)
 * 2. Worker обрабатывает через GitHub Models API (GPT-4o бесплатно)
 * 3. Отвечает мгновенно в Telegram
 * 
 * Переменные окружения (настроить в Cloudflare Dashboard):
 *   TELEGRAM_TOKEN    — токен бота Telegram
 *   GITHUB_TOKEN      — GitHub токен (для GitHub Models API)
 *   GH_TOKEN          — тот же токен (для GitHub API)
 *   GROQ_API_KEY      — опционально, ключ Groq
 *   CF_ACCOUNT        — опционально, account ID Cloudflare
 *   CF_API_TOKEN      — опционально, CF Workers AI токен
 *   GEMINI_API_KEY    — опционально, ключ Gemini
 */

// Провайдеры AI
const PROVIDERS = [
  {
    name: 'github',
    url: 'https://models.github.ai/inference/chat/completions',
    model: 'gpt-4o',
    key: (env) => env.GITHUB_TOKEN || env.GH_TOKEN || '',
    parse: (data) => data?.choices?.[0]?.message?.content || null,
  },
  {
    name: 'groq',
    url: 'https://api.groq.com/openai/v1/chat/completions',
    model: 'llama-3.3-70b-versatile',
    key: (env) => env.GROQ_API_KEY || '',
    parse: (data) => data?.choices?.[0]?.message?.content || null,
  },
  {
    name: 'gemini',
    url: (env) => `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${env.GEMINI_API_KEY || ''}`,
    model: null,
    key: (env) => env.GEMINI_API_KEY || '',
    headers: () => ({ 'Content-Type': 'application/json' }),
    body: (msgs) => ({
      contents: msgs.map(m => ({
        role: m.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: m.content }],
      })),
    }),
    parse: (data) => data?.candidates?.[0]?.content?.parts?.[0]?.text || null,
  },
];

const SYSTEM_PROMPT = `Ты — PawWork Bot, AI-ассистент пользователя.

ТЫ УМЕЕШЬ:
1. Писать любой код (Python, JS, HTML, C++, Go, Rust)
2. Создавать приложения, ботов, сайты
3. Искать в интернете (используй web_search)
4. Анализировать данные

Отвечай на русском. Будь полезным и конкретным.

Твой стиль:
- Кратко, по делу
- Если нужен код — пиши сразу готовый рабочий код
- Используй эмодзи для наглядности`;

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
          return new Response('PawWork Bot v5 — Telegram Webhook', { status: 200 });
        }
        const body = await request.json().catch(() => ({}));
        
        // Message from user
        if (body?.message) {
          await handleMessage(body.message, env);
          return json({ ok: true });
        }
        
        // Callback query (button click)
        if (body?.callback_query) {
          await handleCallback(body.callback_query, env);
          return json({ ok: true });
        }
        
        return json({ ok: true });
      }

      // --- Set webhook ---
      if (path === '/set-webhook') {
        const webhookUrl = url.searchParams.get('url') || `${url.origin}/webhook`;
        const result = await tgApi(env.TELEGRAM_TOKEN, 'setWebhook', {
          url: webhookUrl,
          allowed_updates: ['message', 'callback_query'],
        });
        return json(result);
      }

      // --- Delete webhook ---
      if (path === '/delete-webhook') {
        const result = await tgApi(env.TELEGRAM_TOKEN, 'deleteWebhook', {});
        return json(result);
      }

      // --- Health ---
      if (path === '/health') {
        return json({
          status: 'ok',
          providers: PROVIDERS.filter(p => p.key(env)).map(p => p.name),
        });
      }

      return json({ error: 'Not found' }, 404);
    } catch (e) {
      return json({ error: e.message }, 500);
    }
  },
};

// ======================== TELEGRAM API ========================

async function tgApi(token, method, payload) {
  const url = `https://api.telegram.org/bot${token}/${method}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.json();
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function sendMessage(token, chatId, text, extra = {}) {
  const payload = {
    chat_id: chatId,
    text: text.slice(0, 4096),
    parse_mode: 'HTML',
    ...extra,
  };
  
  // Try with HTML first
  let result = await tgApi(token, 'sendMessage', payload);
  
  // If HTML fails, try escaped HTML
  if (!result.ok) {
    payload.text = escapeHtml(text.slice(0, 4096));
    result = await tgApi(token, 'sendMessage', payload);
  }
  
  // If still fails, try plain text
  if (!result.ok) {
    payload.parse_mode = undefined;
    payload.text = text.slice(0, 4096);
    result = await tgApi(token, 'sendMessage', payload);
  }
  
  return result;
}

async function editMessage(token, chatId, msgId, text, extra = {}) {
  const payload = {
    chat_id: chatId,
    message_id: msgId,
    text: text.slice(0, 4096),
    parse_mode: 'HTML',
    ...extra,
  };
  
  let result = await tgApi(token, 'editMessageText', payload);
  
  if (!result.ok) {
    payload.text = escapeHtml(text.slice(0, 4096));
    result = await tgApi(token, 'editMessageText', payload);
  }
  
  if (!result.ok) {
    payload.parse_mode = undefined;
    payload.text = text.slice(0, 4096);
    result = await tgApi(token, 'editMessageText', payload);
  }
  
  return result;
}

async function answerCallback(token, cbId, text) {
  return tgApi(token, 'answerCallbackQuery', {
    callback_query_id: cbId,
    text: text || '✓',
    show_alert: false,
  });
}

// ======================== AI ========================

async function askAI(messages, env) {
  for (const p of PROVIDERS) {
    const key = p.key(env);
    if (!key) continue;
    
    try {
      const url = typeof p.url === 'function' ? p.url(env) : p.url;
      const headers = p.headers ? p.headers() : {
        'Authorization': `Bearer ${key}`,
        'Content-Type': 'application/json',
      };
      
      const body = p.body ? p.body(messages) : {
        model: p.model,
        messages: messages,
        max_tokens: 4096,
        temperature: 0.3,
      };
      
      const res = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(body),
      });
      
      if (!res.ok) {
        if (res.status === 429 || res.status >= 500) continue; // fallback
        const errText = await res.text().catch(() => '');
        console.error(`[${p.name}] HTTP ${res.status}: ${errText.slice(0, 200)}`);
        continue;
      }
      
      const data = await res.json();
      const text = p.parse(data);
      if (text) return { text, provider: p.name };
    } catch (e) {
      console.error(`[${p.name}] Error: ${e.message}`);
      continue;
    }
  }
  
  return { text: 'Извини, все AI провайдеры временно недоступны.', provider: 'none' };
}

// ======================== MESSAGE HANDLER ========================

const MAIN_MENU = {
  inline_keyboard: [
    [
      { text: '💬 Чат с AI', callback_data: 'mode_chat' },
      { text: '💻 Создать код', callback_data: 'mode_code' },
    ],
    [
      { text: '🔍 Поиск', callback_data: 'mode_search' },
      { text: '⚔️ Агенты', callback_data: 'mode_agents' },
    ],
    [
      { text: '❓ Помощь', callback_data: 'mode_help' },
      { text: '⚙️ Настройки', callback_data: 'mode_settings' },
    ],
  ],
};

function menuFor(mode) {
  return {
    inline_keyboard: [
      [{ text: '🏠 Главное меню', callback_data: 'menu_main' }],
    ],
  };
}

function getWelcomeText() {
  return `🤖 <b>PawWork Bot v5</b>
Мгновенный AI-ассистент на Cloudflare Workers

⚔️ Многоагентная система <b>三省六部</b>:
👑 太子 → 📜 中书省 → 🔍 门下省 → 💻 六部

Работает 24/7 • Мгновенно • Бесплатно

Выбери режим ниже:`;
}

function getHelpText() {
  return `❓ <b>Помощь</b>

<b>Режимы:</b>
💬 Чат — обычный диалог с AI
💻 Код — создание программ
🔍 Поиск — поиск информации
⚔️ Агенты — многоагентная система

<b>Команды:</b>
/start — главное меню
/help — эта справка
/chat — режим чата
/code — режим кода

<b>Провайдер:</b> GitHub Models (GPT-4o)`;
}

function getAgentsText() {
  return `⚔️ <b>Многоагентная система «三省六部»</b>

👑 <b>太子</b> — Маршрутизация
📜 <b>中书省</b> — Планирование
🔍 <b>门下省</b> — Проверка
💻 <b>六部</b> — Исполнение
📮 <b>尚书省</b> — Сборка ответа

Вдохновлено проектом edict (github.com/cft0808/edict)`;
}

// Simple KV storage (in-memory for now, will add Workers KV later)
const memory = {};

async function handleMessage(msg, env) {
  const chatId = msg.chat?.id;
  const text = (msg.text || '').trim();
  const username = msg.from?.first_name || 'User';
  
  if (!chatId || !text) return;
  
  // Send typing indicator (fire and forget)
  tgApi(env.TELEGRAM_TOKEN, 'sendChatAction', {
    chat_id: chatId, action: 'typing',
  }).catch(() => {});
  
  // Commands
  if (text.startsWith('/')) {
    const cmd = text.split(' ')[0].toLowerCase();
    
    if (cmd === '/start') {
      await sendMessage(env.TELEGRAM_TOKEN, chatId, getWelcomeText(), { reply_markup: MAIN_MENU });
      return;
    }
    
    if (cmd === '/help') {
      await sendMessage(env.TELEGRAM_TOKEN, chatId, getHelpText(), { reply_markup: menuFor('help') });
      return;
    }
    
    if (cmd === '/chat' || cmd === '/code') {
      memory[`mode:${chatId}`] = cmd.slice(1);
      const modeName = cmd === '/chat' ? 'Чат' : 'Код';
      await sendMessage(env.TELEGRAM_TOKEN, chatId,
        `💬 <b>Режим: ${modeName}</b>\nНапиши что-нибудь!`,
        { reply_markup: menuFor(cmd.slice(1)) });
      return;
    }
    
    if (cmd === '/agents') {
      await sendMessage(env.TELEGRAM_TOKEN, chatId, getAgentsText(), { reply_markup: menuFor('agents') });
      return;
    }
    
    if (cmd === '/settings') {
      const mode = memory[`mode:${chatId}`] || 'auto';
      await sendMessage(env.TELEGRAM_TOKEN, chatId,
        `⚙️ <b>Настройки</b>\n\nРежим: ${mode}\nПровайдер: GitHub Models (GPT-4o)`,
        { reply_markup: { inline_keyboard: [[{ text: '🏠 Главное меню', callback_data: 'menu_main' }]] } });
      return;
    }
    
    await sendMessage(env.TELEGRAM_TOKEN, chatId, 'Неизвестная команда. Используй /help', { reply_markup: MAIN_MENU });
    return;
  }
  
  // Regular message — AI processing
  const mode = memory[`mode:${chatId}`] || 'auto';
  const history = memory[`history:${chatId}`] || [];
  
  const messages = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...history.slice(-10),
    { role: 'user', content: text },
  ];
  
  const { text: response, provider } = await askAI(messages, env);
  
  // Save history
  history.push({ role: 'user', content: text.slice(0, 200) });
  history.push({ role: 'assistant', content: response.slice(0, 500) });
  if (history.length > 20) history.splice(0, history.length - 20);
  memory[`history:${chatId}`] = history;
  
  // Send response
  const footer = `\n\n<small>⚡ ${provider} · @Gptzloy_bot</small>`;
  await sendMessage(env.TELEGRAM_TOKEN, chatId, response + footer, {
    reply_markup: MAIN_MENU,
  });
}

// ======================== CALLBACK HANDLER ========================

async function handleCallback(cb, env) {
  const data = cb.data || '';
  const cbId = cb.id;
  const chatId = cb.message?.chat?.id;
  const msgId = cb.message?.message_id;
  
  await answerCallback(env.TELEGRAM_TOKEN, cbId, `→ ${data}`);
  
  if (!chatId || !msgId) return;
  
  const texts = {
    menu_main: getWelcomeText(),
    mode_help: getHelpText(),
    mode_agents: getAgentsText(),
  };
  
  const keyboards = {
    menu_main: MAIN_MENU,
    mode_help: menuFor('help'),
    mode_agents: menuFor('agents'),
  };
  
  if (texts[data]) {
    await editMessage(env.TELEGRAM_TOKEN, chatId, msgId, texts[data], {
      reply_markup: keyboards[data],
    });
    return;
  }
  
  if (data === 'mode_chat' || data === 'mode_code' || data === 'mode_search') {
    memory[`mode:${chatId}`] = data.replace('mode_', '');
    const modeNames = { mode_chat: 'Чат', mode_code: 'Код', mode_search: 'Поиск' };
    await editMessage(env.TELEGRAM_TOKEN, chatId, msgId,
      `💬 <b>Режим: ${modeNames[data]}</b>\nНапиши что-нибудь!`,
      { reply_markup: menuFor(data.replace('mode_', '')) });
    return;
  }
  
  if (data === 'mode_settings') {
    const mode = memory[`mode:${chatId}`] || 'auto';
    await editMessage(env.TELEGRAM_TOKEN, chatId, msgId,
      `⚙️ <b>Настройки</b>\n\nРежим: ${mode}\nПровайдер: GitHub Models (GPT-4o)`,
      { reply_markup: { inline_keyboard: [[{ text: '🏠 Главное меню', callback_data: 'menu_main' }]] } });
    return;
  }
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(),
    },
  });
}
