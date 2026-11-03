"""Тексты интерфейса. Новости в них не входят — только оболочка бота."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "tagline": "Ежедневная аналитика рынков",
        "today_head": "Сегодняшние главные новости:",
        "updated": "Обновлено: {stamp} ({tz})",
        "disclaimer": "Не является инвестиционной рекомендацией.",
        "source": "Источник",
        "topic": "Тема",
        "loading": "Собираю свежие заголовки из рабочих деловых RSS-лент. Через несколько секунд здесь будут новости дня.",
        "empty": "Ленты источников сейчас не ответили. Меню на месте: откройте дайджест чуть позже — бот подтянет материалы сам.",
        "no_summary": "В ленте не было отдельного абзаца. Ниже источник и соседние материалы по теме. Цифры бот не додумывает.",
        "open_later": "Текст выше сохранён из ленты издания.",
        "links_ready": "",
        "full_note": "Это текст публикации {source}. Оценки и цифры — из исходного материала, бот их не добавляет.",
        "related": "Рядом по теме",
        "no_article": "Этого материала уже нет в ленте. Откройте свежий дайджест.",
        "empty_cat": "В теме «{cat}» пока нет свежих материалов. Выберите другую тему или общий дайджест.",
        "unknown": "Я веду по рынку через кнопки под сообщением. Начните с дайджеста или откройте /help.",
        "digest_title": "Дайджест дня",
        "analytics_title": "Аналитика",
        "latest_title": "Последние новости",
        "cats_title": "Темы",
        "settings_title": "Настройки",
        "sources_title": "Источники",
        "week_title": "Недельная подборка",
        "plus_title": "Подписка Market News",
        "plots": "Главные сюжеты",
        "spread": "Как распределились материалы",
        "brief": "Короткий разбор",
        "by_topic": "По темам",
        "analytics_blurb": "В свежей подборке чаще встречается тема «{cat}» — материалов: {n}. Начать можно с «{title}» ({source}). Здесь только уже вышедшие новости: бот не прогнозирует цены и не советует, что покупать или продавать.",
        "cats_intro": "Темы за последние дни. Каждый материал открывается внутри бота.",
        "latest_intro": "Свежие публикации по времени выхода.",
        "digest_intro": "Главное за день. Откройте любой пункт — текст останется в боте.",
        "week_intro": "Двенадцать материалов за семь дней, по разным темам.",
        "sources_locked": "Издания, из которых собран дайджест.",
        "sources_open": "Издания, из которых собран дайджест.",
        "sources_intro": "Рабочие ленты, которые бот использует для новостей. Переходов на внешние сайты здесь нет.",
        "sources_line": "В этом выпуске: {names}.",
        "only_one": "В этой подборке пока одна новость",
        "mail_footer": "Ежедневная рассылка Market News. Час и язык меняются в /settings.",
        "settings_lang": "Язык интерфейса: {lang}",
        "settings_push_on": "Рассылка включена, в {hour}:00 ({tz})",
        "settings_push_off": "Рассылка выключена",
        "plus_active": "Plus активен до {until}",
        "plus_off": "Подписка не подключена. Дайджест, аналитика и полный текст остаются бесплатными.",
        "plus_pitch": "Лента рынка в одном окне. Базовый тариф — 0 Stars: до 5 лент и дневной дайджест. Plus — {plus_stars} Stars на 30 дней: до {plus_limit} слотов, до 5 своих сайтов и сообщение по новой статье. Pro — {pro_stars} Stars: до {pro_limit} слотов, до 20 своих сайтов и опрос каждые 5 минут.",
        "plus_thanks": "{plan} подключён до {until}. Дневной дайджест остаётся доступен.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 дней: больше источников и сообщение в чат по новой статье.",
        "plans_title": "Тарифы Market News",
        "plans_text": "В каталоге сейчас {catalog} рабочих лент.\n\nБазовый — 0 Stars: до 5 включённых лент, дневной дайджест.\n\nPlus — 200 Stars / 30 дней: до 100 слотов, до 5 своих сайтов, сообщение при сохранении материала.\n\nPro — 500 Stars / 30 дней: до 500 слотов, до 20 своих сайтов, опрос выбранных лент каждые 5 минут.",
        "feed_title": "Моя лента",
        "feed_intro": "Включите источники в пределах слотов вашего тарифа. В ленте и уведомлениях показываются только материалы с полным текстом.",
        "feed_locked": "нужен {plan}",
        "add_source_prompt": "Пришлите https-адрес сайта или RSS. Бот найдёт ленту и проверит полный текст. Если обычный поиск не сработает, адрес сайта и названия ссылок могут быть переданы сервису ИИ для подсказки RSS. На базовом тарифе сначала откройте подписку.",
        "source_added": "Источник добавлен в вашу ленту: {name}.",
        "source_failed": "С этого адреса не удалось собрать рабочую ленту. Пришлите другой https-адрес.",
        "admin_title": "Админка подписок",
        "admin_intro": "Закрытый раздел.\nВыдача: ID тариф срок_дней — например: 123456789 pro 30.\nОтзыв или статус: просто ID.",
        "admin_grant": "Выдать подписку",
        "admin_revoke": "Забрать подписку",
        "admin_status": "Проверить статус",
        "admin_prompt_grant": "Отправьте: ID тариф срок_дней\nПример: 123456789 plus 30",
        "admin_prompt_user": "Отправьте Telegram ID пользователя.",
        "admin_bad_input": "Не удалось разобрать данные. Попробуйте ещё раз.",
        "admin_not_found": "Пользователь с таким ID ещё не запускал бота.",
        "admin_granted": "Готово: {plan} выдан пользователю {user_id} до {until}.",
        "admin_revoked": "Подписка пользователя {user_id} отозвана.",
        "admin_status_result": "Пользователь {user_id}: {status}.",
        "admin_confirm": "Подтвердить отзыв",
        "admin_cancel": "Отмена",
        "admin_confirm_question": "Отозвать {status} у пользователя {user_id}? Звёзды не возвращаются автоматически.",
        "admin_user_granted": "Вам подключён {plan} до {until}.",
        "admin_user_revoked": "Ваша подписка отозвана администратором. Бесплатный дайджест остаётся доступен.",
        "admin_confirm_wait": "Для отзыва нажмите кнопку подтверждения. Для отмены нажмите «Отмена» или /admin.",
        "admin_expired": "Подтверждение устарело. Откройте /admin заново.",
        "source_duplicate": "Этот адрес уже добавлен в вашу ленту.",
        "subscription_status": "Статус: {status}",
        "pay_failed": "Окно оплаты не открылось. Новости по-прежнему доступны через меню.",
        "story_empty": "Новость дня появится, когда лента ответит. Откройте дайджест через минуту.",
        "opening": "Открываю полный текст…",
        "full_missing": "Полный текст на сайте издания не открылся. Ниже то, что было в ленте.",
        "error": "Не вышло открыть этот экран. Нажмите /start.",
        "cat_stocks": "Акции",
        "cat_oil": "Нефть и газ",
        "cat_macro": "Макро",
        "cat_crypto": "Крипта",
        "cat_markets": "Рынки",
        "btn_digest": "📅 Полный дайджест",
        "btn_analytics": "📊 Аналитика",
        "btn_latest": "📰 Последние",
        "btn_cats": "🗂 Категории",
        "btn_story": "⭐ Новость дня",
        "btn_settings": "⚙️ Настройки",
        "btn_help": "ℹ️ Помощь",
        "btn_full": "Читать полностью",
        "btn_next": "Следующая",
        "btn_menu": "В меню",
        "btn_back": "Назад",
        "btn_collapse": "Свернуть",
        "btn_push_on": "Включить рассылку",
        "btn_push_off": "Выключить рассылку",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "Продлить Plus",
        "btn_week": "🗓 Недельная подборка",
        "btn_pay": "Оплатить {stars} Stars",
        "btn_sources": "📚 Источники",
        "btn_subscription": "⭐ Подписка",
        "btn_my_feed": "📰 Моя лента",
        "btn_add_source": "➕ Добавить источник",
        "btn_read": "Читать",
        "btn_pay_plus": "Plus · 200 Stars",
        "btn_pay_pro": "Pro · 500 Stars",
        "btn_plan_plus": "Plus",
        "btn_plan_pro": "Pro",
        "btn_plan_base": "нет подписки",
        "admin_grant": "Выдать подписку",
        "admin_revoke": "Забрать подписку",
        "admin_status": "Проверить статус",
        "src_investing": "Деловые новости и рынки.",
        "src_cnn": "Новости бизнеса и экономики.",
        "src_yahoo": "Рынки, компании и финансы.",
        "src_default": "Рабочая RSS-лента деловых новостей.",
        "src_bbc": "Деловые новости и компании со всего мира.",
        "src_cnbc": "Рынки, экономика, отчётность и энергия.",
        "src_mw": "Новости рынков и компаний.",
        "src_oil": "Нефть, газ и энергетика.",
        "src_coin": "Криптовалютные рынки.",
        "src_eia": "Данные и публикации об энергетических рынках США.",
        "src_fed": "Решения о денежной политике и выступления представителей ФРС.",
        "src_abc": "Деловые новости и рынки.",
        "help": """<b>Помощь</b>

