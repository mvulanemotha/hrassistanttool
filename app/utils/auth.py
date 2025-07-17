from datetime import datetime , timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

#load environment variables
load_dotenv()

# secreat key to sign JWTS (keep this safe!)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict , expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode , SECRET_KEY , algorithm=ALGORITHM)
    
    return encoded_jwt