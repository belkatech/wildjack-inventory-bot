import os
import json
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import anthropic

app = Flask(__name__)

# Google Sheets setup
def get_sheet_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.environ["SPREADSHEET_ID"]).worksheet("Dashboard")
    rows = sheet.get_all_records(expected_headers=['SKU', 'Item Name', 'Category', 'Quantity', 'Unit', 'Class'])
    return rows

# Format inventory data as text for Claude
def format_inventory(rows):
    lines = ["SKU | Item Name | Category | Quantity | Unit | Class"]
    for row in rows:
        lines.append(f"{row.get('SKU','')} | {row.get('Item Name','')} | {row.get('Category','')} | {row.get('Quantity','')} | {row.get('Unit','')} | {row.get('Class','')}")
    return "\n".join(lines)

# Ask Claude
def ask_claude(question, inventory_text):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are an inventory assistant for Wild Jack, a meat processing company. 
Here is the current inventory data:

{inventory_text}

Answer this question concisely and clearly: {question}"""
            }
        ]
    )
    return message.content[0].text

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    resp = MessagingResponse()
    msg = resp.message()
    try:
        rows = get_sheet_data()
        inventory_text = format_inventory(rows)
        answer = ask_claude(incoming_msg, inventory_text)
        msg.body(answer)
    except Exception as e:
        msg.body(f"Sorry, something went wrong: {str(e)}")
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
