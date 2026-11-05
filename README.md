# Market News

Telegram-бот с ежедневным дайджестом рынков. Сбор только на английском: Top Headlines `business` четыре раза в сутки и тематический Search по расписанию. Русский и арабский — перевод через CVC. В «Моя лента» сначала издания из текущего топа.

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

В текущем тарифе GNews: лимит 1000 запросов в сутки, до 25 статей за запрос. Сбор — один язык `en`, RU/AR переводятся после сохранения. Топ: один запрос в 00:00, 06:00, 12:00 и 18:00 UTC. Search: один запрос в минуту с 07:00 до 22:00 по `GNEWS_SEARCH_TIMEZONE` (по умолчанию `Europe/Kiev`), ночью — раз в 30 минут. Поиск циклически чередует акции, макро/сырьё и крипто, а нерелевантные результаты отбрасываются перед записью в базу. При одном запросе на цикл расчётный расход составляет около 922 запросов в сутки (900 дневных + 18 ночных + 4 топа), с запасом для повторного запуска. Для другой частоты или количества страниц пересчитайте расход и лимит в `.env`.

`GNEWS_QUERY_STOCKS`, `GNEWS_QUERY_MACRO` и `GNEWS_QUERY_CRYPTO` задают запросы по темам. `GNEWS_DAY_SEARCH_MINUTES` и `GNEWS_NIGHT_SEARCH_MINUTES` задают интервалы. Старый `GNEWS_QUERY_EN` остаётся запасным запросом, если тема задана пустой строкой.

Дайджест, главная и «новость дня» показывают текущий снимок топа. «Последние», категории и пуши — выбранные источники из поиска.

Пользователь видит и получает пуши только по выбранным источникам своего языка. Новому пользователю включаются топ-источники по числу новостей в пределах лимита тарифа. При смене языка включаются источники с тем же названием, если они есть.
# Menu artwork

Premium menu covers are stored in `assets/menu/`. They use one shared
text-free visual style, so the same images work for `ru`, `en`, and `ar`
without localization variants or typography artifacts.

