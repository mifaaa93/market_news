# Market News

Telegram-бот с ежедневным дайджестом рынков. Полный текст новости открывается внутри бота; кнопок перехода на сайты изданий нет.

## Запуск (Windows)

1. В BotFather создайте бота и скопируйте токен.
2. Скопируйте `.env.example` в `.env` и вставьте токен в `BOT_TOKEN`.
3. Запустите `start.bat`.

Вручную:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Проверка без Telegram: `.\.venv\Scripts\python.exe -m unittest discover -s tests`

## Развёртывание на сервере (Linux, от root)

Бот работает через long polling: входящие порты для него не нужны. Нужен исходящий HTTPS к `api.telegram.org`, RSS-лентам и (если задан ключ) к `CVC_BASE_URL`. SQLite и лог пишутся в каталог `data/`. Python 3.11 или новее.

Ниже — Ubuntu/Debian. Команды выполняйте от root.

### 1. Пакеты

```bash
apt update
apt install -y python3 python3-venv python3-pip git
```

Опционально, если нужен лендинг на 80/443:

```bash
apt install -y nginx
```

### 2. Код

Скопируйте проект в `/opt/market_news`. Через git:

```bash
mkdir -p /opt
cd /opt
git clone <url-репозитория> market_news
cd /opt/market_news
```

Или с машины разработчика (PowerShell, из корня проекта):

```powershell
scp -r . root@<сервер>:/opt/market_news
```

На сервере не копируйте `__pycache__`, `.venv` и `data/*.sqlite3-shm` / `data/*.sqlite3-wal`, если переносите уже работающую базу — остановите бота, сделайте checkpoint и копируйте только `data/market_news.sqlite3`.

```bash
cd /opt/market_news
mkdir -p data
chmod 700 /opt/market_news
```

### 3. Виртуальное окружение

```bash
cd /opt/market_news
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Проверка: `.venv/bin/python -m unittest discover -s tests`

### 4. Конфиг `.env`

```bash
cd /opt/market_news
cp .env.example .env
chmod 600 .env
nano .env
```

Обязательно заполните:

- `BOT_TOKEN` — токен из BotFather
- `BOT_USERNAME` — username бота без `@`
- `LANDING_BOT_URL` — `https://t.me/<username>`
- `ADMIN_USER_ID` — Telegram ID админа для `/admin`
- `CVC_API_KEY` — если нужны перевод и AI-поиск RSS; без ключа бот работает, перевод и AI-discovery выключены

Остальные поля можно оставить как в `.env.example`. Файл `.env` в git не коммитьте.

### 5. systemd

```bash
cat >/etc/systemd/system/market-news.service <<'EOF'
[Unit]
Description=Market News Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/market_news
ExecStart=/opt/market_news/.venv/bin/python main.py
Restart=always
RestartSec=5
TimeoutStopSec=30
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now market-news
systemctl status market-news --no-pager
```

Логи:

```bash
journalctl -u market-news -f
tail -f /opt/market_news/data/bot.log
```

Полезные команды:

```bash
systemctl restart market-news
systemctl stop market-news
```

В логе при старте должна быть строка `Market News is up`. Если сразу падает — проверьте `BOT_TOKEN` и `journalctl -u market-news -n 100`.

### 6. Лендинг (по желанию)

Статика лежит в `landing/index.html`. Пример nginx:

```nginx
server {
    listen 80;
    server_name example.com;
    root /opt/market_news/landing;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
ln -sf /etc/nginx/sites-available/market-news /etc/nginx/sites-enabled/market-news
nginx -t && systemctl reload nginx
```

HTTPS: `apt install -y certbot python3-certbot-nginx` и `certbot --nginx -d example.com`. Ссылка на бота на лендинге должна совпадать с `LANDING_BOT_URL`.

### 7. Обновление кода

```bash
systemctl stop market-news
cd /opt/market_news
# git pull  или  заново скопировать файлы
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests
systemctl start market-news
```

### 8. Бэкап SQLite

