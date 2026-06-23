# ✈️ Flight Scanner Agent

סוכן Python שסורק מחירי טיסות מישראל לעולם ושולח דוח HTML יומי בעברית למייל — פעמיים ביום.

---

## 🗂️ מבנה הפרויקט

```
flight-agent/
├── src/
│   ├── main.py           # נקודת כניסה ראשית
│   ├── flight_scanner.py # סוקרי טיסות (Kiwi, Aviasales, Google Flights)
│   └── email_builder.py  # בונה מייל HTML
├── .github/
│   └── workflows/
│       └── flight-scanner.yml  # GitHub Actions – 07:00 ו-20:00
├── requirements.txt
└── README.md
```

---

## ⚡ הגדרה ב-5 דקות

### שלב 1: Clone לגיט שלך

```bash
git clone https://github.com/<YOUR_USERNAME>/flight-agent.git
cd flight-agent
```

### שלב 2: הגדרת GitHub Secrets

עבור אל **Settings → Secrets and variables → Actions → New repository secret** והוסף:

| Secret | תיאור | חובה? |
|--------|-------|-------|
| `SMTP_USER` | כתובת Gmail ששולחת את המייל | ✅ |
| `SMTP_PASSWORD` | **App Password** של Gmail (לא הסיסמה הרגילה!) | ✅ |
| `RECIPIENT_EMAILS` | `tal.arieli@gmail.com,ker22ari@gmail.com` | ✅ |
| `KIWI_API_KEY` | API key של Kiwi.com (Tequila) — **מחיר: חינם** | 🔶 מומלץ |
| `SERPAPI_KEY` | API key של SerpAPI (Google Flights) — 100 בקשות/חודש חינם | 🔶 אופציונלי |
| `AVIASALES_TOKEN` | Travelpayouts token | 🔶 אופציונלי |

### שלב 3: יצירת Gmail App Password

1. כנס לחשבון Google → **Security**
2. הפעל **2-Step Verification** (אם לא מופעל)
3. חפש **App Passwords**
4. צור App Password → בחר "Mail" + "Windows Computer"
5. העתק את הקוד בן 16 התווים → זה ה-`SMTP_PASSWORD`

> ⚠️ **חשוב:** אל תשתמש בסיסמת Gmail הרגילה שלך — Google חסם את זה. חייב להיות App Password.

### שלב 4: API Keys (מומלץ מאוד)

#### Kiwi / Tequila API (חינם + עשיר בנתונים)
1. הירשם ב: https://tequila.kiwi.com/
2. צור API key ← הדבק ב-`KIWI_API_KEY`

#### SerpAPI – Google Flights (100 בקשות/חודש חינם)
1. הירשם ב: https://serpapi.com/
2. העתק API key ← הדבק ב-`SERPAPI_KEY`

---

## ⏰ לוח זמנים

| זמן | תיאור |
|-----|-------|
| 07:00 שעון ישראל | מייל בוקר 🌅 |
| 20:00 שעון ישראל | מייל ערב 🌙 |

> **DST note:** ה-cron מוגדר לפי UTC. שעון ישראל = UTC+2 בקיץ, UTC+3 בחורף. ה-workflow מטפל בזה אוטומטית.

---

## 🔧 הרצה מקומית לבדיקה

```bash
# צור קובץ .env
cat > .env << 'EOF'
SMTP_USER=your@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
RECIPIENT_EMAILS=tal.arieli@gmail.com,ker22ari@gmail.com
EMAIL_SESSION=morning
KIWI_API_KEY=your_kiwi_key
EOF

# התקן תלויות
pip install -r requirements.txt

# הרץ
cd src
python -c "from dotenv import load_dotenv; load_dotenv('../.env')" && python main.py
```

---

## 📧 מה יש במייל?

- 🏆 **טבלת 20 הטיסות הזולות ביותר** – יעד, מחיר, תאריך, משך, עצירות, חברה
- 🔗 **קישור ישיר** להזמנה בכל אתר
- 💡 **טיפים לזמן הזמנה** – ימים מומלצים, שעות חיפוש, עצות Wizz/Skyscanner
- 🌍 **כיסוי**: אירופה, ארה"ב, אסיה, מזרח התיכון, אפריקה
- 📅 **חלונות זמן**: שבוע, שבועיים, חודש, חודשיים, 3 חודשים קדימה

---

## 🌐 אתרי הטיסות שנסרקים

| אתר | API | שיטה |
|-----|-----|------|
| **Kiwi.com** (Skypicker) | Tequila API – חינמי | ✅ ישיר |
| **Aviasales** / Travelpayouts | Open API | ✅ ישיר |
| **Google Flights** | דרך SerpAPI | ✅ ישיר (צריך key) |
| **Skyscanner** | קישור ידני לחיפוש | 🔗 לינק בלבד |
| **Kayak** | קישור Explore | 🔗 לינק בלבד |
| **Wizz Air** | קישור ישיר | 🔗 לינק בלבד |

> Skyscanner ו-Kayak חסמו API ציבורי — המייל כולל קישורי חיפוש מוכנים.

---

## 🐛 פתרון בעיות

| בעיה | פתרון |
|------|-------|
| מייל לא מגיע | בדוק App Password, ובדוק בspam |
| "Authentication failed" | ודא שהפעלת 2FA ויצרת App Password חדש |
| 0 טיסות נמצאו | הוסף `KIWI_API_KEY` ל-Secrets |
| GitHub Action נכשלת | ראה Logs → Upload artifact |