Market News присылает деловые новости и короткую сводку по рынку.

<b>Команды</b>
/start — главные новости сейчас
/digest — дайджест дня
/today — то же, что дайджест
/analytics — раскладка по темам
/settings — язык и рассылка
/help — эта справка

<b>Как читать</b>
Откройте дайджест, затем новость. «Читать полностью» показывает текст внутри бота.

<b>Рассылка</b>
Один раз в день, в час из настроек. Там же её можно выключить.

<b>Откуда новости</b>
ABC News Business, BBC Business, CNBC, OilPrice, CoinDesk, U.S. EIA, Federal Reserve.

Это не инвестиционная рекомендация и не прогноз цен.""",
    },
    "en": {
        "tagline": "Daily market analytics",
        "today_head": "Today's top stories:",
        "updated": "Updated: {stamp} ({tz})",
        "disclaimer": "Not investment advice.",
        "source": "Source",
        "topic": "Topic",
        "loading": "Collecting fresh headlines from working business RSS feeds. Today's stories will show up here in a few seconds.",
        "empty": "The source feeds did not answer. The menu still works: open the digest in a minute and the bot will load the stories.",
        "no_summary": "The feed had no standalone paragraph. The source and nearby stories are below. The bot does not invent figures.",
        "open_later": "The text above is saved from the publisher's feed.",
        "links_ready": "",
        "full_note": "This is the text from {source}. Figures and judgements come from the original piece; the bot does not add any.",
        "related": "Nearby on this topic",
        "no_article": "This story is no longer in the feed. Open a fresh digest.",
        "empty_cat": "Nothing fresh in “{cat}” yet. Pick another topic or the main digest.",
        "unknown": "Use the buttons under the message. Start with the digest, or open /help.",
        "digest_title": "Daily digest",
        "analytics_title": "Analytics",
        "latest_title": "Latest news",
        "cats_title": "Topics",
        "settings_title": "Settings",
        "sources_title": "Sources",
        "week_title": "Weekly briefing",
        "plus_title": "Market News Subscription",
        "plots": "Main stories",
        "spread": "How the stories are split",
        "brief": "Short read",
        "by_topic": "By topic",
        "analytics_blurb": "In the latest batch, “{cat}” shows up most often — {n} stories. A sensible place to start is “{title}” ({source}). This is only news that is already out: the bot does not forecast prices or tell you what to buy or sell.",
        "cats_intro": "Topics from the last few days. Every story opens inside the bot.",
        "latest_intro": "The newest stories, in the order they were published.",
        "digest_intro": "The main stories of the day. Open any item and the text stays in the bot.",
        "week_intro": "Twelve stories from the last seven days, across topics.",
        "sources_locked": "Publishers behind the digest.",
        "sources_open": "Publishers behind the digest.",
        "sources_intro": "Working feeds used by the bot. There are no external-site buttons here.",
        "sources_line": "In this edition: {names}.",
        "only_one": "This list has only one story so far",
        "mail_footer": "Daily Market News delivery. Change the hour or the language in /settings.",
        "settings_lang": "Interface language: {lang}",
        "settings_push_on": "Delivery is on, at {hour}:00 ({tz})",
        "settings_push_off": "Delivery is off",
        "plus_active": "Plus is active until {until}",
        "plus_off": "No subscription is active. The digest, analytics and full text stay free.",
        "plus_pitch": "One market feed in one place. Basic: 0 Stars, up to 5 feeds and a daily digest. Plus: {plus_stars} Stars for 30 days, up to {plus_limit} slots, 5 custom sites and a message for each new story. Pro: {pro_stars} Stars, up to {pro_limit} slots, 20 custom sites and a five-minute polling cycle.",
        "plus_thanks": "{plan} is active until {until}. The daily digest remains available.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 days: more sources and a chat message for each new story.",
        "plans_title": "Market News plans",
        "plans_text": "There are {catalog} working feeds in the catalog now.\n\nBasic — 0 Stars: up to 5 included feeds, daily digest.\n\nPlus — 200 Stars / 30 days: up to 100 slots, 5 custom sites, message when a story is saved.\n\nPro — 500 Stars / 30 days: up to 500 slots, 20 custom sites, selected feeds polled every 5 minutes.",
        "feed_title": "My feed",
        "feed_intro": "Enable sources within your plan's slots. Only stories with full text appear in the feed and alerts.",
        "feed_locked": "needs {plan}",
        "add_source_prompt": "Send an https website or RSS address. The bot will verify the feed and a full story. If normal discovery fails, the site address and link names may be sent to an AI provider for RSS suggestions. Basic users should open plans first.",
        "source_added": "Source added to your feed: {name}.",
        "source_failed": "Could not build a working feed from this address. Send another https address.",
        "admin_title": "Subscription admin",
        "admin_intro": "Private section.\nGrant: ID plan days — for example: 123456789 pro 30.\nRevoke or status: send only the ID.",
        "admin_grant": "Grant subscription",
        "admin_revoke": "Revoke subscription",
        "admin_status": "Check status",
        "admin_prompt_grant": "Send: ID plan days\nExample: 123456789 plus 30",
        "admin_prompt_user": "Send the user's Telegram ID.",
        "admin_bad_input": "Could not parse the data. Try again.",
        "admin_not_found": "This user has not started the bot yet.",
        "admin_granted": "Done: {plan} granted to {user_id} until {until}.",
        "admin_revoked": "Subscription for {user_id} was revoked.",
        "admin_status_result": "User {user_id}: {status}.",
        "admin_confirm": "Confirm revocation",
        "admin_cancel": "Cancel",
        "admin_confirm_question": "Revoke {status} for user {user_id}? Stars are not automatically refunded.",
        "admin_user_granted": "Your {plan} subscription is active until {until}.",
        "admin_user_revoked": "Your subscription has been revoked by an admin. The free digest is still available.",
        "admin_confirm_wait": "Use the confirmation button to revoke. To cancel, tap Cancel or /admin.",
        "admin_expired": "Confirmation expired. Open /admin again.",
        "source_duplicate": "This address is already in your feed.",
        "subscription_status": "Status: {status}",
        "pay_failed": "The payment window did not open. The news is still available from the menu.",
        "story_empty": "The story of the day will appear once the feed answers. Open the digest in a minute.",
        "opening": "Opening the full text…",
        "full_missing": "The full text did not open on the publisher site. Below is what the feed had.",
        "error": "This screen did not open. Tap /start.",
        "cat_stocks": "Stocks",
        "cat_oil": "Oil and gas",
        "cat_macro": "Macro",
        "cat_crypto": "Crypto",
        "cat_markets": "Markets",
        "btn_digest": "📅 Full digest",
        "btn_analytics": "📊 Analytics",
        "btn_latest": "📰 Latest",
        "btn_cats": "🗂 Categories",
        "btn_story": "⭐ Story of the day",
        "btn_settings": "⚙️ Settings",
        "btn_help": "ℹ️ Help",
        "btn_full": "Read in full",
        "btn_next": "Next",
        "btn_menu": "Menu",
        "btn_back": "Back",
        "btn_collapse": "Collapse",
        "btn_push_on": "Turn delivery on",
        "btn_push_off": "Turn delivery off",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "Renew Plus",
        "btn_week": "🗓 Weekly briefing",
        "btn_pay": "Pay {stars} Stars",
        "btn_sources": "📚 Sources",
        "btn_subscription": "⭐ Subscription",
        "btn_my_feed": "📰 My feed",
        "btn_add_source": "➕ Add source",
        "btn_read": "Read",
        "btn_pay_plus": "Plus · 200 Stars",
        "btn_pay_pro": "Pro · 500 Stars",
        "btn_plan_plus": "Plus",
        "btn_plan_pro": "Pro",
        "btn_plan_base": "no subscription",
        "admin_grant": "Grant subscription",
        "admin_revoke": "Revoke subscription",
        "admin_status": "Check status",
        "src_investing": "Business and market news.",
        "src_cnn": "Business and economy news.",
        "src_yahoo": "Markets, companies and finance.",
        "src_default": "A working RSS feed for business news.",
        "src_bbc": "Business news and companies from around the world.",
        "src_cnbc": "Markets, the economy, earnings and energy.",
        "src_mw": "Market and company news.",
        "src_oil": "Oil, gas and energy.",
        "src_coin": "Cryptocurrency markets.",
        "src_eia": "U.S. energy market reports and data.",
        "src_fed": "Monetary policy decisions and Federal Reserve speeches.",
        "src_abc": "Business and market news.",
        "help": """<b>Help</b>

