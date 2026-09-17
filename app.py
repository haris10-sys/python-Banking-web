from flask import(
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    make_response,
    send_file
)
import json
import csv
import io
import smtplib
import base64

from email.message import EmailMessage

from datetime import datetime, date


EMAIL_ADDRESS = "harishaikh2004@gmail.com"
EMAIL_PASSWORD = "haris2004"

app = Flask(__name__)
app.secret_key = "my_secret_key"


# =========================================================
# LOAD ACCOUNTS
# =========================================================

with open("accounts.json", "r") as file:
    accounts = json.load(file)


# =========================================================
# SAVE ACCOUNTS
# =========================================================

def save_accounts():
    with open("accounts.json", "w") as file:
        json.dump(accounts, file, indent=4)


# =========================================================
# CONVERT OLD TRANSACTIONS
# =========================================================

def convert_old_transactions():

    changed = False

    for account_number, account in accounts.items():

        transactions = account.get("transactions", [])

        new_transactions = []

        for transaction in transactions:

            # Already upgraded
            if isinstance(transaction, dict):
                new_transactions.append(transaction)
                continue

            # Old transaction was stored as text
            text = str(transaction)

            transaction_type = "Transaction"
            amount = 0
            details = text

            # Find amount
            try:
                amount_text = text.split("₹")[1].split()[0]
                amount = int(amount_text)
            except:
                amount = 0

            # Find transaction type
            if "Deposit" in text:
                transaction_type = "Deposit"
                details = "Cash deposit"

            elif "Withdraw" in text:
                transaction_type = "Withdraw"
                details = "Cash withdrawal"

            elif "Transferred" in text:
                transaction_type = "Transfer"
                transaction_type = "Transfer"

                if "to" in text:
                    details = text.split("to", 1)[1].strip()

            elif "Received" in text:
                transaction_type = "Received"

                if "from" in text:
                    details = "Received " + text.split("from", 1)[1].strip()

            # Try to get old date/time
            parts = text.split(" - ")

            date = datetime.now().strftime("%d-%m-%Y")
            time = datetime.now().strftime("%I:%M %p")

            if len(parts) >= 1:

                old_date_time = parts[0]

                try:

                    old_datetime = datetime.strptime(
                        old_date_time,
                        "%d-%m-%y %I:%M %p"
                    )

                    date = old_datetime.strftime("%d-%m-%Y")
                    time = old_datetime.strftime("%I:%M %p")

                except:
                    pass

            new_transactions.append({
                "type": transaction_type,
                "amount": amount,
                "balance": None,
                "details": details,
                "date": date,
                "time": time,
                "status": "Completed"
            })

            changed = True

        account["transactions"] = new_transactions

    if changed:
        save_accounts()


# Convert old transaction records when Flask starts
convert_old_transactions()


# =========================================================
# ADD TRANSACTION
# =========================================================

def add_transaction(transaction_type, amount, balance, details=""):

    current_account = session.get("account")

    if current_account is None:
        return

    now = datetime.now()

    transaction = {
        "type": transaction_type,
        "amount": amount,
        "balance": balance,
        "details": details,
        "date": now.strftime("%d-%m-%Y"),
        "time": now.strftime("%I:%M %p"),
        "status": "Completed"
    }

    accounts[current_account]["transactions"].append(transaction)

    save_accounts()


# =========================================================
# RECEIPT
# =========================================================

def receipt(transaction, amount):

    current_account = session.get("account")

    now = datetime.now()

    date = now.strftime("%d-%m-%Y")
    time = now.strftime("%I:%M %p")

    return render_template(
        "receipt.html",
        name=accounts[current_account]["name"],
        account=current_account,
        transaction=transaction,
        amount=amount,
        balance=accounts[current_account]["balance"],
        date=date,
        time=time
    )


# =========================================================
# HOME
# =========================================================

@app.route("/home")
def home():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        user=accounts[current_account]
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        account_number = request.form["account"]
        pin = request.form["pin"]

        if (
            account_number in accounts
            and accounts[account_number]["pin"] == pin
        ):

            session["account"] = account_number

            return redirect(url_for("home"))

        return "❌ Invalid Account Number or PIN"

    return render_template("login.html")


# =========================================================
# BALANCE
# =========================================================

@app.route("/balance")
def check_balance():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    balance = accounts[current_account]["balance"]

    return f"Your balance is ₹{balance}"


# =========================================================
# DEPOSIT
# =========================================================

