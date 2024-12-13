# app.py
from flask import Flask, request
from stripe_client import StripeClient
from webhook_handler import WebhookHandler

app = Flask(__name__)

STRIPE_API_KEY = "your_stripe_api_key"
WEBHOOK_SECRET = "your_webhook_secret"

# Initialize Stripe Client and Webhook Handler
stripe_client = StripeClient(STRIPE_API_KEY)
webhook_handler = WebhookHandler(WEBHOOK_SECRET, stripe_client)

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    return webhook_handler.handle_webhook(payload, sig_header)

if __name__ == '__main__':
    app.run(debug=True)
