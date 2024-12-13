import stripe
import logging
from typing import Optional, Dict

from django.http import HttpResponse
from flask import Flask

# Configuration settings
stripe.api_key = "your_stripe_api_key"
WEBHOOK_SECRET = "your_webhook_secret"

# Initialize Flask app
app = Flask(__name__)

# Stripe Client Class (for handling payments)
class StripeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        stripe.api_key = api_key

    def create_customer(self, email: str, name: Optional[str] = None, description: Optional[str] = None) -> Dict:
        """
        Create a Stripe customer.
        """
        return stripe.Customer.create(
            email=email,
            name=name,
            description=description
        )

    def create_payment_intent(self, amount: int, currency: str, customer_id: Optional[str] = None, description: Optional[str] = None) -> Dict:
        """
        Create a payment intent.
        """
        return stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=customer_id,
            description=description
        )

    # def retrieve_payment_intent(self, payment_intent_id: str) -> Dict:
    #     """
    #     Retrieve details of a payment intent.
    #     """
    #     return stripe.PaymentIntent.retrieve(payment_intent_id)
    #
    # def refund_payment(self, charge_id: str, amount: Optional[int] = None) -> Dict:
    #     """
    #     Refund a payment.
    #     """
    #     return stripe.Refund.create(
    #         charge=charge_id,
    #         amount=amount
    #     )

    def retrieve_customer(self, customer_id: str) -> Dict:
        """
        Retrieve details of a customer.
        """
        return stripe.Customer.retrieve(customer_id)

    def delete_customer(self, customer_id: str) -> Dict:
        """
        Delete a customer.
        """
        return stripe.Customer.delete(customer_id)

    def create_subscription(self, customer_id: str, price_id: str, trial_period_days: Optional[int] = None) -> Dict:
        """
        Create a subscription for a customer.
        """
        return stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            trial_period_days=trial_period_days
        )

    def retrieve_subscription(self, subscription_id: str) -> Dict:
        """
        Retrieve details of a subscription.
        """
        return stripe.Subscription.retrieve(subscription_id)

    def delete_subscription(self, subscription_id: str) -> Dict:
        """
        Cancel a subscription.
        """
        return stripe.Subscription.delete(subscription_id)

    def create_invoice(self, customer_id: str, description: Optional[str] = None) -> Dict:
        """
        Create an invoice for a customer.
        """
        return stripe.Invoice.create(
            customer=customer_id,
            description=description,
            auto_advance=True  # Automatically finalize the invoice
        )

    def retrieve_invoice(self, invoice_id: str) -> Dict:
        """
        Retrieve details of an invoice.
        """
        return stripe.Invoice.retrieve(invoice_id)



