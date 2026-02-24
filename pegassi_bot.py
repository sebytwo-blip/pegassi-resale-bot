import requests
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

API_URL = "https://api.celebratix.io/shop/v1/events/e_rpf7t?includeTicketTypes=true"

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
        "Accept": "application/json"
    }

    r = requests.get(API_URL, headers=headers)

    try:
        return r.json()
    except Exception as e:
        print("Failed to parse JSON:", e)
        print("Raw response:", r.text)
        return {}


def extract_ticket_dict(data):
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

    return msg


def check_resale(ticket_dict):
    global alert_active

    for ticket in ticket_dict.values():
        resale = ticket.get("ticketsOfferedInResale", 0)

        if resale > 0 and not alert_active:
            send_message(
                CHAT_ID,
                f"🚨 RESALE LIVE 🚨\n\n{ticket['name']}\nAvailable resale tickets: {resale}"
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
                    send_message(chat_id, "⚠️ Could not fetch ticket data.")

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
