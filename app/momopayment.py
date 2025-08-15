from dotenv  import load_dotenv
import uuid
import base64
import requests
import os
from app.database.database import SessionLocal
from app.models.user_model import Transactions , Credits
from sqlalchemy.orm import Session
import asyncio


load_dotenv()

url = os.getenv("MOMO_COLLECTION_URL")

#generate xxid
def generate_uuid():
    return str(uuid.uuid4())

#generate a token 
def get_mtn_token():
    username = os.getenv("MOMO_USERNAME")
    password = os.getenv("MOMO_PASSWORD")

    # create the basic auth string
    mtn_credentials = f"{username}:{password}"
    base64_credentials = base64.b64encode(mtn_credentials.encode()).decode()

    headers = {
        "Ocp-Apim-Subscription-Key":  os.getenv("Ocp_Apim_Subscription_Key"),
        "Authorization": f"Basic {base64_credentials}",
        "X-Target-Environment": os.getenv("X_Target_Environment"),
        "Connection": "keep-alive"
    }


    res = requests.post(f"{url}token/" , headers=headers)

    if res.status_code == 200:
        return res.json()
    else:
        raise Exception(f"Failed to get token: { res.status_code }, {res.text}")

#request to pay
def request_to_pay(amount , msisdn , uuid):
    
    # request payment payload 
     # The payload as per MoMo API spec
    data = {
        "amount": str(amount),
        "currency": "SZL",
        "externalId": str(msisdn),
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": str(msisdn)
        },
        "payerMessage": "Transfer funds to HireAI",
        "payeeNote": "Adding Credits to HireAI"
    }

    token_data = get_mtn_token()

    #header
    headers = {
       "Authorization": f"Bearer {token_data["access_token"]}",
       "X-Reference-Id": uuid,  # same format as d6404b78-03ca-4c8c-9709-6540053da4e0
       "X-Target-Environment": os.getenv("X_Target_Environment"),  # or "production"
       "Content-Type": "application/json",
       "Ocp-Apim-Subscription-Key": os.getenv("Ocp_Apim_Subscription_Key"), 
       "keep-alive": "true"
    }

    try:
        res = requests.post(f"{url}v1_0/requesttopay" , json=data , headers=headers)
        res.raise_for_status()
        
        if 'application/json' in res.headers.get('Content-Type', '') and res.content:
            response_data = res.json()
        else:
            response_data = {"message": res.text or "Payment request sent"}

        # Return useful info to frontend
        return {
            "status_code": res.status_code,
            "reference_id": uuid,
            "response": response_data,
            "message": "Payment request is being processed"
        }

    except requests.exceptions.RequestException as e:
        return {
            "status_code": 500,
            "error": str(e),
            "message": "Failed to process payment"
        }


# check if a user has approved a transaction
def momo_status(uuid:str):
    """ Check if MoMo transaction has been approved """
    try:

       #get tokens
       token_data = get_mtn_token()
       access_token = token_data["access_token"]

       headers = {
            "Ocp-Apim-Subscription-Key": os.getenv("Ocp_Apim_Subscription_Key"),
            "Authorization": f"Bearer {access_token}",
            "X-Target-Environment": os.getenv("X_Target_Environment"),
            "Connection": "keep-alive"
        }

       res = requests.get(f"{url}v1_0/requesttopay/{uuid}" , headers=headers)

       if res.status_code == 200:
           status = res.json().get("status")
           print(f"✅ Payment Status: {status}")
           return status
           
       else:
           print(f"❌ API Error: {res.status_code} - {res.text}")
           return 0

    except Exception as e:
        print(f"⚠️ Exception occurred: {str(e)}")
        return 0

# get database
async def update_transactions_credits ():

    print("🔍 Checking pending MoMo transactions...")

    db: Session = SessionLocal()

    try:

        #Get a transaction with status = 0
        transaction = db.query(Transactions).filter(Transactions.status == 0).first()

        if transaction and transaction.reference_id:
            status =  momo_status(transaction.reference_id)

            # Map MoMo API status to your DB status
            if status == "SUCCESSFUL":
                transaction.status = 1  # e.g., 1 = Paid
                
                # 🔹 Update Credit table
                credit_record = db.query(Credits).filter(Credits.user_id == transaction.user_id).first()

                if credit_record:
                    credit_record += transaction.amount
                    print(f"💰 Credit updated: {credit_record.amount}")

            elif status == "FAILED":
                transaction.status = -1  # e.g., -1 = Failed
            elif status == "PENDING":
                print("Transaction is still pending, no update.")
                return
            
            db.commit()
            print(f"✅ Transaction {transaction.reference_id} updated to status {transaction.status}")

        else:
            print("No pending transaction")

    finally:
        db.close()


# call function update_transactions_credits periodically

async def update_transactions_credits_periodically():
    while True:
        try:
            print("🔄 Checking pending transactions and updating credits...")
            await update_transactions_credits() 
        except Exception as e:
            print(f"⚠️ Error in updating transactions: {e}")
        await asyncio.sleep(10) # wait 10 seconds before checking again


