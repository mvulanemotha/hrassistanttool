from fastapi import HTTPException
import stripe 
import os
from dotenv import load_dotenv

load_dotenv()
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET_KEY

#create an intenet
def create_payment_intent(amount: int):
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="zar",
            payment_method_types=['card']
        )
        return {"clientSecret": intent.client_secret}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))