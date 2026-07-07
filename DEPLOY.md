# Деплой backend калькулятора (Render / Railway)

## Самый быстрый способ — Render Blueprint (render.yaml уже в репозитории)

1. Зайти на https://dashboard.render.com/blueprints
2. **New Blueprint Instance** → выбрать репозиторий `pisyjones-max/calculator`.
   Render сам найдёт `render.yaml` и `Dockerfile` и предложит создать сервис
   `platforma-calculator` со всеми настройками (Docker runtime, health-check
   на `/health`, список нужных переменных окружения).
3. Render попросит заполнить переменные, помеченные `sync: false`
   (секреты — они не хранятся в git):
   - `TELEGRAM_BOT_TOKEN` — токен бота от @BotFather
   - `TELEGRAM_CHAT_ID` — chat_id менеджера/группы
   - `PUBLIC_BASE_URL` — на первый раз можно оставить пустым, после деплоя
     Render покажет ваш домен (`https://platforma-calculator-XXXX.onrender.com`)
     — впишите его сюда и передеплойте (Manual Deploy → Deploy latest commit)
   - `DATABASE_URL` — можно оставить пустым (тогда используется SQLite),
     заполнить понадобится только при подключении Postgres, см. ниже
4. Нажать **Apply** — Render соберёт Docker-образ и запустит сервис.
5. Проверить: открыть `https://<ваш-домен>.onrender.com/health` →
   должно быть `{"status":"ok"}`, и `/widget` — там должен отрисоваться калькулятор.

Дальше — ровно то же самое, что описано ниже (CORS, Postgres, embed-сниппет).
Разделы ниже пригодятся, если Blueprint недоступен (например, аккаунт без
доступа к Blueprints) — тогда сервис создаётся вручную через "New Web Service".

---

Backend — FastAPI-приложение с зависимостью на WeasyPrint (генерация PDF-смет),
которому нужны системные библиотеки (Pango/Cairo). Обычный "голый" Python
buildpack их не ставит, поэтому деплоим через Docker (`Dockerfile` уже в репозитории).

## Вариант 1: Render

1. **New → Web Service** → подключить репозиторий `pisyjones-max/calculator`.
2. Runtime: **Docker** (Render сам увидит `Dockerfile` в корне и предложит его).
3. Instance type: любой, для старта хватит Free/Starter.
4. Переменные окружения (Settings → Environment):
   - `TELEGRAM_BOT_TOKEN` — токен бота от @BotFather
   - `TELEGRAM_CHAT_ID` — chat_id менеджера/группы
   - `PUBLIC_BASE_URL` — будет присвоен после первого деплоя, например `https://platforma-calc.onrender.com` (или ваш кастомный домен) — впишите и передеплойте
   - `ALLOWED_ORIGINS` — сначала можно не задавать (CORS будет `*`), после подключения домена `platforma-msk.ru` — задать `https://platforma-msk.ru,https://www.platforma-msk.ru` и передеплоить
   - `DATABASE_URL` — см. раздел "База данных" ниже
5. Render сам собирает образ по `Dockerfile` и запускает `CMD` из него — ничего
   дополнительно в "Start Command" указывать не нужно.
6. После деплоя проверить: `https://<ваш-домен>/health` → `{"status":"ok"}`.

## Вариант 2: Railway

1. **New Project → Deploy from GitHub repo** → выбрать `calculator`.
2. Railway тоже автоматически находит `Dockerfile` и билдит через него.
3. Переменные окружения — те же самые, вкладка **Variables**.
4. Railway сам назначает публичный домен (или подключите кастомный в **Settings → Domains**).
5. Порт: Railway сам пробрасывает `$PORT` — `Dockerfile` уже это учитывает
   (`--port ${PORT:-8000}`), ничего менять не нужно.

## База данных: важный нюанс с SQLite

Сейчас проект использует SQLite-файл (`platforma.db`), который лежит **внутри
контейнера**. На Render/Railway диск контейнера эфемерный: при каждом
передеплое (пуш в git, ручной redeploy) файл пересоздаётся из `seed_db.py`
(товары/поставщики/цены — статика, это ок), **но все накопленные реальные
заявки (`quote_requests`) и сметы (`quotes`) при передеплое потеряются**.