Market News sends business stories and a short market brief.

<b>Commands</b>
/start — the top stories right now
/digest — today's digest
/today — the same as the digest
/analytics — a breakdown by topic
/settings — language and delivery
/help — this note

<b>How to read</b>
Open the digest, then a story. “Read in full” stays inside the bot.

<b>Delivery</b>
Once a day, at the hour you pick in settings. You can turn it off there.

<b>Where the news comes from</b>
ABC News Business, BBC Business, CNBC, OilPrice, CoinDesk, U.S. EIA, Federal Reserve.

This is not investment advice and not a price forecast.""",
    },
    "ar": {
        "tagline": "تحليل يومي للأسواق",
        "today_head": "أبرز أخبار اليوم:",
        "updated": "آخر تحديث: {stamp} ({tz})",
        "disclaimer": "ليس نصيحة استثمارية.",
        "source": "المصدر",
        "topic": "الموضوع",
        "loading": "أجمع العناوين الجديدة من خلاصات RSS العاملة. ستظهر أخبار اليوم هنا خلال ثوانٍ.",
        "empty": "لم تستجب مصادر الأخبار الآن. القائمة تعمل: افتح الموجز بعد دقيقة وسيحمّل البوت المواد.",
        "no_summary": "لم تأتِ في الخلاصة فقرة مستقلة. في الأسفل المصدر ومواد قريبة من الموضوع. البوت لا يخترع أرقامًا.",
        "open_later": "النص أعلاه محفوظ من خلاصة الناشر.",
        "links_ready": "",
        "full_note": "هذا نص من {source}. الأرقام والأحكام من المادة الأصلية، والبوت لا يضيف شيئًا.",
        "related": "مواد قريبة في الموضوع",
        "no_article": "هذه المادة لم تعد في الخلاصة. افتح موجزًا جديدًا.",
        "empty_cat": "لا مواد جديدة في «{cat}» بعد. اختر موضوعًا آخر أو الموجز العام.",
        "unknown": "استخدم الأزرار تحت الرسالة. ابدأ بالموجز أو افتح /help.",
        "digest_title": "موجز اليوم",
        "analytics_title": "التحليل",
        "latest_title": "آخر الأخبار",
        "cats_title": "المواضيع",
        "settings_title": "الإعدادات",
        "sources_title": "المصادر",
        "week_title": "موجز الأسبوع",
        "plus_title": "اشتراك Market News",
        "plots": "أبرز الموضوعات",
        "spread": "كيف توزعت المواد",
        "brief": "قراءة قصيرة",
        "by_topic": "حسب الموضوع",
        "analytics_blurb": "في الدفعة الأخيرة يظهر موضوع «{cat}» أكثر من غيره — {n} مواد. يمكن البدء بـ«{title}» ({source}). هنا أخبار نُشرت فقط: البوت لا يتوقع الأسعار ولا يقول ماذا تشتري أو تبيع.",
        "cats_intro": "مواضيع الأيام الأخيرة. كل مادة تُفتح داخل البوت.",
        "latest_intro": "أحدث المواد حسب وقت النشر.",
        "digest_intro": "أهم ما في اليوم. افتح أي بند ويبقى النص داخل البوت.",
        "week_intro": "اثنتا عشرة مادة من آخر سبعة أيام، من مواضيع مختلفة.",
        "sources_locked": "الناشرون وراء الموجز.",
        "sources_open": "الناشرون وراء الموجز.",
        "sources_intro": "خلاصات RSS العاملة التي يستخدمها البوت. لا توجد أزرار لمواقع خارجية هنا.",
        "sources_line": "في هذا العدد: {names}.",
        "only_one": "في هذه القائمة خبر واحد حتى الآن",
        "mail_footer": "رسالة Market News اليومية. غيّر الساعة أو اللغة في /settings.",
        "settings_lang": "لغة الواجهة: {lang}",
        "settings_push_on": "الإرسال مفعّل، الساعة {hour}:00 ({tz})",
        "settings_push_off": "الإرسال متوقف",
        "plus_active": "Plus فعّال حتى {until}",
        "plus_off": "لا يوجد اشتراك فعّال. الموجز والتحليل والنص الكامل مجانية.",
        "plus_pitch": "كل أخبار السوق في نافذة واحدة. الأساسي: 0 Stars، حتى 5 مصادر وموجز يومي. Plus: {plus_stars} Stars لمدة 30 يومًا، حتى {plus_limit} مصدرًا و5 مواقع خاصة ورسالة عند حفظ الخبر. Pro: {pro_stars} Stars، حتى {pro_limit} مصدرًا و20 موقعًا وفحص كل 5 دقائق.",
        "plus_thanks": "اشتراك {plan} فعّال حتى {until}. يبقى الموجز اليومي متاحًا.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 يومًا: مصادر أكثر ورسالة عند حفظ كل خبر جديد.",
        "plans_title": "خطط Market News",
        "plans_text": "يوجد الآن {catalog} مصدرًا عاملًا في الكتالوج.\n\nالأساسي — 0 Stars: حتى 5 مصادر وموجز يومي.\n\nPlus — 200 Stars / 30 يومًا: حتى 100 مصدر، 5 مواقع خاصة، ورسالة عند حفظ الخبر.\n\nPro — 500 Stars / 30 يومًا: حتى 500 مصدر، 20 موقعًا، وفحص كل 5 دقائق.",
        "feed_title": "موجزِي",
        "feed_intro": "فعّل المصادر ضمن عدد الخانات في خطتك. تظهر الأخبار ذات النص الكامل فقط في الموجز والتنبيهات.",
        "feed_locked": "يتطلب {plan}",
        "add_source_prompt": "أرسل عنوان موقع أو RSS يبدأ بـ https. سيتحقق البوت من الخلاصة والنص الكامل. إذا فشل البحث المعتاد، قد يُرسل عنوان الموقع وأسماء الروابط إلى مزود الذكاء الاصطناعي لاقتراح RSS. افتح الخطط أولًا في الأساسي.",
        "source_added": "أُضيف المصدر إلى موجزك: {name}.",
        "source_failed": "تعذر إنشاء موجز من هذا العنوان. أرسل عنوان https آخر.",
        "admin_title": "إدارة الاشتراكات",
        "admin_intro": "قسم خاص.\nالمنح: ID الخطة الأيام — مثال: 123456789 pro 30.\nالسحب أو الحالة: أرسل المعرف فقط.",
        "admin_grant": "منح اشتراك",
        "admin_revoke": "سحب اشتراك",
        "admin_status": "فحص الحالة",
        "admin_prompt_grant": "أرسل: ID الخطة الأيام\nمثال: 123456789 plus 30",
        "admin_prompt_user": "أرسل معرف Telegram للمستخدم.",
        "admin_bad_input": "تعذر فهم البيانات. حاول مرة أخرى.",
        "admin_not_found": "هذا المستخدم لم يبدأ البوت بعد.",
        "admin_granted": "تم: مُنحت {plan} للمستخدم {user_id} حتى {until}.",
        "admin_revoked": "تم سحب اشتراك المستخدم {user_id}.",
        "admin_status_result": "المستخدم {user_id}: {status}.",
        "admin_confirm": "تأكيد السحب",
        "admin_cancel": "إلغاء",
        "admin_confirm_question": "سحب {status} من المستخدم {user_id}؟ لا تُسترد النجوم تلقائيًا.",
        "admin_user_granted": "اشتراكك {plan} فعّال حتى {until}.",
        "admin_user_revoked": "سحب المسؤول اشتراكك. يبقى الموجز المجاني متاحًا.",
        "admin_confirm_wait": "استخدم زر التأكيد للسحب، أو إلغاء /admin.",
        "admin_expired": "انتهت صلاحية التأكيد. افتح /admin مجددًا.",
        "source_duplicate": "هذا العنوان مضاف بالفعل.",
        "subscription_status": "الحالة: {status}",
        "pay_failed": "لم تُفتح نافذة الدفع. الأخبار ما زالت متاحة من القائمة.",
        "story_empty": "خبر اليوم يظهر عندما ترد الخلاصة. افتح الموجز بعد دقيقة.",
        "opening": "أفتح النص الكامل…",
        "full_missing": "لم يفتح النص الكامل على موقع الناشر. في الأسفل ما جاء في الخلاصة.",
        "error": "لم تُفتح هذه الشاشة. اضغط /start.",
        "cat_stocks": "الأسهم",
        "cat_oil": "النفط والغاز",
        "cat_macro": "الاقتصاد الكلي",
        "cat_crypto": "العملات الرقمية",
        "cat_markets": "الأسواق",
        "btn_digest": "📅 الموجز الكامل",
        "btn_analytics": "📊 التحليل",
        "btn_latest": "📰 الأحدث",
        "btn_cats": "🗂 التصنيفات",
        "btn_story": "⭐ خبر اليوم",
        "btn_settings": "⚙️ الإعدادات",
        "btn_help": "ℹ️ مساعدة",
        "btn_full": "اقرأ كاملًا",
        "btn_next": "التالية",
        "btn_menu": "القائمة",
        "btn_back": "رجوع",
        "btn_collapse": "طي",
        "btn_push_on": "تشغيل الإرسال",
        "btn_push_off": "إيقاف الإرسال",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "تجديد Plus",
        "btn_week": "🗓 موجز الأسبوع",
        "btn_pay": "ادفع {stars} Stars",
        "btn_sources": "📚 المصادر",
        "btn_subscription": "⭐ الاشتراك",
        "btn_my_feed": "📰 موجزي",
        "btn_add_source": "➕ إضافة مصدر",
        "btn_read": "قراءة",
        "btn_pay_plus": "Plus · 200 Stars",
        "btn_pay_pro": "Pro · 500 Stars",
        "btn_plan_plus": "Plus",
        "btn_plan_pro": "Pro",
        "btn_plan_base": "لا اشتراك",
        "admin_grant": "منح اشتراك",
        "admin_revoke": "سحب اشتراك",
        "admin_status": "فحص الحالة",
        "src_investing": "أخبار الأعمال والأسواق.",
        "src_cnn": "أخبار الأعمال والاقتصاد.",
        "src_yahoo": "الأسواق والشركات والمال.",
        "src_default": "خلاصة RSS عاملة لأخبار الأعمال.",
        "src_bbc": "أخبار الأعمال والشركات من حول العالم.",
        "src_cnbc": "الأسواق والاقتصاد والنتائج والطاقة.",
        "src_mw": "أخبار الأسواق والشركات.",
        "src_oil": "النفط والغاز والطاقة.",
        "src_coin": "أسواق العملات الرقمية.",
        "src_eia": "بيانات وأخبار أسواق الطاقة الأمريكية.",
        "src_fed": "قرارات السياسة النقدية وخطابات الاحتياطي الفيدرالي.",
        "src_abc": "أخبار الأعمال والأسواق.",
        "help": """<b>مساعدة</b>

