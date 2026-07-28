# 🚀 PawWork VPS Ultimate — Полный гайд

## Быстрый старт (2 минуты)

```bash
# 1. Установи всё одной командой:
curl -fsSL https://raw.githubusercontent.com/muromec061-cyber/pawwork-clone/master/deploy-vps.sh | sudo bash

# Или если хочешь настроить:
curl -fsSL https://raw.githubusercontent.com/muromec061-cyber/pawwork-clone/master/deploy-vps.sh > deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

## Получить бесплатный VPS с root (без карты)

### Вариант 1: FreeVPS.info (6GB RAM, 120GB NVMe)
1. Зайди на https://freevps.info
2. Нажми "Claim Free VPS"
3. Укажи email (любой) — без карты
4. Получишь SSH root доступ через email
5. Подключись: `ssh root@твой-ip`

### Вариант 2: GratisVPS.net (2GB RAM)
1. Зайди на https://gratisvps.net
2. Нажми "Create Free VPS"
3. Верификация по email — без карты
4. Полный root доступ

### Вариант 3: GitHub Codespaces (через браузер)
1. Открой https://github.com/muromec061-cyber/pawwork-clone
2. Code → Create codespace on master
3. Готово — VSCode в браузере с 4 cores, 8GB RAM, 60h/мес бесплатно
4. В терминале Codespaces запусти: `bash deploy-vps.sh`

## Что будет установлено

| Компонент | Порт | Назначение |
|-----------|------|------------|
| **Ollama** | 11434 | Локальные AI модели |
| **Portainer** | 9000 | Docker веб-панель |
| **Telegram Bot** | 8080 | @Gptzloy_bot |
| **Nginx Proxy Manager** | 81 | Прокси + SSL |
| **Uptime Kuma** | 3001 | Мониторинг 24/7 |
| **OpenClaw** | 3737 | AI ассистент (384k⭐) |
| **CrewAI** | — | Мульти-агенты (56k⭐) |
| **Eliza OS** | — | Agentic OS (19k⭐) |

## Использование бота

Напиши **@Gptzloy_bot** в Telegram:

```
нарисуй киберпанк кота в космосе
/image красивая девушка в стиле cyberpunk
/ask какой фреймворк лучше для AI агентов?
/ollama
/portainer
```

## Управление

```bash
# Статус всех сервисов
systemctl status docker ollama openclaw pawwork-bot

// Перезапуск всего
systemctl restart docker ollama openclaw pawwork-bot

# Логи бота
journalctl -u pawwork-bot -f -n 50

# Логи OpenClaw
journalctl -u openclaw -f -n 50
```

## Требования

- Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- Минимум 1GB RAM (рекомендуется 4GB+)
- Root доступ
- Открытые порты: 80, 443, 8080, 9000, 3001
