import re
import os
import psycopg2
import psycopg2.extras
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from datetime import datetime
from zoneinfo import ZoneInfo

STORE_TZ = ZoneInfo("America/New_York")
PROMO_DAYS = {6, 0, 1}  # Sunday (6), Monday (0), Tuesday (1)

app = FastAPI(title="Kiosk Check-IN & Rewards API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

VISIT_MILESTONE = 10  # Every 6th visit = reward


class CheckInRequest(BaseModel):
    name: str
    phone_number: str
    referred_phone: Optional[str] = None


class RedeemRequest(BaseModel):
    phone_number: str


def get_db_connection():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    return conn


def normalize_phone(raw_phone: str) -> str:
    numbers = re.sub(r'\D', '', raw_phone)
    if len(numbers) == 11 and numbers.startswith('1'):
        numbers = numbers[1:]
    if len(numbers) != 10:
        raise HTTPException(status_code=400, detail="Phone number must be 10 digits long.")
    return numbers


@app.post('/api/checkin')
def check_in(payload: CheckInRequest):
    phone = normalize_phone(payload.phone_number)
    clean_name = payload.name.strip()
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT * FROM customers WHERE phone_number = %s", (phone,))
        existing_user = cursor.fetchone()
        referred_user = None
        if existing_user is None:
            is_new_user = True
            referrer_id = None

            if payload.referred_phone:
                referred_phone = normalize_phone(payload.referred_phone)
                if referred_phone == phone:
                    raise HTTPException(status_code=400, detail="You cannot refer yourself.")
                cursor.execute("SELECT * FROM customers WHERE phone_number = %s", (referred_phone,))
                referred_user = cursor.fetchone()
                if referred_user is None:
                    raise HTTPException(status_code=400, detail="Referred user does not exist.")
                else:
                    referrer_id = referred_user['id']
                    cursor.execute(
                        "UPDATE customers SET available_discounts = available_discounts + 1 WHERE id = %s",
                        (referrer_id,)
                    )
                    cursor.execute(
                        "INSERT INTO rewards (customer_id, reason) VALUES(%s, %s)",
                        (referrer_id, 'REFERRAL')
                    )

            cursor.execute(
                "INSERT INTO customers (name, phone_number, visits_count, referred_by) VALUES(%s, %s, %s, %s) RETURNING id",
                (clean_name, phone, 1, referrer_id)
            )
            customer_id = cursor.fetchone()["id"]
            visits_count = 1
            available_discounts = 0
        else:
            is_new_user = False
            customer_id = existing_user["id"]
            today_local = datetime.now(STORE_TZ).date()
            cursor.execute(
                "SELECT 1 FROM visits WHERE customer_id = %s AND (created_at AT TIMEZONE 'America/New_York'):: date= %s LIMIT 1",(customer_id,today_local),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(status_code = 400,
                                    detail = "You've already checked in today! Come back on your next visit to earn more points. See you soon")
            visits_count = existing_user["visits_count"] + 1
            available_discounts = existing_user["available_discounts"]
            cursor.execute(
                "UPDATE customers SET visits_count = %s WHERE id = %s",
                (visits_count, customer_id)
            )

        cursor.execute("INSERT INTO visits (customer_id) VALUES (%s)", (customer_id,))

        remainder = visits_count % VISIT_MILESTONE
        if remainder == 0:
            visits_away = 0
            available_discounts += 1
            cursor.execute(
                "UPDATE customers SET available_discounts = %s WHERE id = %s",
                (available_discounts, customer_id)
            )
            cursor.execute(
                "INSERT INTO rewards (customer_id, reason) VALUES(%s, %s)",
                (customer_id, 'VISIT')
            )
        else:
            visits_away = VISIT_MILESTONE - remainder

        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    promo = evaluate_off_peak_promo()
    return {
        "is_new_user": is_new_user,
        "name": clean_name if is_new_user else existing_user["name"],
        "visits_count": visits_count,
        "visits_away": visits_away,
        "available_discounts": available_discounts,
        "promo": promo,
        "referral_message": (
            f"Sweet! {referred_user['name']} just earned 20% off for referring you. "
            f"Refer a friend on your next visit to earn 20% off too!"
            if referred_user else None
            )
    }


def evaluate_off_peak_promo(now: Optional[datetime] = None) -> dict:
    if now is None:
        now = datetime.now(STORE_TZ)
    promo_eligible = False
    promo_reason = ""
    promo_days = [0, 1]  # Sunday (6), Monday (0), Tuesday (1)
    if now.weekday() in promo_days:
        promo_eligible = True
        promo_reason = "Special day discount"
    # elif 13 <= now.hour < 15:
    #     promo_eligible = True
    #     promo_reason = "Special hour discount"

    return {
        "promo_eligible": promo_eligible,
        "promo_reason": promo_reason,
        "promo_message": "Off-Peak Special: Show this screen at checkout for 10% off today!" if promo_eligible else None
    }


@app.post('/api/redeem')
def redeem_discount(payload: RedeemRequest):
    phone_number = normalize_phone(payload.phone_number)
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT * FROM customers WHERE phone_number = %s", (phone_number,))
        existing_user = cursor.fetchone()

        if existing_user is None:
            raise HTTPException(status_code=400, detail="Customer does not exist.")

        if existing_user["available_discounts"] <= 0:
            raise HTTPException(status_code=400, detail="No available discounts to redeem.")

        customer_id = existing_user["id"]
        cursor.execute(
            "SELECT id FROM rewards WHERE customer_id = %s AND status = 'AVAILABLE' ORDER BY id ASC LIMIT 1",
            (customer_id,)
        )
        reward_row = cursor.fetchone()
        if reward_row is None:
            raise HTTPException(status_code=400, detail="No available rewards to redeem.")

        reward_id = reward_row["id"]
        cursor.execute(
            "UPDATE rewards SET status = %s, redeemed_at = CURRENT_TIMESTAMP WHERE id = %s",
            ("REDEEMED", reward_id)
        )
        cursor.execute(
            "UPDATE customers SET available_discounts = available_discounts - 1 WHERE id = %s",
            (customer_id,)
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return {
        "name": existing_user["name"],
        "message": "Discount redeemed successfully.",
        "available_discounts": existing_user["available_discounts"] - 1
    }
