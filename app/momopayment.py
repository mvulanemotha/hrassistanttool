from dotenv  import load_dotenv
import uuid
import base64
import requests
import os

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

