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


def notify_new_lead(
    quote_number: str,
    quote_id: int,
    calc_type: str,
    total: float,
    supplier_name: str,
    client_name: str,
    client_phone: str,
    client_email: str | None = None,
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
    if PUBLIC_BASE_URL:
        lines.append(f"")
        lines.append(f"📄 PDF: {PUBLIC_BASE_URL}/api/quotes/{quote_id}/pdf")

    text = "\n".join(lines)

    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            print(f"[telegram_notifier] Telegram API вернул {resp.status_code}: {resp.text}")
            return False
        return True
    except httpx.HTTPError as e:
        print(f"[telegram_notifier] Не удалось отправить уведомление: {e}")
        return False
