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


#function to sending email to processed cv

def send_cv_email(email):
    # Create email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    msg["Subject"] = "Your CV has been processed"

    body = (
        f"Hello,\n\n"
        f"Your CV has been successfully processed.\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"Thank you,\nHireAI Team"
    )
    msg.attach(MIMEText(body, "plain"))

    try:
        # Connect to Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send email
        server.sendmail(sender_email,email, msg.as_string())
        print(f"✅ Email sent to {email}")

        server.quit()

    except Exception as e:
        print("❌ Error sending email:", e)