# Webhook Handler Class (for processing Stripe webhook events)
class WebhookHandler:
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def handle_webhook(self, payload, sig_header):
        """
        Handle the Stripe webhook event by verifying the signature and processing
        the event based on its type.
        """
        event = None

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
        except ValueError:
            return {"error": "Invalid payload"}, 400
        except stripe.error.SignatureVerificationError:
            return {"error": "Invalid signature"}, 400

        # Handle the event
        event_type = event.get('type')
        data_object = event['data']['object']

        if event_type == 'customer.subscription.created':
            WebhookHandler.handle_subscription_created(data_object)
        elif event_type == 'customer.subscription.deleted':
            WebhookHandler.handle_subscription_deleted(data_object)
        elif event_type == 'invoice.paid':
            WebhookHandler.handle_invoice_paid(data_object)
        elif event_type == 'invoice.updated':
            WebhookHandler.handle_invoice_updated(data_object)
        elif event_type == 'invoice.payment_succeeded':
            WebhookHandler.handle_invoice_payment_succeeded(data_object)
        elif event_type == 'payment_intent.succeeded':
            WebhookHandler.handle_payment_intent_succeeded(data_object)
        elif event_type == 'customer.created':
            WebhookHandler.handle_customer_created(data_object)

        else:
            print(f"Unhandled event type: {event_type}")

        return jsonify({'status': 'success'}), 20

    def handle_subscription_created(subscription):
        """
        Handle the customer.subscription.created event.
        """
        # print(f"Subscription created: {subscription['id']}")
        try:
            data = WebhookHandler.extract_subscription_data(subscription)

            if data is None:
                return HttpResponse(status=200)  # Exit if there was an issue with extracting the data

            # Log for debugging purposes
            logging.info(f"Processing subscription created event for {data['subscription_id']}")

            # Store or update the subscription in the database
            obj, created = Subscription.objects.update_or_create(
                stripe_subscription_id=data['subscription_id'],
                defaults={
                    'customer_id': data['customer_id']
                }
            )

            # Log the outcome
            if created:
                print(f"New subscription record created: {data['subscription_id']}")
            else:
                print(f"Subscription record updated: {data['subscription_id']}")

        except Exception as e:
            print(f"Error processing subscription created event: {str(e)}")

    def handle_subscription_deleted(subscription):
        """
        Handle the customer.subscription.deleted event.
        """
        # print(f"Subscription deleted: {subscription['id']}")
        try:
            # Extract subscription ID
            subscription_id = subscription.get('id')

            if not subscription_id:
                logging.info("No subscription ID found for deletion event.")
                return HttpResponse(status=200)

            # Log the deletion event
            print(f"Subscription deleted: {subscription_id}")

            # Here, you may want to update the subscription status or remove it from the database
            obj, created = Subscription.objects.update_or_create(
                stripe_subscription_id=subscription_id,
                defaults={
                    'status': 'deleted'
                }
            )

            if created:
                print(f"New subscription record created for deleted subscription: {subscription_id}")
            else:
                print(f"Subscription record updated to 'deleted': {subscription_id}")

        except Exception as e:
            print(f"Error processing subscription deleted event: {str(e)}")

    def handle_invoice_paid(invoice):
        """
        Handle the invoice.paid event.
        """
        # print(f"Invoice paid: {invoice['id']}")
        try:
            data = WebhookHandler.extract_invoice_data(invoice)

            if data is None:
                return HttpResponse(status=200)  # Exit if there was an issue with extracting the data

            if not data['user']:
                logging.error("User not found.")
                return HttpResponse(status=200)

            # Log for debugging
            print(f"Invoice paid event received for invoice ID: {data['invoice_id']}")

            # Store or update the invoice in the database
            obj, created = Invoice.objects.update_or_create(
                stripe_invoice_id=data['invoice_id'],
                defaults={
                    'customer_id': data['customer_id']
                }
            )

            if created:
                print(f"New invoice record created for ID: {data['invoice_id']}")
            else:
                print(f"Invoice record updated for ID: {data['invoice_id']}")

        except Exception as e:
            print(f"Error processing invoice.paid event: {str(e)}")

    def handle_invoice_updated(invoice):
        """
        Handle the invoice.updated event.
        """
        # print(f"Invoice updated: {invoice['id']}")
        try:
            # Extract necessary data from the invoice object
            data = WebhookHandler.extract_invoice_data(invoice)

            if data is None:
                return HttpResponse(status=200)  # Exit if there was an issue with extracting the data

            if not data['user']:
                logging.error("User not found.")
                return HttpResponse(status=200)

            # Log for debugging
            print(f"Processing invoice updated event for invoice ID: {data['invoice_id']}")

            # Store or update the invoice in the database
            obj, created = Invoice.objects.update_or_create(
                stripe_invoice_id=data['invoice_id'],
                defaults={
                    'customer_id': data['customer_id']
                }
            )

            if created:
                print(f"New invoice record created: {data['invoice_id']}")
            else:
                print(f"Invoice record updated: {data['invoice_id']}")

        except Exception as e:
            print(f"Error processing invoice updated event: {str(e)}")

    def handle_invoice_payment_succeeded(invoice):
        """
        Handle the invoice.payment_succeeded event.
        """
        # print(f"Invoice payment succeeded: {invoice['id']}")
        try:
            data = WebhookHandler.extract_invoice_data(invoice)

            if data is None:
                return HttpResponse(status=200)  # Exit if there was an issue with extracting the data

            if not data['user']:
                logging.error("User not found.")
                return HttpResponse(status=200)

            # Store or update the invoice in the database
            obj, created = Invoice.objects.update_or_create(
                stripe_invoice_id=data['invoice_id'],
                defaults={
                    'customer_id': data['customer_id']
                }
            )

            if created:
                print(f"Invoice payment succeeded and recorded: {data['invoice_id']}")
            else:
                print(f"Invoice record updated: {data['invoice_id']}")

        except Exception as e:
            print(f"Error processing invoice.payment_succeeded event: {str(e)}")

    def handle_payment_intent_succeeded(payment_intent):
        """
        Handle the payment_intent.succeeded event.
        """
        # print(f"PaymentIntent succeeded: {payment_intent['id']}")
        try:
            # Extract necessary data from the payment_intent object
            data = WebhookHandler.extract_payment_intent_data(payment_intent)

            if data is None:
                return HttpResponse(status=200)  # Exit if there was an issue with extracting the data

            # Log for debugging purposes
            print(f"Processing payment intent succeeded event for payment ID: {data['payment_id']}")

            # Store or update the payment intent in the database
            obj, created = PaymentIntent.objects.update_or_create(
                stripe_payment_intent_id=data['payment_id'],
                defaults={
                    'amount': data['amount'],
                    'currency': data['currency'],
                    'customer_id': data['customer_id'],
                    'status': data['status'],
                    'metadata': data['metadata']
                }
            )

            if created:
                print(f"Payment intent created: {data['payment_id']}")
            else:
                print(f"Payment intent updated: {data['payment_id']}")

        except Exception as e:
            print(f"Error processing payment intent: {str(e)}")

    def handle_customer_created(customer):
        """
        Handle the customer.created event.
        """
        try:
            data = WebhookHandler.extract_customer_data(customer)

            if data is None:
                return HttpResponse(status=200)  # Exit if there was an issue with extracting the data

            # Log for debugging purposes
            logging.info(f"Processing customer created event for {data['customer_id']}")

            # Store or update the customer in the database
            obj, created = Customer.objects.update_or_create(
                stripe_customer_id=data['customer_id'],
                defaults={
                    'email': data['email'],
                    'name': data['name'],
                    'description': data['description'],
                }
            )

            # Log the outcome
            if created:
                print(f"New customer record created: {data['customer_id']}")
            else:
                print(f"Customer record updated: {data['customer_id']}")

        except Exception as e:
            print(f"Error processing customer created event: {str(e)}")

    def extract_invoice_data(invoice, timezone=None):
        """
        Helper function to extract the necessary data from an invoice.
        """
        try:
            invoice_id = invoice.get('id')
            # customer_id = invoice.get('customer')
            # amount_paid = invoice.get('amount_paid')
            # currency = invoice.get('currency')
            # status = invoice.get('status')
            # payment_intent = invoice.get('payment_intent')
            # metadata = invoice.get('metadata', {})
            # product_id = invoice['lines']['data'][0]['plan']['product']
            # price_id = invoice['lines']['data'][0]['price']['id']
            # payment_status = invoice['status']
            customer_email = invoice.get('customer_email', None)
            user = User.objects.filter(email=customer_email).first()
            # subscription_id = invoice.get('subscription', None)
            # product_details = stripe.Product.retrieve(product_id)
            # plan_name = product_details.name
            # plan_price = float(invoice['lines']['data'][0]['amount'] / 100)
            # product_description = product_details['description']
            # next_invoice_sequence = invoice['lines']['data'][0]['price']['recurring']['interval_count'] + 1
            # interval = invoice['lines']['data'][0]['price']['recurring']['interval']
            # subscription_details = stripe.Subscription.retrieve(subscription_id)
            # subscription_status = subscription_details.status
            # created_time = subscription_details['current_period_start']
            # expires_at_time = subscription_details['current_period_end']
            # subscription_id = subscription_details['id']
            # start_date = datetime.fromtimestamp(created_time, tz=timezone.utc)
            # expires_date = datetime.fromtimestamp(expires_at_time, tz=timezone.utc)

            return {
                'invoice_id': invoice_id,
                'user': user
            }
        except Exception as e:
            print(f"Error extracting invoice data: {str(e)}")
            return None

    def extract_payment_intent_data(payment_intent):
        """
        Helper function to extract necessary data from a payment intent.
        """
        try:
            payment_id = payment_intent.get('id')
            amount = payment_intent.get('amount_received')
            currency = payment_intent.get('currency')
            customer = payment_intent.get('customer')
            status = payment_intent.get('status')
            metadata = payment_intent.get('metadata', {})

            return {
                'payment_id': payment_id,
                'amount': amount,
                'currency': currency,
                'customer_id': customer,
                'status': status,
                'metadata': metadata
            }
        except Exception as e:
            print(f"Error extracting payment intent data: {str(e)}")
            return None

    def extract_subscription_data(subscription):
        """
        Helper function to extract necessary data from a subscription.
        """
        try:
            subscription_id = subscription.get('id')
            customer_id = subscription.get('customer')
            user = User.objects.filter(stripe_customer_id=customer_id)  # change with model name
            # status = subscription.get('status')
            # plan_id = subscription['items']['data'][0]['plan']['id'] if subscription.get('items') and subscription['items']['data'] else None
            # start_date = datetime.fromtimestamp(subscription.get('current_period_start')) if subscription.get('current_period_start') else None
            # end_date = datetime.fromtimestamp(subscription.get('current_period_end')) if subscription.get('current_period_end') else None
            # metadata = subscription.get('metadata', {})
            # product_id = subscription['items']['data'][0]['price']['product']
            # product_details = stripe.Product.retrieve(product_id)
            # plan_name = product_details['name']
            # product_description = product_details['description']
            # invoice_id = subscription['latest_invoice']
            # plan_price = subscription['items']['data'][0]['price']['unit_amount']
            # subscription_details = stripe.Subscription.retrieve(subscription_id)
            # price_id = subscription_details['items']['data'][0]['price']['id']
            # interval = subscription['items']['data'][0]['plan']['interval']
            # payment_status = subscription['status']

            return {
                'subscription_id': subscription_id,
                'user': user
            }
        except Exception as e:
            print(f"Error extracting subscription data: {str(e)}")
            return None

    def extract_customer_data(customer):
        """
        Helper function to extract necessary data from a customer object.
        """
        try:
            customer_id = customer.get('id')
            email = customer.get('email')
            name = customer.get('name')
            description = customer.get('description')

            # You can add more fields here depending on what is available from the customer object

            return {
                'customer_id': customer_id,
                'email': email,
                'name': name,
                'description': description
            }
        except Exception as e:
            print(f"Error extracting customer data: {str(e)}")
            return None


    def success_true_response(message=None, data=None, count=None):
        result = dict(success=True)
        result['message'] = message or ''
        result['data'] = data or {}
        if count is not None:
            result['count'] = count
        return result

    def success_false_response(message=None, data=None):
        result = dict(success=False)
        result['message'] = message or ''
        result['data'] = data or {}

        return result


@app.route('/webhook', methods=['POST'])
def stripe_webhook(request=None):
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_handler = WebhookHandler(WEBHOOK_SECRET)
    return webhook_handler.handle_webhook(payload, sig_header)

if __name__ == "__main__":
    app.run(debug=True)