# Market News

Telegram-бот с ежедневным дайджестом рынков. Сбор только на английском: Top Headlines `business` четыре раза в сутки и Search каждые 5 минут. Русский и арабский — перевод через CVC. В «Моя лента» сначала издания из текущего топа.

## Запуск в Docker

1. Скопируйте `.env.example` в `.env`.
2. Заполните `BOT_TOKEN`, `GNEWS_API_KEY` и `POSTGRES_PASSWORD`.
3. Запустите:

```
docker compose up --build -d
```

Сервисы:

- `postgres` — PostgreSQL 16, на хосте `127.0.0.1:5433` (5432 на этой машине уже занят Champ)
- `bot` — long polling, исходящий HTTPS к Telegram и GNews
- `landing` — статика на `:8080`

Логи бота: `docker compose logs -f bot`.

Остановка: `docker compose down`. Данные Postgres остаются в volume `pgdata`.

## Локальный запуск без контейнера бота

Поднимите только базу: `docker compose up -d postgres`.

В `.env` укажите:

```
DATABASE_URL=postgresql://market_news:change_me@127.0.0.1:5433/market_news
```

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Проверка: `python -m unittest discover -s tests`

Интеграционные тесты базы включаются, если задан `TEST_DATABASE_URL`.

## Лимиты GNews

Essential: 1000 запросов в сутки, до 25 статей за запрос, без 12-часовой задержки. Топ: 3 запроса (en, ru, ar) в 00:00, 06:00, 12:00 и 18:00 UTC. Поиск: те же 3 языка каждые 5 минут (~876 запросов/сутки вместе с топом).

Дайджест, главная и «новость дня» показывают текущий снимок топа. «Последние», категории и пуши — выбранные источники из поиска.

Пользователь видит и получает пуши только по выбранным источникам своего языка. Новому пользователю включаются топ-источники по числу новостей в пределах лимита тарифа. При смене языка включаются источники с тем же названием, если они есть.
