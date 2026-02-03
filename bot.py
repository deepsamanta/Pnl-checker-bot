

import time
import json
import hmac
import hashlib
import requests
import os


# ===== COINDCX API =====
COINDCX_KEY = os.getenv("COINDCX_KEY")
COINDCX_SECRET = os.getenv("COINDCX_SECRET")

# ==============================
# CONFIG
# ==============================
API_KEY = COINDCX_KEY
API_SECRET = COINDCX_SECRET

# ==============================
# CONFIG
# ==============================
BASE_URL = "https://api.coindcx.com"


PNL_TARGET = 0.3     # USDT
CHECK_INTERVAL = 10     # 5 minutes

secret_bytes = API_SECRET.encode()


# ==============================
# AUTH HELPER
# ==============================
def sign_request(body: dict):
    json_body = json.dumps(body, separators=(',', ':'))
    signature = hmac.new(
        secret_bytes,
        json_body.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": API_KEY,
        "X-AUTH-SIGNATURE": signature
    }
    return json_body, headers


# ==============================
# GET CROSS MARGIN PNL
# ==============================
def get_cross_pnl():
    body = {
        "timestamp": int(time.time() * 1000)
    }

    json_body, headers = sign_request(body)

    url = BASE_URL + "/exchange/v1/derivatives/futures/positions/cross_margin_details"
    response = requests.get(url, data=json_body, headers=headers)
    response.raise_for_status()

    return response.json()


# ==============================
# GET OPEN POSITIONS (CORRECT METHOD)
# ==============================
def get_open_positions():
    body = {
        "timestamp": int(time.time() * 1000),
        "page": "1",
        "size": "20",
        "margin_currency_short_name": ["USDT"]
    }

    json_body, headers = sign_request(body)

    url = BASE_URL + "/exchange/v1/derivatives/futures/positions"
    response = requests.post(url, data=json_body, headers=headers)
    response.raise_for_status()

    positions = response.json()

    # Filter only ACTIVE positions
    active_positions = [
        pos for pos in positions
        if float(pos.get("active_pos", 0)) != 0
    ]

    return active_positions


# ==============================
# EXIT POSITION USING POSITION ID
# ==============================
def exit_position(position_id):
    body = {
        "timestamp": int(time.time() * 1000),
        "id": position_id
    }

    json_body, headers = sign_request(body)

    url = BASE_URL + "/exchange/v1/derivatives/futures/positions/exit"
    response = requests.post(url, data=json_body, headers=headers)
    response.raise_for_status()

    return response.json()


# ==============================
# CLOSE ALL OPEN POSITIONS
# ==============================
def close_all_positions():
    positions = get_open_positions()

    if not positions:
        print("ℹ️ No active positions found.")
        return

    for pos in positions:
        position_id = pos["id"]
        pair = pos.get("pair")
        qty = pos.get("active_pos")

        print(f"🚪 Exiting {pair} | Qty: {qty} | ID: {position_id}")
        exit_position(position_id)

    print("✅ All active positions exited.")


# ==============================
# MAIN LOOP
# ==============================
def main():
    print("🚀 CoinDCX Cross PnL Guard Bot Started (ALWAYS ON)")

    while True:
        try:
            pnl_data = get_cross_pnl()
            pnl = float(pnl_data["pnl"])

            print(f"[{time.ctime()}] 💰 Current PnL: {pnl:.4f} USDT")

            if pnl >= PNL_TARGET:
                print("🎯 PnL target reached!")
                close_all_positions()

                # 🧊 Cooldown to prevent repeated exits
                print("⏳ Cooldown after exit...")
                time.sleep(30)
                continue

        except Exception as e:
            print("❌ Error:", str(e))

        time.sleep(CHECK_INTERVAL)


# ==============================
# ENTRY POINT
# ==============================
if __name__ == "__main__":
    main()