@app.route("/deposit", methods=["GET", "POST"])
def deposit():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    if request.method == "POST":

        try:
            amount = int(request.form["amount"])
        except ValueError:
            return "❌ Please enter a valid amount."

        if amount <= 0:
            return "❌ Please enter an amount greater than ₹0."

        # Add money
        accounts[current_account]["balance"] += amount

        # New balance
        new_balance = accounts[current_account]["balance"]

        # Transaction
        add_transaction(
            "Deposit",
            amount,
            new_balance,
            "Cash deposit"
        )

        return receipt("Deposit", amount)

    return render_template(
        "deposit.html",
        user=accounts[current_account]
    )


# =========================================================
# WITHDRAW
# =========================================================

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    if request.method == "POST":

        try:
            amount = int(request.form["amount"])
        except ValueError:
            return "❌ Please enter a valid amount."

        if amount <= 0:
            return "❌ Please enter an amount greater than ₹0."

        if amount > accounts[current_account]["balance"]:
            return "❌ Insufficient Balance."

        # Remove money
        accounts[current_account]["balance"] -= amount

        # New balance
        new_balance = accounts[current_account]["balance"]

        # Transaction
        add_transaction(
            "Withdraw",
            amount,
            new_balance,
            "Cash withdrawal"
        )

        return receipt("Withdraw", amount)

    return render_template(
        "withdraw.html",
        user=accounts[current_account]
    )


# =========================================================
# FAST CASH
# =========================================================

@app.route("/fastcash")
def fastcash():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    return render_template(
        "fastcash.html",
        user=accounts[current_account]
    )


# =========================================================
# FAST CASH AMOUNT
# =========================================================

@app.route("/fastcash/<int:amount>")
def fastcash_amount(amount):

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    if amount <= 0:
        return "❌ Invalid amount."

    if amount > accounts[current_account]["balance"]:
        return "❌ Insufficient Balance."

    # Withdraw money
    accounts[current_account]["balance"] -= amount

    # New balance
    new_balance = accounts[current_account]["balance"]

    # Transaction
    add_transaction(
        "Withdraw",
        amount,
        new_balance,
        "Fast Cash withdrawal"
    )

    return receipt("Fast Cash", amount)


# =========================================================
# CHANGE PIN
# =========================================================

@app.route("/changepin", methods=["GET", "POST"])
def change_pin():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    if request.method == "POST":

        old_pin = request.form["old_pin"]
        new_pin = request.form["new_pin"]
        confirm_pin = request.form["confirm_pin"]

        if accounts[current_account]["pin"] != old_pin:
            return "❌ Incorrect old PIN"

        if new_pin != confirm_pin:
            return "❌ New PIN and Confirm PIN do not match."

        accounts[current_account]["pin"] = new_pin

        save_accounts()

        return redirect(url_for("login"))

    return render_template("changepin.html")


# =========================================================
# TRANSFER MONEY
# =========================================================