Варианты:
- **Для быстрого старта** — оставить как есть. Все заявки и так дублируются
  в Telegram-уведомление менеджеру и поставщику, так что потеря БД не значит
  потерю лида — просто в самой БД не накопится история.
- **Для нормальной эксплуатации** — подключить Postgres:
  1. Render/Railway → добавить Postgres-инстанс в проект (кнопка "Add Database").
  2. Скопировать выданный `DATABASE_URL` (или "Internal Database URL") в
     переменные окружения web-сервиса.
  3. В `requirements.txt` добавить `psycopg2-binary` (не входит по умолчанию,
     т.к. не нужен для SQLite) и передеплоить.
  4. `app/database.py` уже читает `DATABASE_URL` из окружения — правок в коде
     больше не нужно.
  5. Убрать/оставить `python scripts/seed_db.py` в `CMD` — он **upsert**-ит
     товары/поставщиков по slug, повторный запуск безопасен и не трогает
     заявки/сметы.

## Проверка после деплоя

```bash
curl https://<домен>/health
curl -X POST https://<домен>/api/calculate/roofing \
  -H "Content-Type: application/json" \
  -d '{"length":10,"width":8,"angle":30,"material":"metal_tile_grand"}'
```

Должен вернуться JSON с расчётом и тремя поставщиками (`suppliers: [...]`).

## Встраивание виджета на platforma-msk.ru

Backend отдаёт готовую embed-страницу на `/widget` (без шапки сайта,
компактная, с автоподгонкой высоты). На platforma-msk.ru достаточно вставить:

```html
<iframe
  id="platforma-calc-widget"
  src="https://<домен-backend>/widget"
  style="width:100%; border:0; min-height:520px;"
  loading="lazy">
</iframe>
<script>
  // Виджет сам присылает свою реальную высоту (форма короче, чем смета
  // с тремя карточками поставщиков) — подгоняем iframe без скролла внутри.
  window.addEventListener("message", function(e) {
    if (e.data && e.data.type === "platforma-widget-resize") {
      var el = document.getElementById("platforma-calc-widget");
      if (el) el.style.height = e.data.height + "px";
    }
  });
</script>
```

Если фронтенд `platforma-msk.ru` и backend калькулятора — разные домены,
дополнительно ничего настраивать на стороне iframe не нужно: `/widget`
сам ходит в свой же backend по относительным путям (`API_BASE=""`, тот же
origin, откуда отдана страница `/widget`).

Если планируете открыть калькулятор и как отдельный сайт (например
`calc.platforma-msk.ru`), и **встраивать** его на `platforma-msk.ru` — это
один и тот же backend, просто в `ALLOWED_ORIGINS` нужно перечислить оба
домена (сам поддомен калькулятора обычно ходит с того же origin, а вот
`platforma-msk.ru`, встраивающий iframe, — CORS для него не нужен вовсе,
т.к. запросы из iframe идут на origin самого iframe, то есть на backend, а
не "поперёк" на platforma-msk.ru; ALLOWED_ORIGINS нужен только если сам JS
на platforma-msk.ru **напрямую** (не через iframe) дёргает API калькулятора).

## Рассылка поставщикам

Поставщик получает лид в Telegram напрямую, если для него в БД заполнен
`telegram_chat_id` (таблица `suppliers`). Чтобы подключить поставщика:

1. Поставщик пишет `/start` тому же боту PLATFORMA (токен из `TELEGRAM_BOT_TOKEN`).
2. Узнать его chat_id: `https://api.telegram.org/bot<TOKEN>/getUpdates` → найти
   `"chat":{"id": ...}` в последнем апдейте от этого пользователя.
3. Проставить `telegram_chat_id` в таблице `suppliers` для нужной записи
   (через прямой `UPDATE` в БД или добавив поле в `scripts/seed_db.py`).

Если `telegram_chat_id` не заполнен — ничего не ломается, заявка просто
уходит только менеджеру (как раньше).
