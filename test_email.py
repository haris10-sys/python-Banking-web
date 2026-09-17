import smtplib

EMAIL_ADDRESS = "YOUR_GMAIL@gmail.com"
EMAIL_PASSWORD = "YOUR_16_CHARACTER_APP_PASSWORD"

with smtplib.SMTP("smtp.gmail.com", 587) as server:

    server.starttls()

    server.login(
        EMAIL_ADDRESS,
        EMAIL_PASSWORD
    )

print("✅ Gmail SMTP login successful!")