База: `/opt/market_news/data/market_news.sqlite3`. Копировать файл на лету нельзя надёжно. Сделайте snapshot:

```bash
apt install -y sqlite3
mkdir -p /root/backups
sqlite3 /opt/market_news/data/market_news.sqlite3 ".backup '/root/backups/market_news-$(date +%F).sqlite3'"
```

Восстановление: `systemctl stop market-news`, подмените `data/market_news.sqlite3`, удалите `-wal`/`-shm` если они остались от старой сессии, `systemctl start market-news`.

## Команды

- `/start` — три главные новости и меню
- `/digest` и `/today` — дайджест дня
- `/analytics` — раскладка по темам
- `/settings` — язык, час рассылки, часовой пояс
- `/help` — справка

Интерфейс по умолчанию русский, в настройках есть английский. Заголовки приходят на языке источника.

## Откуда новости

ABC News Business, BBC Business, CNBC, OilPrice, CoinDesk, U.S. EIA и Federal Reserve (всего одиннадцать RSS-лент). Из-за отсутствия доступного полного текста MarketWatch, Investing.com, Yahoo Finance и устаревшая лента CNN исключены из каталога. Релизы EIA и выступления ФРС выходят не каждый день; короткие материалы не проходят фильтр полного текста. Общая лента обновляется каждые 20 минут; Pro опрашивает выбранные ленты каждые 5 минут. Рассылка — раз в день в выбранный час.

## Подписка

На главном экране доступны тарифы Telegram Stars:

- Базовый — до 5 включённых лент и дневной дайджест.
- Plus — 200 Stars на 30 дней, до 100 слотов, до 5 своих сайтов и уведомление по новой статье.
- Pro — 500 Stars на 30 дней, до 500 слотов, до 20 своих сайтов и опрос выбранных лент каждые 5 минут.

Каталог и выбор лент находятся в разделе «Моя лента». Пользовательский RSS-адрес сохраняется только после успешной проверки.

## Админка подписок

Команда `/admin` доступна только Telegram ID `480055341` и не показывается в общем меню. В разделе можно выдать подписку, проверить статус и отозвать её. Для выдачи: выберите кнопку и отправьте `ID plus 30` или `ID pro 30` (допустимо 1–365 дней; без срока — 30). Пользователь для выдачи может ещё не запускать бота; для проверки и отзыва он должен быть зарегистрирован. Повторная выдача продлевает существующий активный срок; отзыв требует подтверждения и отключает платные функции, **не возвращая Stars автоматически**. События записываются в `admin_actions`.

При добавлении сайта бот сначала ищет RSS/Atom обычным способом: `<link>`, стандартные пути `/feed`, `/rss`, `/atom.xml` и варианты раздела. Если это не помогло и настроен `CVC_API_KEY`, включается AI-подсказка кандидатов (может расходовать средства на счёте провайдера). В ИИ передаются URL сайта, заголовок и отобранные ссылки со страницы, а не текст статей. AI только предлагает URL; домен, RSS-формат, статью и полный текст повторно проверяет код. Сокращатели, соцсети, локальные и внутренние IP, небезопасные редиректы запрещены.

Новости парсятся и сохраняются отдельно от перевода. Переводчик-воркер проверяет готовые статьи каждые 10 секунд, переводит их и сразу запускает индивидуальные уведомления.

Статичный лендинг: `landing/index.html`. Для просмотра извне (в PowerShell, из корня проекта):

```powershell
# Окно 1: статический сервер. Бот запускать для этого не требуется.
.\.venv\Scripts\python.exe -m http.server 8080 --bind 127.0.0.1 --directory landing

# Окно 2: после однократной настройки токена ngrok
ngrok config add-authtoken "<ваш authtoken>"
ngrok http 8080
```

Публичный HTTPS-адрес появится в строке `Forwarding` окна ngrok. Не публикуйте authtoken; кнопки лендинга ведут на `https://t.me/test99012_bot`. Оба окна должны оставаться открытыми.
