import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

#load environment variables
load_dotenv()

#gmail credentials 
sender_email = os.getenv("GMAIL_USER")
sender_password = os.getenv("GMAIL_PASS")


#function to send
def send_email(email):

    #create email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    msg["subject"] = "Your OTP Code"

    #generate 4-digit OPT
    otp = str(random.randint(1000, 9999))

    body = f"Hello,\n\nYour OTP code is: {otp}\n\nIf you did not request this, please ignore."
    msg.attach(MIMEText(body , "plain"))

    try:
        #connect to gmail smtp
        server = smtplib.SMTP("smtp.gmail.com" , 587)
        server.starttls()
        server.login(sender_email , sender_password)

        #send email
        server.sendmail(sender_email , email , msg.as_string())
        print(f"✅ OTP email sent to {email}: {otp}")

        server.quit()

    except Exception as e:
        print("❌ Error:", e)

    return otp