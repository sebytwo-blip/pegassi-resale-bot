import requests
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

API_URL = "https://api.celebratix.io/shop/v1/channel-layout/87jds?eventSgid=e_rpf7t"

last_update_id = 0
alert_active = False


def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": chat_id, "text": text}
    )


def get_ticket_data():
    r = requests.get(API_URL)
    return r.json()


def extract_ticket_dict(data):
    if "ticketTypeDictionary" in data:
        return data["ticketTypeDictionary"]

    if "data" in data and "ticketTypeDictionary" in data["data"]:
        return data["data"]["ticketTypeDictionary"]

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
