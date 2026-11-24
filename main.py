import re
import sqlite3
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from datetime import datetime
from zoneinfo import ZoneInfo

STORE_TZ = ZoneInfo("America/New_York")
PROMO_DAYS = {6, 0, 1}  # Sunday (6), Monday (0), Tuesday (1)

app = FastAPI(title = "Kiosk Check-IN & Rewards API ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "null",  # file:// protocol (opening HTML directly in browser)
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
DB_PATH = Path(__file__).parent / "db" / "kiosk.db"
VISIT_MILESTONE = 6  # Every 5th visit = 15% off

class CheckInRequest(BaseModel):
    name: str
    phone_number: str
    referred_phone : Optional[str] = None

class RedeemRequest(BaseModel):
    phone_number: str 
    
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("Pragma foreign_keys = ON;")  # Enable foreign key support
    return conn

def normalize_phone(raw_phone: str) -> str:
    """
    TODO 1: Strip all non-digit characters using regex (re.sub).
    Hint: If someone enters a 11-digit US number starting with '1' (like '17035551234'),
    slice off the leading '1' so all numbers are stored as clean 10-digit strings.
    Raise HTTPException(status_code=400) if length != 10.
    """
    # Strip all non-digit numbers
    numbers = re.sub(r'\D','', raw_phone)
    # Check if the number is 11 digits and starts with '1'
    
    if len(numbers) == 11 and numbers.startswith('1'):
        numbers = numbers[1:] # Remove the leading '1'
    
    if len(numbers)!= 10:
        raise HTTPException(status_code=400, detail="Phone number must be 10 digits long.")

    return numbers

@app.post('/api/checkin')
def check_in(payload:CheckInRequest):
    phone = normalize_phone(payload.phone_number)
    clean_name = payload.name.strip()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # TODO 2: Query `customers` by `phone_number` using a parameterized query (?,).
        existing_user = cursor.execute(
            "SELECT * FROM customers WHERE phone_number = ?",(phone,)
        ).fetchone()
        
        if existing_user is None:
            is_new_user = True
            referrer_id = None
        
            # Handle referral if provided
            if payload.referred_phone and payload.referred_phone is not None:
                
                referred_phone = normalize_phone(payload.referred_phone)
                if referred_phone == phone:
                    raise HTTPException(status_code=400, detail="You cannot refer yourself.")
                reffered_user =cursor.execute(
                    "SELECT * FROM customers WHERE phone_number = ?", (referred_phone,)
                ).fetchone()
                if reffered_user == None:
                    raise HTTPException(status_code=400, detail="Referred user does not exist.")
                
                else:
                    referrer_id = reffered_user['id']
                    cursor.execute(
                        "UPDATE customers SET available_discounts = available_discounts + 1 WHERE id = ?", (referrer_id,)
                    )
                    cursor.execute(
                        "INSERT INTO rewards (customer_id, reason) VALUES(?,?)", (referrer_id, 'REFERRAL')
                    )
                    
            
            # Insert new customer into the database
            cursor.execute(
                "INSERT INTO customers (name,phone_number, visits_count,referred_by) VALUES(?,?,?,?)",(clean_name, phone, 1, referrer_id)
            )
         
            customer_id = cursor.lastrowid
            visits_count = 1
            available_discounts = 0
        else:
            is_new_user = False
            customer_id = existing_user["id"]
            visits_count = existing_user["visits_count"] + 1
            available_discounts = existing_user["available_discounts"]

            # TODO 5: Update `visits_count` in `customers` for `customer_id`.
            cursor.execute(
                "UPDATE customers SET visits_count = ? WHERE id = ?" , (visits_count, customer_id)
            )
                

        # TODO 6: Insert a check-in timestamp record into `visits` for `customer_id`.
        cursor.execute(
            "INSERT INTO visits (customer_id) VALUES (?)", (customer_id,) 
        )

        # TODO 7: Reward Milestone Math (Every 5th visit unlocks 20% off!)
        # - Compute `remainder = visits_count % VISIT_MILESTONE`
        remainder = visits_count % VISIT_MILESTONE
        # - If remainder == 0:
        if remainder == 0:
            visits_away = 0
            available_discounts += 1
            cursor.execute(
                "UPDATE customers SET available_discounts = ? WHERE id = ?", (available_discounts, customer_id)
            )
            cursor.execute(
                "INSERT INTO rewards (customer_id, reason) VALUES(?,?)", (customer_id, 'VISIT')
            )
        else:
            visits_away = VISIT_MILESTONE - remainder
        conn.commit()
    promo = evaluate_off_peak_promo()
    return {
        "is_new_user": is_new_user,
        "name": clean_name if is_new_user else existing_user["name"],
        "visits_count": visits_count,
        "visits_away": visits_away,
        "available_discounts": available_discounts,
        "promo":promo
    }
            
def evaluate_off_peak_promo(now: Optional[datetime] = None) -> dict:
    """
    TODO 8: Determine if the current check-in qualifies for an instant off-peak discount.
    - If `now` is None, get the current time in STORE_TZ: datetime.now(STORE_TZ)
      (Accepting an optional `now` parameter makes unit testing easy!)
    - Check Condition A: Is `now.weekday()` in PROMO_DAYS? (Sun, Mon, Tue)
    - Check Condition B: Is `13 <= now.hour < 15`? (1:00 PM - 2:59 PM)
    - Return a dictionary:
      {
          "promo_eligible": True or False,
          "promo_reason": "SUN_TUE_SPECIAL" | "HAPPY_HOUR_1_3PM" | None,
          "promo_message": "e.g. Off-Peak Special: Show this screen at checkout for 20% off today!" or None
      }
    """
    if now is None:
        now = datetime.now(STORE_TZ)
    promo_eligible = False
    promo_reason = ""
    promo_days = [6,0,1] # Sunday (6), Monday (0), Tuesday (1)
    if now.weekday() in promo_days:
        promo_eligible = True
        promo_reason = "Special day discount"
    
    elif 13<= now.hour < 15:
        promo_eligible = True
        promo_reason = "Special hour discount"
    
    return {
        "promo_eligible": promo_eligible,
        "promo_reason": promo_reason,
        "promo_message": "Off-Peak Special: Show this screen at checkout for 20% off today!" if promo_eligible else None
    }
    
@app.post('/api/redeem')  
def redeem_discount(payload: RedeemRequest):
    phone_number = payload.phone_number
    phone_number = normalize_phone(payload.phone_number)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        existing_user = cursor.execute(
            "SELECT * FROM customers WHERE phone_number = ?",(phone_number,)
        ).fetchone()
        
        if existing_user is not None:
            if existing_user["available_discounts"]<=0:
                raise HTTPException(status_code = 400, detail="No available discounts to redeem.")
            customer_id = existing_user["id"]
            reward_row = cursor.execute(
                "SELECT id FROM rewards WHERE customer_id = ? AND status = 'AVAILABLE' ORDER BY id ASC LIMIT 1", (customer_id,),
            ).fetchone()
            if reward_row is None:
                raise HTTPException(status_code=400, detail="No available rewards to redeem.")
            reward_id = reward_row["id"]
            cursor.execute(
                            "UPDATE rewards SET status = ?, redeemed_at = CURRENT_TIMESTAMP  WHERE id = ?",("REDEEMED",reward_id),
                        )
        if existing_user is None:
            raise HTTPException(status_code=400, detail="Customer does not exist.")
        
        cursor.execute(
            "UPDATE customers SET available_discounts = available_discounts - 1 WHERE id = ?", (customer_id,),
        )
        conn.commit()
        return{
            "name": existing_user["name"],
            "message": "Discount redeemed successfully.",
            "available_discounts": existing_user["available_discounts"] - 1
        }
        
        
    
    
        
            
        
            
            
            
        
    
            
            
                
                
                
                
                
    
    
    
    