يرسل Market News أخبار الأعمال وملخصًا قصيرًا للسوق.

<b>الأوامر</b>
/start — أبرز الأخبار الآن
/digest — موجز اليوم
/today — نفس الموجز
/analytics — توزيع حسب المواضيع
/settings — اللغة والإرسال
/help — هذه الملاحظة

<b>كيف تقرأ</b>
افتح الموجز ثم الخبر. «اقرأ كاملًا» يبقى داخل البوت.

<b>الإرسال</b>
مرة في اليوم، في الساعة التي تختارها من الإعدادات. ويمكن إيقافه هناك.

<b>من أين تأتي الأخبار</b>
ABC News Business وBBC Business وCNBC وOilPrice وCoinDesk وU.S. EIA وFederal Reserve.

هذا ليس نصيحة استثمارية ولا توقعًا للأسعار.""",
    },
}

TZ_LABELS = {
    "ru": {
        "Europe/Moscow": "Москва",
        "Asia/Dubai": "Дубай",
        "Europe/London": "Лондон",
        "UTC": "UTC",
    },
    "en": {
        "Europe/Moscow": "Moscow",
        "Asia/Dubai": "Dubai",
        "Europe/London": "London",
        "UTC": "UTC",
    },
    "ar": {
        "Europe/Moscow": "موسكو",
        "Asia/Dubai": "دبي",
        "Europe/London": "لندن",
        "UTC": "UTC",
    },
}

ABOUT_RU = (
    "Market News собирает деловые новости из рабочих RSS-лент и раскладывает их "
    "по темам. Дайджест приходит раз в день, читать можно прямо в боте. "
    "Это не инвестиционный совет и не прогноз цен."
)
ABOUT_EN = (
    "Market News collects business stories from working RSS feeds and sorts them "
    "by topic. A digest arrives once a day and can be read inside the bot. "
    "This is not investment advice and not a price forecast."
)
SHORT_RU = "Ежедневный дайджест рынков: новости и короткая сводка внутри бота."
SHORT_EN = "A daily market digest: stories and a short brief inside the bot."
ABOUT_AR = (
    "يجمع Market News أخبار الأعمال من خلاصات RSS العاملة ويصنفها حسب الموضوع. "
    "يصل الموجز مرة في اليوم ويمكن قراءته داخل البوت. هذا ليس نصيحة استثمارية "
    "ولا توقعًا للأسعار."
)
SHORT_AR = "موجز يومي للأسواق: أخبار وملخص قصير داخل البوت."

COMMANDS_RU = (
    ("start", "Главные новости"),
    ("digest", "Дайджест дня"),
    ("today", "Сегодняшние новости"),
    ("analytics", "Аналитика"),
    ("settings", "Настройки"),
    ("help", "Помощь"),
)
COMMANDS_EN = (
    ("start", "Top stories"),
    ("digest", "Daily digest"),
    ("today", "Today's news"),
    ("analytics", "Analytics"),
    ("settings", "Settings"),
    ("help", "Help"),
)
COMMANDS_UK = (
    ("start", "Головні новини"),
    ("digest", "Дайджест дня"),
    ("today", "Новини сьогодні"),
    ("analytics", "Аналітика"),
    ("settings", "Налаштування"),
    ("help", "Допомога"),
)
COMMANDS_AR = (
    ("start", "أهم الأخبار"),
    ("digest", "موجز اليوم"),
    ("today", "أخبار اليوم"),
    ("analytics", "التحليل"),
    ("settings", "الإعدادات"),
    ("help", "المساعدة"),
)
COMMANDS = {
    "ru": COMMANDS_RU,
    "en": COMMANDS_EN,
    "uk": COMMANDS_UK,
    "ar": COMMANDS_AR,
}


def t(lang: str, key: str) -> str:
    table = STRINGS.get(lang) or STRINGS["ru"]
    if key in table:
        return table[key]
    if key in STRINGS["ru"]:
        return STRINGS["ru"][key]
    raise KeyError(key)


def fill(template: str, **kwargs: object) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def tz_label(lang: str, zone: str) -> str:
    table = TZ_LABELS.get(lang) or TZ_LABELS["ru"]
    return table.get(zone, zone)


def lang_label(lang: str) -> str:
    return {"ru": "Русский", "en": "English", "ar": "العربية"}.get(lang, lang)


def cat_name(lang: str, category: str) -> str:
    key = f"cat_{category}"
    if key in STRINGS["ru"]:
        return t(lang, key)
    return t(lang, "cat_markets")
