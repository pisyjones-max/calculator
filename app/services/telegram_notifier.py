"""
Уведомление менеджера в Telegram о новой заявке с калькулятора.

Настройка (переменные окружения):
  TELEGRAM_BOT_TOKEN   — токен бота (получить у @BotFather)
  TELEGRAM_CHAT_ID     — chat_id менеджера/группы, куда слать заявки
  PUBLIC_BASE_URL      — публичный домен backend (например https://platforma-msk.ru),
                          нужен только чтобы вставить в сообщение прямую ссылку на PDF.
                          Если не задан — ссылка не прикладывается.

Если TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID не заданы — уведомление просто не
отправляется (тихо, с логом в консоль), заявка всё равно сохраняется в БД.
Так намеренно: разработчик может гонять калькулятор локально без бота,
а сама заявка при этом не теряется.
"""
import os
import httpx

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

CALC_TYPE_NAMES = {
    "roofing": "Кровля",
    "facade": "Фасад",
    "insulation": "Утепление",
}


SOURCE_LABELS = {
    "widget": "виджет (встроен на стороннем сайте)",
    "standalone": "отдельный сайт калькулятора",
}


def _send(chat_id: str, text: str) -> bool:
    """Низкоуровневый хелпер отправки сообщения через Bot API — общий для менеджера и поставщиков."""
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            print(f"[telegram_notifier] Telegram API вернул {resp.status_code}: {resp.text}")
            return False
        return True
    except httpx.HTTPError as e:
        print(f"[telegram_notifier] Не удалось отправить уведомление: {e}")
        return False


def notify_new_lead(
    quote_number: str,
    quote_id: int,
    calc_type: str,
    total: float,
    supplier_name: str,
    client_name: str,
    client_phone: str,
    client_email: str | None = None,
    source: str | None = None,
    page_url: str | None = None,
) -> bool:
    """
    Отправляет сообщение менеджеру в Telegram. Возвращает True, если
    отправлено успешно, False — если бот не настроен или запрос не удался
    (в обоих случаях исключение НЕ пробрасывается наверх — заявка не
    должна теряться из-за проблем с уведомлением).
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[telegram_notifier] Бот не настроен (нет TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID) — "
              f"заявка {quote_number} сохранена в БД, но уведомление НЕ отправлено.")
        return False

    calc_label = CALC_TYPE_NAMES.get(calc_type, calc_type)
    total_fmt = f"{round(total):,}".replace(",", "\u00a0")

    lines = [
        f"🔔 <b>Новая заявка с калькулятора</b>",
        f"",
        f"№ {quote_number} · {calc_label}",
        f"Сумма: <b>{total_fmt} ₽</b>",
        f"Поставщик: {supplier_name}",
        f"",
        f"👤 {client_name}",
        f"📞 {client_phone}",
    ]
    if client_email:
        lines.append(f"✉️ {client_email}")
    # Источник лида — помогает понять, откуда реально приходят люди:
    # с самого platforma-msk.ru, или с виджета, встроенного на чужом сайте
    # (и на какой именно странице — по page_url).
    if source:
        lines.append(f"")
        lines.append(f"🌐 Источник: {SOURCE_LABELS.get(source, source)}")
    if page_url:
        lines.append(f"🔗 Страница: {page_url}")
    if PUBLIC_BASE_URL:
        lines.append(f"")
        lines.append(f"📄 PDF: {PUBLIC_BASE_URL}/api/quotes/{quote_id}/pdf")

    return _send(TELEGRAM_CHAT_ID, "\n".join(lines))


def notify_supplier_new_lead(
    supplier_chat_id: str | None,
    quote_number: str,
    calc_type: str,
    total: float,
    client_name: str,
    client_phone: str,
) -> bool:
    """
    Рассылка лида напрямую поставщику через того же бота PLATFORMA (не
    отдельный бот на стороне поставщика — предполагается, что поставщик
    просто добавлен как получатель существующего бота: получил ссылку
    вида t.me/<bot_username>, написал /start, узнал свой chat_id и сообщил
    его нам — этот chat_id сохраняется в Supplier.telegram_chat_id).

    Если для поставщика chat_id не настроен — тихо ничего не делаем,
    возвращаем False; заявка при этом всё равно доходит до менеджера
    через notify_new_lead.
    """
    if not TELEGRAM_BOT_TOKEN:
        return False
    if not supplier_chat_id:
        return False

    calc_label = CALC_TYPE_NAMES.get(calc_type, calc_type)
    total_fmt = f"{round(total):,}".replace(",", "\u00a0")

    lines = [
        f"🔔 <b>Новая заявка от клиента PLATFORMA</b>",
        f"",
        f"№ {quote_number} · {calc_label}",
        f"Сумма сметы: <b>{total_fmt} ₽</b>",
        f"",
        f"👤 {client_name}",
        f"📞 {client_phone}",
        f"",
        f"Свяжитесь с клиентом напрямую — он выбрал вас как поставщика.",
    ]
    return _send(supplier_chat_id, "\n".join(lines))
