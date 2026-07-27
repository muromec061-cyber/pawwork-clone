// ===========================================================
//   PawWork Clone — Deploy to Cloudflare Workers
//   Не требует Wrangler, чистое API
// ===========================================================
const https = require('https');
const fs = require('fs');
const path = require('path');

// ⚠️ ВСТАВЬ СВОИ ДАННЫЕ:
const ACCOUNT_ID = '97967f6692e43872b7cd74ebff3788ba';
const API_TOKEN = '';  // <<< Новый токен с правами Workers:Edit
const WORKER_NAME = 'pawwork-clone';

const WORKER_PATH = path.join(__dirname, '..', 'src', 'worker.js');
const KV_NAME = 'pawwork-memory';

// ====== HTTP HELPER ======
function httpsReq(method, host, pathname, body = null, headers = {}) {
  return new Promise((resolve, reject) => {
    const opts = { host, path: pathname, method, headers: { ...headers } };
    if (body) opts.headers['Content-Length'] = Buffer.byteLength(body);

    const req = https.request(opts, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ status: res.statusCode, ...parsed });
        } catch {
          resolve({ status: res.statusCode, raw: data.slice(0, 500) });
        }
      });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

function cfApi(method, path, body = null) {
  const url = new URL(path, 'https://api.cloudflare.com');
  return httpsReq(method, 'api.cloudflare.com', url.pathname + url.search, body, {
    'Authorization': `Bearer ${API_TOKEN}`,
    'Content-Type': 'application/json',
  });
}

// ====== MAIN ======
async function deploy() {
  console.log('🚀 PawWork Clone — Deploy\n');

  if (!API_TOKEN) {
    console.log('❌ API_TOKEN не задан!');
    console.log('1. Зайди: https://dash.cloudflare.com/profile/api-tokens');
    console.log('2. Создай токен с правами: Workers:Edit, Workers KV:Write');
    console.log('3. Вставь токен в API_TOKEN в deploy.js\n');
    process.exit(1);
  }

  // 1. Создаём KV namespace
  console.log(`📦 Создаю KV: ${KV_NAME}...`);
  let kvId = null;
  const listRes = await cfApi('GET', `/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces`);
  if (listRes.success) {
    const existing = listRes.result.find(n => n.title === KV_NAME);
    if (existing) {
      kvId = existing.id;
      console.log(`   ✅ KV уже существует: ${kvId}`);
    }
  }
  if (!kvId) {
    const createRes = await cfApi('POST', `/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces`, {
      title: KV_NAME
    });
    if (createRes.success) {
      kvId = createRes.result.id;
      console.log(`   ✅ KV создан: ${kvId}`);
    } else {
      console.log(`   ❌ Ошибка KV: ${JSON.stringify(createRes.errors)}`);
    }
  }

  // 2. Читаем worker.js
  const workerCode = fs.readFileSync(WORKER_PATH, 'utf-8');
  console.log(`   📄 Worker: ${(workerCode.length / 1024).toFixed(1)} KB`);

  // 3. Загружаем worker
  console.log(`\n📦 Загружаю worker: ${WORKER_NAME}...`);
  const uploadRes = await cfApi('PUT', `/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${WORKER_NAME}`, workerCode, {
    'Authorization': `Bearer ${API_TOKEN}`,
    'Content-Type': 'application/javascript',
  });

  if (uploadRes.success || uploadRes.status === 200) {
    // Обновляем привязку KV
    if (kvId) {
      console.log(`   🔗 Привязываю KV...`);
      const bindRes = await cfApi('PUT', `/client/v4/accounts/${ACCOUNT_ID}/workers/scripts/${WORKER_NAME}`, workerCode, {
        'Authorization': `Bearer ${API_TOKEN}`,
        'Content-Type': 'application/javascript',
        'X-Cf-Worker-Kv-Name': KV_NAME,
        'X-Cf-Worker-Kv-Id': kvId,
      });
    }

    console.log(`\n✅ Worker загружен!`);
    console.log(`   URL: https://${WORKER_NAME}.${ACCOUNT_ID}.workers.dev`);
    console.log(`   Dashboard: https://dash.cloudflare.com/${ACCOUNT_ID}/workers/view/${WORKER_NAME}`);
  } else {
    console.log(`\n❌ Ошибка: ${JSON.stringify(uploadRes.errors || uploadRes)}`);

    if (uploadRes.status === 403 || uploadRes.status === 401) {
      console.log('\n🔑 Проблема с токеном! Создай новый:');
      console.log('   1. https://dash.cloudflare.com/profile/api-tokens');
      console.log('   2. "Create Token" → "Edit Cloudflare Workers"');
      console.log('   3. В Account Resources выбери свой аккаунт');
      console.log('   4. Вставь новый токен в deploy.js');
    }
  }

  // 4. Настраиваем секреты (env variables)
  console.log(`\n🔐 Настройка секретов (через Dashboard):`);
  console.log(`   ${'='.repeat(50)}`);
  console.log(`   Обязательно добавь в Workers → ${WORKER_NAME} → Settings → Variables:`);
  console.log(`   ${'='.repeat(50)}`);
  console.log(`   PAWWORK_API_KEY    — твой личный ключ API`);
  console.log(`   GROQ_API_KEY       — https://console.groq.com/keys`);
  console.log(`   GITHUB_TOKEN       — https://github.com/settings/tokens`);
  console.log(`   TELEGRAM_BOT_TOKEN — @BotFather`);
  console.log(`   CF_ACCOUNT         — ${ACCOUNT_ID}`);
  console.log(`   CF_API_TOKEN       — Cloudflare API токен`);
  console.log(`   GEMINI_API_KEY     — https://aistudio.google.com/app/apikey`);
  console.log(`   COLAB_URL          — URL от Colab (опционально)`);
  console.log(`   COLAB_KEY          — ключ для Colab (опционально)`);
  console.log(`   ${'='.repeat(50)}`);

  // 5. Настройка Telegram webhook
  console.log(`\n📱 Настройка Telegram webhook:`);
  console.log(`   GET https://${WORKER_NAME}.${ACCOUNT_ID}.workers.dev/set-webhook?url=https://${WORKER_NAME}.${ACCOUNT_ID}.workers.dev/webhook`);
  console.log(`   (Или отправь этот URL в браузере после деплоя)`);
}

deploy().catch(console.error);
