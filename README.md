# 🐾 PawWork Clone — Твой личный AI агент 24/7

**Клон PawWork, который живёт на бесплатных серверах 24/7.**

## Архитектура (5 бесплатных слоёв)

```
Ты ← Telegram / API → Cloudflare Worker (24/7, бесплатно)
                             ↓
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
           Groq API     GitHub Models   CF Workers AI
         (Llama 70B)     (GPT-4o)       (Qwen 1.5B)
         (Qwen 32B)     (DS R1)
                             ↓
                        GitHub ← файлы, деплой, Pages
                        
              ⚡ Colab (твои GGUF: qwen2, Moonlight, kimi-vl)
```

## Быстрый старт

### 1. Получи API ключи (все бесплатно, без карты)

| Сервис | Что даёт | Где взять |
|--------|----------|-----------|
| **Groq** | Llama 3.3 70B, Qwen 3 32B (1000/день) | https://console.groq.com/keys |
| **GitHub Models** | GPT-4o, Llama 4, DeepSeek R1 | https://github.com/settings/tokens |
| **Google Gemini** | Gemini 2.5 Flash (бесплатно) | https://aistudio.google.com/app/apikey |
| **Cloudflare** | Workers + KV (бесплатно) | https://dash.cloudflare.com |
| **ngrok** | Туннель для Colab | https://dashboard.ngrok.com |

### 2. Настрой

```bash
git clone https://github.com/muromec061-cyber/pawwork-clone
cd pawwork-clone
```

### 3. Деплой

```bash
# 1. Отредактируй deploy/deploy.js — вставь ACCOUNT_ID и API_TOKEN
# 2. Запусти:
node deploy/deploy.js

# 3. Открой URL из вывода и настрой секреты в Dashboard
```

### 4. Colab (твои GGUF модели — опционально)

1. Открой https://colab.research.google.com/
2. File → Upload notebook → выбери `colab/ollama-server.ipynb`
3. Runtime → Run all (выбери GPU T4)
4. Полученный URL вставь в COLAB_URL и COLAB_KEY в Cloudflare Worker

## API

```
GET  /                          — статус
POST /v1/chat                   — чат
POST /v1/agent                  — ReAct агент
POST /v1/code                   — генерация кода
POST /v1/file                   — файловые операции
POST /v1/deploy                 — деплой на GitHub
POST /v1/memory                 — память
POST /v1/providers              — список активных провайдеров
POST /webhook                   — Telegram webhook
```

Все запросы: `Authorization: Bearer {PAWWORK_API_KEY}`

## Telegram бот

После деплоя открой в браузере:
```
https://{worker}.{account}.workers.dev/set-webhook
```

Напиши `/start` боту @pawwork_ai_bot и пользуйся.