@app.route("/transfer", methods=["GET", "POST"])
def transfer():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    if request.method == "POST":

        receiver = request.form["receiver"]

        try:
            amount = int(request.form["amount"])
        except ValueError:
            return "❌ Please enter a valid amount."

        # Receiver exists?
        if receiver not in accounts:
            return "❌ Receiver account not found."

        # Don't transfer to yourself
        if receiver == current_account:
            return "❌ You cannot transfer money to your own account."

        # Amount must be positive
        if amount <= 0:
            return "❌ Please enter a valid amount."

        # Check balance
        if amount > accounts[current_account]["balance"]:
            return "❌ Insufficient Balance."

        # =================================================
        # SEND MONEY
        # =================================================

        accounts[current_account]["balance"] -= amount

        sender_balance = accounts[current_account]["balance"]

        # =================================================
        # RECEIVE MONEY
        # =================================================

        accounts[receiver]["balance"] += amount

        receiver_balance = accounts[receiver]["balance"]

        # =================================================
        # SENDER TRANSACTION
        # =================================================

        add_transaction(
            "Transfer",
            amount,
            sender_balance,
            f"Transferred to account {receiver}"
        )

        # =================================================
        # RECEIVER TRANSACTION
        # =================================================

        now = datetime.now()

        receiver_transaction = {
            "type": "Received",
            "amount": amount,
            "balance": receiver_balance,
            "details": f"Received from account {current_account}",
            "date": now.strftime("%d-%m-%Y"),
            "time": now.strftime("%I:%M %p"),
            "status": "Completed"
        }

        accounts[receiver]["transactions"].append(
            receiver_transaction
        )

        save_accounts()

        return receipt("Money Transfer", amount)

    return render_template(
        "transfer.html",
        user=accounts[current_account]
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    account = accounts[current_account]
    transactions = account.get("transactions", [])

    return render_template(
        "history.html",
        account=account,
        account_number=current_account,
        transactions=transactions
    )
# =========================================================
# ACCOUNT STATEMENT
# =========================================================

@app.route("/account-statement", methods=["GET", "POST"])
def account_statement():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    if request.method == "POST":

        date_range = request.form.get("date_range")
        file_type = request.form.get("file_type")
        mode = request.form.get("mode")

        custom_from = request.form.get("custom_from")
        custom_to = request.form.get("custom_to")

        # -----------------------------------------
        # Check custom date range
        # -----------------------------------------

        if date_range == "custom":

            if not custom_from or not custom_to:
                return "❌ Please select both From Date and To Date."

            if custom_from > custom_to:
                return "❌ From Date cannot be after To Date."

        return render_template(
            "statement_confirm.html",
            user=accounts[current_account],
            date_range=date_range,
            file_type=file_type,
            mode=mode,
            custom_from=custom_from,
            custom_to=custom_to
        )

    return render_template(
        "account_statement.html",
        user=accounts[current_account]
    )


# =========================================================
# GENERATE ACCOUNT STATEMENT
# =========================================================

@app.route("/generate-statement", methods=["POST"])
def generate_statement():

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    date_range = request.form.get("date_range")
    file_type = request.form.get("file_type")
    mode = request.form.get("mode")

    custom_from = request.form.get("custom_from")
    custom_to = request.form.get("custom_to")

    # Get all transactions
    transactions = accounts[current_account]["transactions"]

    # =====================================================
    # DATE FILTERING
    # =====================================================

    today = date.today()

    selected_transactions = []

    for transaction in transactions:

        transaction_date_string = transaction.get("date")

        if not transaction_date_string:
            continue

        try:
            transaction_date = datetime.strptime(
                transaction_date_string,
                "%d-%m-%Y"
            ).date()

        except ValueError:
            continue

        include_transaction = False

        # -----------------------------------------
        # CURRENT MONTH
        # -----------------------------------------

        if date_range == "current_month":

            if (
                transaction_date.year == today.year
                and transaction_date.month == today.month
            ):
                include_transaction = True

        # -----------------------------------------
        # LAST 3 MONTHS
        # -----------------------------------------

        elif date_range == "last_3_months":

            from datetime import timedelta

            # Approximate previous 3 months
            start_date = today - timedelta(days=90)

            if start_date <= transaction_date <= today:
                include_transaction = True

        # -----------------------------------------
        # LAST FINANCIAL YEAR
        # -----------------------------------------

        elif date_range == "last_financial_year":

            # Indian financial year:
            # 1 April to 31 March

            if today.month >= 4:

                # Current FY = Apr current year -> Mar next year
                # Last FY = Apr previous year -> Mar current year

                start_date = date(today.year - 1, 4, 1)
                end_date = date(today.year, 3, 31)

            else:

                # Current FY = Apr previous year -> Mar current year
                # Last FY = Apr two years ago -> Mar previous year

                start_date = date(today.year - 2, 4, 1)
                end_date = date(today.year - 1, 3, 31)

            if start_date <= transaction_date <= end_date:
                include_transaction = True

        # -----------------------------------------
        # CUSTOM
        # -----------------------------------------

        elif date_range == "custom":

            if custom_from and custom_to:

                start_date = datetime.strptime(
                    custom_from,
                    "%Y-%m-%d"
                ).date()

                end_date = datetime.strptime(
                    custom_to,
                    "%Y-%m-%d"
                ).date()

                if start_date <= transaction_date <= end_date:
                    include_transaction = True

        # -----------------------------------------
        # ADD TRANSACTION
        # -----------------------------------------

        if include_transaction:
            selected_transactions.append(transaction)


    # =====================================================
    # DOWNLOAD CSV
    # =====================================================

    if file_type == "csv" and mode == "download":

        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "Date",
            "Time",
            "Transaction Type",
            "Amount",
            "Balance",
            "Details",
            "Status"
        ])

        for transaction in selected_transactions:

            writer.writerow([
                transaction.get("date", ""),
                transaction.get("time", ""),
                transaction.get("type", ""),
                transaction.get("amount", ""),
                transaction.get("balance", ""),
                transaction.get("details", ""),
                transaction.get("status", "")
            ])

        response = make_response(output.getvalue())

        response.headers["Content-Disposition"] = (
            f"attachment; filename="
            f"PythonBank_Statement_{current_account}.csv"
        )

        response.headers["Content-Type"] = "text/csv"

        return response


    # =====================================================
    # DOWNLOAD PDF
    # =====================================================

    if file_type == "pdf" and mode == "download":

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle
        )

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()

        elements = []

        # -----------------------------------------
        # PDF HEADER
        # -----------------------------------------

        elements.append(
            Paragraph(
                "PYTHON BANK",
                styles["Title"]
            )
        )

        elements.append(
            Paragraph(
                "Account Statement",
                styles["Heading2"]
            )
        )

        elements.append(
            Spacer(1, 15)
        )

        elements.append(
            Paragraph(
                f"<b>Account Number:</b> {current_account}",
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                f"<b>Account Holder:</b> "
                f"{accounts[current_account]['name']}",
                styles["Normal"]
            )
        )

        elements.append(
            Spacer(1, 20)
        )

        # -----------------------------------------
        # TABLE
        # -----------------------------------------

        data = [
            [
                "Date",
                "Time",
                "Type",
                "Amount",
                "Balance",
                "Status"
            ]
        ]

        for transaction in selected_transactions:

            balance = transaction.get("balance")

            if balance is None:
                balance_text = "-"
            else:
                balance_text = f"Rs. {balance:,.2f}"

            data.append([
                transaction.get("date", ""),
                transaction.get("time", ""),
                transaction.get("type", ""),
                f"Rs. {transaction.get('amount', 0):,.2f}",
                balance_text,
                transaction.get("status", "")
            ])

        # -----------------------------------------
        # NO TRANSACTIONS
        # -----------------------------------------

        if len(data) == 1:

            data.append([
                "-",
                "-",
                "No transactions",
                "-",
                "-",
                "-"
            ])

        table = Table(
            data,
            repeatRows=1
        )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0878f9")
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica"
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                )
            ])
        )

        elements.append(table)

        elements.append(
            Spacer(1, 20)
        )

        elements.append(
            Paragraph(
                "This is a computer-generated account statement.",
                styles["Normal"]
            )
        )

        # -----------------------------------------
        # CREATE PDF
        # -----------------------------------------

        doc.build(elements)

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=(
                f"PythonBank_Statement_{current_account}.pdf"
            ),
            mimetype="application/pdf"
        )


    # =====================================================
    # EMAIL
    # =====================================================

    if mode == "email":

        return render_template(
            "statement_email.html",
            user=accounts[current_account],
            file_type=file_type,
            date_range=date_range
        )


    return "❌ Invalid statement request."
