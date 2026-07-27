// ===========================================================
//   Test PawWork Clone API
// ===========================================================
const https = require('https');

const WORKER_URL = 'https://pawwork-clone.YOUR_ACCOUNT.workers.dev';
const API_KEY = 'твой_ключ'; // PAWWORK_API_KEY

async function test() {
  const opts = {
    hostname: new URL(WORKER_URL).hostname,
    headers: { 'Content-Type': 'application/json' }
  };
  if (API_KEY) opts.headers['Authorization'] = `Bearer ${API_KEY}`;

  // Test health
  const health = await request('/');
  console.log('🏥 Health:', JSON.stringify(health, null, 2));

  // Test chat
  const chat = await request('/v1/chat', {
    messages: [
      { role: 'system', content: 'Ты полезный ассистент.' },
      { role: 'user', content: 'Напиши hello world на Python' }
    ]
  });
  console.log('\n💬 Chat:', JSON.stringify(chat, null, 2));

  // Test agent
  const agent = await request('/v1/agent', {
    prompt: 'Создай HTML страницу "Привет, мир!" и сохрани её как файл index.html',
    session_id: 'test-1'
  });
  console.log('\n🤖 Agent:', JSON.stringify(agent, null, 2));

  // Test providers
  const prov = await request('/v1/providers');
  console.log('\n🔌 Providers:', JSON.stringify(prov, null, 2));
}

function request(path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, WORKER_URL);
    const opts = {
      hostname: url.hostname,
      path: url.pathname,
      method: body ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json' }
    };
    if (API_KEY) opts.headers['Authorization'] = `Bearer ${API_KEY}`;

    const req = https.request(opts, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { resolve({ raw: data.slice(0, 500) }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

test().catch(console.error);
