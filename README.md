# Angels Brows Shaping — Check-In Kiosk

A lightweight customer check-in and rewards system built for in-store use. Customers enter their name and phone number to check in, track visits, earn milestone discounts, refer friends, and redeem rewards — all from a simple browser-based kiosk.

---

## Features

- **Customer check-in** via name and phone number
- **Visit tracking** — every 6th visit earns a reward discount
- **Referral rewards** — existing customers earn a discount when a new customer uses their phone number at sign-up
- **Off-peak promos** — automatic 20% discount shown on Sundays, Mondays, Tuesdays, or between 1–3 PM (ET)
- **Discount redemption** — staff can redeem an available discount directly from the check-in confirmation modal

---

## Tech Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Frontend | HTML, CSS, Vanilla JavaScript     |
| Backend  | Python, FastAPI                   |
| Database | PostgreSQL (Supabase)             |
| Hosting  | Render (API) + Netlify (Frontend) |

---

## Project Structure

```
checkin_kiosk/
├── main.py              # FastAPI backend — all routes and business logic
├── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html       # Kiosk UI
│   └── app.js           # Fetch calls to the API, modal logic
└── db/
    └── schema.sql       # PostgreSQL table definitions
```

---

## Database Schema

**`customers`** — one row per unique phone number
| Column               | Type      | Notes                          |
|----------------------|-----------|--------------------------------|
| id                   | SERIAL PK |                                |
| name                 | TEXT      |                                |
| phone_number         | TEXT      | Unique, stored as 10 digits    |
| visits_count         | INTEGER   | Increments on every check-in   |
| available_discounts  | INTEGER   | Earned via milestones/referrals|
| referred_by          | INTEGER   | FK → customers(id)             |
| created_at           | TIMESTAMP |                                |

**`visits`** — log of every check-in event
| Column      | Type      |
|-------------|-----------|
| id          | SERIAL PK |
| customer_id | INTEGER FK|
| created_at  | TIMESTAMP |

**`rewards`** — individual discount records
| Column      | Type                        | Notes                        |
|-------------|-----------------------------|------------------------------|
| id          | SERIAL PK                   |                              |
| customer_id | INTEGER FK                  |                              |
| reason      | TEXT                        | `VISIT` or `REFERRAL`        |
| status      | TEXT                        | `AVAILABLE` or `REDEEMED`    |
| created_at  | TIMESTAMP                   |                              |
| redeemed_at | TIMESTAMP                   | Set when status → `REDEEMED` |

---

## API Endpoints

### `POST /api/checkin`
Check in a customer. Creates the customer if they don't exist yet.

**Request body:**
```json
{
  "name": "Maya Patel",
  "phone_number": "7035550199",
  "referred_phone": "7035550100"
}
```

**Response:**
```json
{
  "is_new_user": true,
  "name": "Maya Patel",
  "visits_count": 1,
  "visits_away": 5,
  "available_discounts": 0,
  "promo": {
    "promo_eligible": false,
    "promo_reason": "",
    "promo_message": null
  }
}
```

---

### `POST /api/redeem`
Redeem one available discount for a customer.

**Request body:**
```json
{
  "phone_number": "7035550199"
}
```

**Response:**
```json
{
  "name": "Maya Patel",
  "message": "Discount redeemed successfully.",
  "available_discounts": 0
}
```

---

## Rewards Logic

| Trigger                        | Reward                              |
|-------------------------------|-------------------------------------|
| Every 6th visit                | +1 discount added to the account    |
| New customer uses referral code| Referrer gets +1 discount           |
| Sunday, Monday, or Tuesday     | Instant 20% off shown at check-in   |
| 1:00 PM – 2:59 PM (ET)        | Instant 20% off shown at check-in   |

Promo discounts are shown as a message on-screen and do not deduct from `available_discounts`.

---

## Local Development

### Prerequisites
- Python 3.11+
- A PostgreSQL database (local or Supabase)

### Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd checkin_kiosk

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set the database URL
export DATABASE_URL="postgresql://user:password@host:5432/dbname"

# 5. Run the API
uvicorn main:app --reload
```

Then open `frontend/index.html` directly in a browser, or serve it with any static file server.

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

---

## Deployment

### Database — Supabase (free)
1. Create a project at [supabase.com](https://supabase.com)
2. Open the **SQL Editor** and run the contents of `db/schema.sql`
3. Copy the connection URI from **Settings → Database → URI**

### Backend — Render (free tier)
1. Connect your GitHub repo at [render.com](https://render.com) → New Web Service
2. Set **Build command:** `pip install -r requirements.txt`
3. Set **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variable: `DATABASE_URL` = your Supabase URI
5. After deploy, copy your Render URL (e.g. `https://your-app.onrender.com`)

### Frontend — Netlify (free)
1. Update `API_BASE` in `frontend/app.js` to your Render URL
2. Go to [netlify.com](https://netlify.com) → Deploy manually → drag and drop the `frontend/` folder