@app.route("/send-statement-email", methods=["POST"])
def send_statement_email():

    import os
    import resend

    current_account = session.get("account")

    if current_account is None:
        return redirect(url_for("login"))

    email = request.form.get("email")
    file_type = request.form.get("file_type")
    date_range = request.form.get("date_range")

    custom_from = request.form.get("custom_from")
    custom_to = request.form.get("custom_to")

    # -----------------------------
    # GET TRANSACTIONS
    # -----------------------------

    transactions = accounts[current_account]["transactions"]

    today = date.today()

    selected_transactions = []

    # -----------------------------
    # DATE FILTER
    # -----------------------------

    for transaction in transactions:

        transaction_date_string = transaction.get("date")

        if not transaction_date_string:
            continue

        try:
            transaction_date = datetime.strptime(
                transaction_date_string,
                "%d-%m-%Y"
            ).date()

        except ValueError:
            continue

        include_transaction = False

        # Current Month
        if date_range == "current_month":

            if (
                transaction_date.year == today.year
                and transaction_date.month == today.month
            ):
                include_transaction = True

        # Last 3 Months
        elif date_range == "last_3_months":

            from datetime import timedelta

            start_date = today - timedelta(days=90)

            if start_date <= transaction_date <= today:
                include_transaction = True

        # Last Financial Year
        elif date_range == "last_financial_year":

            if today.month >= 4:

                start_date = date(
                    today.year - 1,
                    4,
                    1
                )

                end_date = date(
                    today.year,
                    3,
                    31
                )

            else:

                start_date = date(
                    today.year - 2,
                    4,
                    1
                )

                end_date = date(
                    today.year - 1,
                    3,
                    31
                )

            if start_date <= transaction_date <= end_date:
                include_transaction = True

        # Custom
        elif date_range == "custom":

            if custom_from and custom_to:

                start_date = datetime.strptime(
                    custom_from,
                    "%Y-%m-%d"
                ).date()

                end_date = datetime.strptime(
                    custom_to,
                    "%Y-%m-%d"
                ).date()

                if start_date <= transaction_date <= end_date:
                    include_transaction = True

        if include_transaction:
            selected_transactions.append(transaction)

    # -----------------------------
    # CREATE ATTACHMENT
    # -----------------------------

    attachment_data = None
    attachment_name = None
    attachment_type = None

    # =============================
    # CSV
    # =============================

    if file_type == "csv":

        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "Date",
            "Time",
            "Transaction Type",
            "Amount",
            "Balance",
            "Details",
            "Status"
        ])

        for transaction in selected_transactions:

            writer.writerow([
                transaction.get("date", ""),
                transaction.get("time", ""),
                transaction.get("type", ""),
                transaction.get("amount", ""),
                transaction.get("balance", ""),
                transaction.get("details", ""),
                transaction.get("status", "")
            ])

        attachment_data = output.getvalue().encode("utf-8")

        attachment_name = (
            f"PythonBank_Statement_{current_account}.csv"
        )

        attachment_type = "text/csv"

    # =============================
    # PDF
    # =============================

    elif file_type == "pdf":

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle
        )

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()

        elements = []

        elements.append(
            Paragraph(
                "PYTHON BANK",
                styles["Title"]
            )
        )

        elements.append(
            Paragraph(
                "Account Statement",
                styles["Heading2"]
            )
        )

        elements.append(
            Spacer(1, 15)
        )

        elements.append(
            Paragraph(
                f"<b>Account Number:</b> {current_account}",
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                f"<b>Account Holder:</b> "
                f"{accounts[current_account]['name']}",
                styles["Normal"]
            )
        )

        elements.append(
            Spacer(1, 20)
        )

        data = [[
            "Date",
            "Time",
            "Type",
            "Amount",
            "Balance",
            "Status"
        ]]

        for transaction in selected_transactions:

            amount = transaction.get("amount", 0)

            balance = transaction.get("balance")

            if balance is None:
                balance_text = "-"
            else:
                balance_text = f"Rs. {balance:,.2f}"

            data.append([
                transaction.get("date", ""),
                transaction.get("time", ""),
                transaction.get("type", ""),
                f"Rs. {amount:,.2f}",
                balance_text,
                transaction.get("status", "")
            ])

        if len(data) == 1:

            data.append([
                "-",
                "-",
                "No transactions",
                "-",
                "-",
                "-"
            ])

        table = Table(
            data,
            repeatRows=1
        )

        table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0878f9")
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6
                )

            ])
        )

        elements.append(table)

        elements.append(
            Spacer(1, 20)
        )

        elements.append(
            Paragraph(
                "This is a computer-generated account statement.",
                styles["Normal"]
            )
        )

        doc.build(elements)

        buffer.seek(0)

        attachment_data = buffer.read()

        attachment_name = (
            f"PythonBank_Statement_{current_account}.pdf"
        )

        attachment_type = "application/pdf"

    else:

        return "Invalid file format."

    # -----------------------------
    # SEND EMAIL USING RESEND
    # -----------------------------

    try:

        # Get API key from Windows environment variable
        resend.api_key = os.environ.get("RESEND_API_KEY")

        if not resend.api_key:
            return "❌ Resend API key not found."

        # Email content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">

            <h2 style="color:#0878f9;">
                PYTHON BANK
            </h2>

            <h3>Account Statement</h3>

            <p>
                Dear {accounts[current_account]['name']},
            </p>

            <p>
                Please find your Python Bank account statement
                attached to this email.
            </p>

            <p>
                <b>Account Number:</b> {current_account}<br>
                <b>Statement Period:</b>
                {date_range.replace("_", " ").title()}<br>
                <b>File Format:</b>
                {file_type.upper()}
            </p>

            <p>
                This is an automatically generated email
                from Python Bank.
            </p>

            <br>

            <p>
                Regards,<br>
                <b>Python Bank</b><br>
                Secure Digital Banking
            </p>

        </body>
        </html>
        """

        # Resend email parameters
        params = {
            "from": "Python Bank <onboarding@resend.dev>",
            "to": [email],
            "subject": "Python Bank - Account Statement",
            "html": html_content,

            "attachments": [
                {
                    "filename": attachment_name,
                    "content": base64.b64encode(attachment_data).decode("utf-8")
                }
            ]
        }

        # Send email
        resend.Emails.send(params)

        return render_template(
            "statement_email_success.html",
            email=email,
            file_type=file_type
        )

    except Exception as e:

        return f"""
        <h2>Email could not be sent.</h2>

        <p>
            Please check your Resend settings.
        </p>

        <p>Error:</p>

        <pre>{e}</pre>
        """

# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )