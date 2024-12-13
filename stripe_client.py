import stripe
from typing import Optional, Dict

class StripeClient:
    def __init__(self, api_key: str):
        """
        Initialize the Stripe utility with your API key.
        """
        stripe.api_key = api_key

    def create_customer(self, email: str, name: Optional[str] = None, description: Optional[str] = None) -> Dict:
        """
        Create a Stripe customer.
        """
        try:
            return stripe.Customer.create(
                email=email,
                name=name,
                description=description
            )
        except stripe.error.StripeError as e:
            print(f"Error creating customer: {e.user_message}")
            return {}

    def create_payment_intent(self, amount: int, currency: str, customer_id: Optional[str] = None,
                              description: Optional[str] = None) -> Dict:
        """
        Create a payment intent.
        """
        try:
            return stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                description=description
            )
        except stripe.error.StripeError as e:
            print(f"Error creating payment intent: {e.user_message}")
            return {}

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
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            print(f"Error retrieving customer: {e.user_message}")
            return {}

    def delete_customer(self, customer_id: str) -> Dict:
        """
        Delete a customer.
        """
        try:
            return stripe.Customer.delete(customer_id)
        except stripe.error.StripeError as e:
            print(f"Error deleting customer: {e.user_message}")
            return {}

    def create_subscription(self, customer_id: str, price_id: str, trial_period_days: Optional[int] = None) -> Dict:
        """
        Create a subscription for a customer.
        """
        try:
            return stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                trial_period_days=trial_period_days
            )
        except stripe.error.StripeError as e:
            print(f"Error creating subscription: {e.user_message}")
            return {}

    def retrieve_subscription(self, subscription_id: str) -> Dict:
        """
        Retrieve details of a subscription.
        """
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            print(f"Error retrieving subscription: {e.user_message}")
            return {}

    def cancel_subscription(self, subscription_id: str) -> Dict:
        """
        Cancel a subscription.
        """
        try:
            return stripe.Subscription.delete(subscription_id)
        except stripe.error.StripeError as e:
            print(f"Error canceling subscription: {e.user_message}")
            return {}

    def create_invoice(self, customer_id: str, description: Optional[str] = None) -> Dict:
        """
        Create an invoice for a customer.
        """
        try:
            return stripe.Invoice.create(
                customer=customer_id,
                description=description,
                auto_advance=True  # Automatically finalize the invoice
            )
        except stripe.error.StripeError as e:
            print(f"Error creating invoice: {e.user_message}")
            return {}

    def retrieve_invoice(self, invoice_id: str) -> Dict:
        """
        Retrieve details of an invoice.
        """
        try:
            return stripe.Invoice.retrieve(invoice_id)
        except stripe.error.StripeError as e:
            print(f"Error retrieving invoice: {e.user_message}")
            return {}

# Example usage
if __name__ == "__main__":
    # Replace with your Stripe API key
    stripe_api_key = "your_stripe_api_key"
    stripe_util = StripeClient(api_key=stripe_api_key)

    # Create a customer
    customer = stripe_util.create_customer(email="customer@example.com", name="John Doe")
    if customer:
        print("Customer created:", customer)

    # Create a payment intent
    if customer.get('id'):
        payment_intent = stripe_util.create_payment_intent(amount=2000, currency="usd", customer_id=customer['id'])
        if payment_intent:
            print("Payment Intent created:", payment_intent)

    # Create a subscription
    if customer.get('id'):
        subscription = stripe_util.create_subscription(customer_id=customer['id'], price_id="price_XXXXXXXXXXXXXXXX")
        if subscription:
            print("Subscription created:", subscription)

    # Create an invoice
    if customer.get('id'):
        invoice = stripe_util.create_invoice(customer_id=customer['id'], description="Test Invoice")
        if invoice:
            print("Invoice created:", invoice)
