# 💰 Iran-Gold-Currency-Bot

[فارسی](#فارسی) · [English](#english)

A Persian Telegram bot for Iran free-market currency, gold, and coin prices.

Built with **python-telegram-bot** and the **Oanor Iran Rial Market API**.

Author: [iArvin0](https://github.com/iArvin0)

---

# فارسی

## معرفی

این بات قیمت ارزهای بازار آزاد، طلا و سکه را به **تومان** نمایش می‌دهد.

کاربر لازم نیست دستور خاصی بنویسد. نمونه:

```text
یورو
۱۰ یورو
یک یورو
10 euro
EUR
25 USD
دلار کانادا
۱۰ گرم طلا
طلای ۲۴ عیار
سکه امامی
۲ نیم سکه
```

اگر تعداد نوشته نشود، بات قیمت **یک واحد** را نمایش می‌دهد.

## اطلاعات خروجی

در صورت ارائه توسط API:

- قیمت فعلی
- ارزش کل مقدار واردشده
- بالاترین قیمت روز
- پایین‌ترین قیمت روز
- قیمت بازشدن روز
- تغییر روزانه
- درصد تغییر
- زمان/تاریخ آخرین بروزرسانی

> داده `high/low` منبع، OHLC روزانه است و لزوماً یک پنجره rolling دقیق ۲۴ ساعته نیست.

## ارزهای پشتیبانی‌شده

- USD — دلار آمریکا
- EUR — یورو
- GBP — پوند انگلیس
- AED — درهم امارات
- TRY — لیر ترکیه
- CAD — دلار کانادا
- AUD — دلار استرالیا
- CHF — فرانک سوئیس
- CNY — یوان چین
- RUB — روبل روسیه
- IQD — دینار عراق
- SAR — ریال عربستان
- JPY — ین ژاپن

## طلا

- طلای ۱۸ عیار
- طلای ۲۴ عیار
- مثقال طلا
- اونس جهانی طلا

اگر فقط بنویسید:

```text
طلا
```

منظور بات **یک گرم طلای ۱۸ عیار** است.

## سکه

- سکه امامی
- سکه بهار آزادی
- نیم سکه
- ربع سکه
- سکه گرمی

## منبع داده

پروژه از **Iran Rial Market API** در Oanor استفاده می‌کند:

https://www.oanor.com/api/irr-api

این API نرخ بازار آزاد ایران را برای ارز، طلا و سکه ارائه می‌کند و پلن رایگان دارد. سهمیه و
قیمت‌گذاری ممکن است در آینده تغییر کند؛ صفحه رسمی API را بررسی کنید.

Endpointهای استفاده‌شده:

```text
GET /v1/currencies
GET /v1/gold
GET /v1/price
GET /v1/symbols
```

برای کاهش مصرف سهمیه، پاسخ‌های بازار برای مدت کوتاهی در RAM cache می‌شوند. هیچ SQL یا دیتابیسی
استفاده نمی‌شود.

## دریافت API Key

1. در Oanor حساب بسازید.
2. Iran Rial Market API را باز کنید.
3. پلن موردنظر را فعال کنید.
4. یک API Key بسازید.
5. Key را فقط داخل `.env` قرار دهید.

کلید از طریق header زیر ارسال می‌شود:

```text
x-oanor-key
```

## نصب در Windows

```powershell
git clone https://github.com/iArvin0/Iran-Gold-Currency-Bot.git
cd Iran-Gold-Currency-Bot

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
python -m pip install -r requirements.txt
```

فایل env:

```powershell
Copy-Item .env.example .env
```

داخل `.env`:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
OANOR_API_KEY=YOUR_OANOR_API_KEY
```

اجرا:

```powershell
python run.py
```

## Linux / VPS

```bash
git clone https://github.com/iArvin0/Iran-Gold-Currency-Bot.git
cd Iran-Gold-Currency-Bot

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -r requirements.txt

cp .env.example .env
nano .env

python run.py
```

## Docker

```bash
cp .env.example .env
```

توکن تلگرام و API Key را داخل `.env` قرار دهید:

```bash
docker compose up -d --build
```

لاگ‌ها:

```bash
docker compose logs -f
```

توقف:

```bash
docker compose down
```

## متغیرهای محیطی

| متغیر | پیش‌فرض | توضیح |
|---|---:|---|
| `BOT_TOKEN` | اجباری | توکن BotFather |
| `OANOR_API_KEY` | اجباری | کلید Iran Rial Market API |
| `OANOR_BASE_URL` | `https://api.oanor.com/irr-api` | آدرس پایه API |
| `CACHE_TTL_SECONDS` | `60` | مدت cache نرخ‌ها در RAM |
| `SYMBOLS_CACHE_TTL_SECONDS` | `21600` | cache لیست نمادها |
| `HTTP_TIMEOUT_SECONDS` | `15` | timeout درخواست API |
| `LOG_DIR` | `logs` | پوشه لاگ |
| `LOG_LEVEL` | `INFO` | سطح لاگ |

## دستورات بات

```text
/start
/help
```

## تست پروژه

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest -q
```

## ساختار پروژه

```text
Iran-Gold-Currency-Bot/
├── .github/
│   └── workflows/
│       └── ci.yml
├── app/
│   ├── __init__.py
│   ├── catalog.py
│   ├── config.py
│   ├── errors.py
│   ├── formatter.py
│   ├── handlers.py
│   ├── logging_config.py
│   ├── main.py
│   ├── market_api.py
│   └── parser.py
├── tests/
│   ├── test_formatter.py
│   ├── test_market_api.py
│   └── test_parser.py
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── run.py
└── SECURITY.md
```

## نکات امنیتی

فایل `.env` را روی GitHub قرار ندهید.

اگر Bot Token یا Oanor API Key در اسکرین‌شات، لاگ یا commit لو رفت، آن را فوراً باطل و دوباره
ایجاد کنید.

## لایسنس

MIT License — © 2026 iArvin0

---

# English

## Overview

A Persian Telegram bot that returns Iran free-market prices in **Toman** for currencies, gold, and
gold coins.

Users can type natural queries such as:

```text
یورو
۱۰ یورو
one euro
10 EUR
25 USD
دلار کانادا
۱۰ گرم طلا
سکه امامی
```

If no amount is provided, the bot assumes one unit.

## Features

- Persian text interface
- Persian and English asset names
- ISO currency codes
- Persian and Arabic digits
- Simple Persian/English number words
- Currency conversion by amount
- Gold quantity calculation
- Coin prices
- Current price
- Daily high / low / open when available
- Daily absolute and percentage change when available
- Last update timestamp when available
- Toman-only display
- In-memory TTL cache
- No SQL/database
- `/start` and `/help`
- Rotating logs
- Secret redaction
- Docker / Docker Compose
- GitHub Actions
- Ruff + pytest

## Data source

The project uses the Oanor **Iran Rial Market API**:

https://www.oanor.com/api/irr-api

The API exposes Iran free-market (bazaar) currency rates plus Iranian gold and coin market data.
Its pricing and free-tier quotas can change, so check the provider page for current limits.

The API documentation describes latest open/high/low/close and daily change. These are daily OHLC
figures; they should not be described as a guaranteed rolling 24-hour window.

## Setup

```bash
git clone https://github.com/iArvin0/Iran-Gold-Currency-Bot.git
cd Iran-Gold-Currency-Bot

python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Configure:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
OANOR_API_KEY=YOUR_OANOR_API_KEY
```

Run:

```bash
python run.py
```

## Docker

```bash
docker compose up -d --build
```

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest -q
```

## Security

Never commit `.env`, bot tokens, or API keys.

## License

MIT License — © 2026 iArvin0
