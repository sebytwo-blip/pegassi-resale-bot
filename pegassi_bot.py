import requests
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

API_URL = "https://api.celebratix.io/shop/v2/87jds/e_rpf7t"

last_update_id = 0
alert_active = False


def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": chat_id, "text": text}
    )


def get_ticket_data():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "X-Celebratix-App-Id": "widget:2.4.5",
        "X-Celebratix-Shop-Channel": "87jds"
    }

    try:
        r = requests.get(API_URL, headers=headers, timeout=10)

        if r.status_code != 200:
            print("API returned status:", r.status_code)
            return None

        if "application/json" not in r.headers.get("Content-Type", ""):
            print("Received non-JSON response (likely Cloudflare).")
            return None

        return r.json()

    except Exception as e:
        print("API request failed:", e)
        return None


def extract_ticket_dict(data):
    if not data:
        print("No data received from API.")
        return None
    # Direct structure
    if "ticketTypeDictionary" in data:
        return data["ticketTypeDictionary"]

    # Nested inside "data"
    if "data" in data:
        inner = data["data"]

        # Sometimes dictionary is directly inside
        if "ticketTypeDictionary" in inner:
            return inner["ticketTypeDictionary"]

        # Sometimes tickets are inside list[0]
        if "list" in inner and len(inner["list"]) > 0:
            first_event = inner["list"][0]
            if "ticketTypeDictionary" in first_event:
                return first_event["ticketTypeDictionary"]

    print("Ticket dictionary not found. Full data keys:", list(data.keys()))
    return None


def build_status_message(ticket_dict):
    msg = "📊 Pegassi Resale Status\n\n"

    for ticket in ticket_dict.values():
        msg += (
            f"{ticket['name']}\n"
            f"Resale tickets: {ticket.get('ticketsOfferedInResale', 0)}\n"
            f"Normal available: {ticket.get('ticketsAvailable', 0)}\n"
            f"Status: {ticket.get('status', 'Unknown')}\n\n"
        )

    msg += "\n🎟 Event link:\nhttps://shop.celebratix.io/?c=87jds\n"
    return msg


def check_resale(ticket_dict):
    global alert_active

    for ticket in ticket_dict.values():
        resale = ticket.get("ticketsOfferedInResale", 0)

        if resale > 0 and not alert_active:
            send_message(
                CHAT_ID,
                f"🚨 RESALE LIVE 🚨\n\n"
                f"{ticket['name']}\n"
                f"Available resale tickets: {resale}\n\n"
                f"🎟 Buy now:\n"
                f"https://shop.celebratix.io/?c=87jds"
            )
            alert_active = True

        if resale == 0:
            alert_active = False


print("Bot running...")

while True:
    try:
        # ---- CHECK RESALE ----
        data = get_ticket_data()
        ticket_dict = extract_ticket_dict(data)

        if ticket_dict:
            check_resale(ticket_dict)

        # ---- CHECK TELEGRAM COMMANDS (LONG POLLING) ----
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": last_update_id + 1, "timeout": 30}
        ).json()

        for result in response.get("result", []):
            last_update_id = result["update_id"]

            message = result.get("message")
            if not message:
                continue

            text = message.get("text")
            chat_id = message["chat"]["id"]

            print("Received:", text)

            if text and text.startswith("/status"):
                if ticket_dict:
                    status_msg = build_status_message(ticket_dict)
                    send_message(chat_id, status_msg)
                else:
                    send_message(chat_id, "⚠️ API temporarily unavailable. Please try again in a minute.")

        time.sleep(15)

    except Exception as e:
        print("Error:", e)
        time.sleep(15)
