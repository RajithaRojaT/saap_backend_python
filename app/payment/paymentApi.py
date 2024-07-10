import os
import json
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import FileResponse, JSONResponse
import stripe
import requests
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta, timezone
from app.login.auth import JWTBearer
from app.models import Invoice, PaymentHistory, User
from app.params import DELETED, RECORD_STATUS, USER_NOT_FOUND
from app.payment.invoice import create_invoice_pdf
from database import SessionLocal, get_db
from sqlalchemy import desc
 
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripeprice_id = os.getenv("stripe_price_id")
payments = APIRouter(prefix="/payment", tags=["payment"])
DOMAIN_URL = os.getenv("Stripeurl")

next_payment_date = (datetime.now() + timedelta(days=365)).date()


@payments.post(
    "/create-checkout-session",
)
def create_checkout_session(
    request: dict, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())
):
    """
    The above functions handle creating a checkout session for Stripe payments and checking the payment
    status.

    :param request: The `request` parameter in the `create_checkout_session` function is a dictionary
    containing the data sent in the HTTP request to create a checkout session. It likely includes
    information such as the user's email address needed to create a Stripe customer, which is then used
    to create a checkout session for payment processing
    :type request: dict
    :param db: The `db` parameter in the code snippet refers to a database session object. It is used to
    interact with the database and perform operations like querying, committing changes, and rolling
    back transactions. In this case, it seems to be an instance of a database session that is being
    passed as a dependency using
    :type db: Session
    :return: For the `create_checkout_session` endpoint, the function returns a dictionary containing
    the `session_id` and `redirect_url` if successful.
    """
    try:
        email = request.get("email")
        stripe_id = create_customer(email)

        user = db.query(User).filter(User.email == email).first()

        if user is None:
            db.close()
            return {"error": "User not found"}

        latest_payment_history = (
            db.query(PaymentHistory)
            .filter(PaymentHistory.customer_id == user.stripe_id)
            .all()
        )

        if latest_payment_history:
            for payment_history in latest_payment_history:
                if payment_history.next_payment_date > datetime.now().date():
                    return {"error": "Next payment date has not arrived yet"}

        checkout_session = stripe.checkout.Session.create(
            customer=stripe_id,
            line_items=[
                {
                    "price": stripeprice_id,
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=DOMAIN_URL + "/payment-status",
            cancel_url=DOMAIN_URL + "/payment-status",
        )
        print(checkout_session)

        check_out_id = checkout_session.id
        db.close()
        return {"session_id": check_out_id, "redirect_url": checkout_session.url}
    except stripe.error.StripeError as e:
        db.close()
        raise HTTPException(status_code=400, detail=str(e))


@payments.get("/check-payment-status/")
def check_payment_status(
    db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())
):
    """
    The function `check_payment_status` retrieves payment information for a given user ID and returns
    details if the payment is successful.

    :param user_id: The `user_id` parameter in the `check_payment_status` function is a unique
    identifier for a user in your system. It is used to retrieve information about a specific
    user's payment status and gather relevant details such as payment amount, transaction ID, renewal date,
    billing details, etc.
    :type user_id: str
    :param db: The `db` parameter in the code snippet refers to a database session object. It is used to
    interact with the database and perform operations like querying, committing changes, and rolling
    back transactions.
    :type db: Session
    :return: The `check_payment_status` function returns a response dictionary containing information
    about the payment status. If the payment status is "paid", it includes details such as transaction
    ID, amount paid in USD, customer billed to, renewal date, and billing details. If the payment status
    is not "paid", it returns a message indicating that the payment is pending.
    """
 
    try:
        user_id = user_data["id"]
        user_payment_history = (
            db.query(PaymentHistory)
            .filter(PaymentHistory.created_by_id == user_id)
            .order_by(desc(PaymentHistory.created_at))
            .first()
        )
        if user_payment_history and user_payment_history.status == "paid":
            session_id = user_payment_history.stripe_checkout_id
            transaction_date_time = user_payment_history.created_at
            session = stripe.checkout.Session.retrieve(session_id)
            customer_id = session.customer
            customer = stripe.Customer.retrieve(customer_id)
            customer_name = customer.name if customer and customer.name else None
            billing_details = session.metadata.get("billing_details", {})
            payment_date = user_payment_history.payment_date
            next_payment_date = user_payment_history.next_payment_date
            amount_paid = user_payment_history.total_amount
            transaction_id = user_payment_history.stripe_payment_intent_id
            plan_active = "inactive"
            if next_payment_date and next_payment_date > datetime.now().date():
                plan_active = "active"
            response = {
                "status": True,
                "message": "Payment successful!",
                "transaction_id": transaction_id,
                "billed_to": customer_name,
                "amount_paid_usd": amount_paid,
                "payment_date": payment_date.strftime("%d %B %Y"),
                "renewal_date": next_payment_date.strftime("%d %B %Y"),
                # "billing_details": billing_details,
                "plan_active": plan_active,
                "transaction_date_time": transaction_date_time,
            }
            db.close()
            return response
        else:
            db.close()
            return {"status": False, "message": "Payment Failed."}
    except stripe.error.StripeError as e:
        db.close()
        raise HTTPException(status_code=400, detail=str(e))


@payments.post("/webhook")
async def webhook(request: Request):
    """
    The function processes a Stripe webhook event for completed checkout sessions and generates and
    saves invoice details.

    :param request: The code snippet you provided is a Python FastAPI endpoint for handling a webhook
    from Stripe. The endpoint processes a checkout session completed event and saves relevant payment
    and invoice details to a database
    :type request: Request
    :return: The code snippet is returning a JSONResponse with content {"success": True}.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    customer_id = event["data"]["object"]["customer"]
    customer = stripe.Customer.retrieve(customer_id)
    customer_email = customer.get("email", None)
    db = SessionLocal()
    user_details = (
        db.query(User)
        .filter(
            User.email == customer_email,
            User.record_status == RECORD_STATUS,
            User.deleted == DELETED,
        )
        .first()
    )
    if user_details is None:
        db.close()
        response = JSONResponse(
            content={
                "success": False,
                "message": "USER_NOT_FOUND",
                "translation_key": "USER_NOT_FOUND",
                "status": status.HTTP_400_BAD_REQUEST,
            }
        )
        response.status_code = status.HTTP_400_BAD_REQUEST
        return response

    if event["type"] == "invoice.created":
        invoice = event["data"]["object"]
        expiry_date_timestamp = invoice["period_end"]
        next_payment_date = (datetime.now() + timedelta(days=365)).date()
        created_by_id = user_details.id
        expires_at_datetime = datetime.fromtimestamp(
            expiry_date_timestamp, timezone.utc
        )
        next_payment_formatted_date = expires_at_datetime.strftime("%Y-%m-%d %H:%M:%S")
        payment_history = (
            db.query(PaymentHistory)
            .filter(PaymentHistory.invoice_detail == invoice.id)
            .first()
        )
        invoiceObject = SaveInvoiceDetail(
            db,
            event["data"]["object"].id,
            invoice,
            payment_history,
            next_payment_formatted_date,
            customer_email,
        )

    if event["type"] == "checkout.session.completed":
 
        session = event["data"]["object"]
        payment_intent_id = session["payment_intent"]
        checkout_id = session["id"]
        customer_id = session["customer"]
        payment_status = session.get("payment_status")
        payment_transaction_status = session["status"]
        payment_intent_ids = session["payment_intent"]
        payment_intents = stripe.PaymentIntent.retrieve(payment_intent_ids)
        next_payment_date = (datetime.now() + timedelta(days=365)).date()
        paid_amount = payment_intents["amount_received"] / 100
        total_amount = paid_amount
        customer_name = session.customer_details.name
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
 
        payment_history = PaymentHistory(
            payment_date=datetime.now().date(),
            total_amount=total_amount,
            next_payment_date=next_payment_date,
            status=payment_status,
            created_by_id=user_details.id,
            stripe_payment_intent_id=payment_intent_id,
            stripe_checkout_id=checkout_id,
            customer_id=customer_id,
            stripe_transaction_status=payment_transaction_status,
            checkout_detail=json.dumps(session),
            payment_intent_detail=json.dumps(payment_intent),
            # stripe_subscription_id= customer_name,
        )
 
        db.add(payment_history)
        db.commit()
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=(
                False if payment_intent["payment_method_types"][0] == "card" else True
            ),
        )
        payment_history.invoice_detail = invoice.id
        db.add(payment_history)
 
        db.commit()
        # user = db.query(User).filter(User.email == customer_email).first()
        # if user:
        #     user.role_id = 2
        #     db.commit()
    db.close()
    return JSONResponse(content={"success": True})


def create_customer(email):
    """
    The function `create_customer` checks if a customer with a given email exists in the Stripe
    database, and creates a new customer if not.

    :param email: The `create_customer` function takes an email as a parameter. This function is used to
    create a new customer in a payment processing system like Stripe using the provided email address.
    If a customer with the same email already exists, it retrieves the existing customer ID. If not, it
    creates a new customer
    :return: The `create_customer` function returns the `customer_id` of the newly created customer or
    the existing customer based on the provided email. If an error occurs during the process, it returns
    `None`.
    """
    try:
        existing_customers = stripe.Customer.list(email=email, limit=1)
        if existing_customers.data:
            customer_id = existing_customers.data[0].id
        else:
            customer = stripe.Customer.create(
                email=email,
            )
            customer_id = customer.id
        return customer_id
    except stripe.error.StripeError as e:
        print(f"Error creating customer: {e}")
        return None
 
@payments.get("/invoices/")
def get_invoices(
    user_id: int, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())
):
    """
    This Python function retrieves all invoices from the database filtered by user_id, along with the
    This Python function retrieves all invoices from the database filtered by user_id, along with the
    amount_paid from the payment_history table.

    :param user_id: The ID of the user whose invoices are to be retrieved.
    :type user_id: int
    :param db: The `db` parameter in the `get_invoices` function is of type `Session` and is obtained
    using the `Depends` function with the `get_db` function as a dependency. This parameter represents a
    database session that will be used to query the database for invoices.
    :type db: Session
    :return: A list of dictionaries containing invoice details and amount_paid.
    """
    results = (
        db.query(
            Invoice,
            PaymentHistory.total_amount,
            Invoice.payment_date,
            PaymentHistory.next_payment_date,
            PaymentHistory.stripe_payment_intent_id,
        )
        .join(PaymentHistory, Invoice.payment_id == PaymentHistory.id)
        .filter(Invoice.created_by_id == user_id)
        .all()
    )


    invoices = []
    for (
        invoice_obj,
        amount_paid,
        payment_date,
        next_payment_date,
        stripe_payment_intent_id,
    ) in results:
        # Calculate subscription period
        subscription_period = None
        subscription_period_str = None
        if next_payment_date and payment_date:
            difference_in_days = (next_payment_date - payment_date).days
            subscription_period_in_months = round(difference_in_days / 30.4375)
            subscription_period_str = f"{subscription_period_in_months} Months"

        invoice = {
            "invoice": {
                "created_at": invoice_obj.created_at,
                "payment_id": invoice_obj.payment_id,
                "payment_date": payment_date.strftime("%Y-%m-%d"),
                "created_by_id": invoice_obj.created_by_id,
                "stripe_invoice_id": invoice_obj.stripe_invoice_id,
                "next_invoice_date": (
                    next_payment_date.strftime("%Y-%m-%d")
                    if next_payment_date
                    else None
                ),
                "id": invoice_obj.id,
                "status": invoice_obj.status,
                "invoice_status": "Success",
                "file_path": invoice_obj.file_path,
            },
            "amount_paid": amount_paid,
            "start_date": payment_date.strftime("%d %B %Y"),
            "renewal_date": (
                next_payment_date.strftime("%d %B %Y") if next_payment_date else None
            ),
            "plan_status": (
                "active"
                if next_payment_date and next_payment_date > datetime.now().date()
                else "inactive"
            ),
            "transaction_id": stripe_payment_intent_id,
            "subscription_plan": (
                "Yearly"
                if next_payment_date and difference_in_days >= 365
                else "Monthly"
            ),
            "subscription_period": f"{payment_date.strftime('%d %B %Y')} - {next_payment_date.strftime('%d %B %Y')}",
        }
        invoices.append(invoice)
    db.close()
    return invoices


def SaveInvoiceDetail(
    db: Session,
    invoice_id: str,
    invoice_data: json,
    payment_history: dict,
    next_payment_date: date,
    customer_email: str,
):
    """
    This function saves invoice details along with payment history and subscription data in a database.

    :param db: The `db` parameter is an instance of the database session that will be used to interact
    with the database. It is typically used to query, insert, update, and delete data from the database
    within the context of a session

    """
    try:

        pdffile = retrieve_invoice_pdf(invoice_id)
        db_invoice = Invoice(
            stripe_invoice_id=invoice_id,
            invoice_detail=invoice_data,
            payment_id=payment_history.id,
            status=invoice_data["status"],
            next_invoice_date=next_payment_date,
            file_path=pdffile,
            invoice_status="Success",
        )
        db_invoice.payment_date = payment_history.payment_date
        db_invoice.created_by_id = payment_history.created_by_id
        db_invoice.invoice_detail = invoice_data
        db.add(db_invoice)
        db.commit()
        db.refresh(db_invoice)
        return db_invoice
    except Exception as e:
        print("error in invoice", str(e))
        response = JSONResponse(
            content={
                "success": False,
                "message": "An error occurred.",
                "translation_key": "INTERNAL_SERVER_ERROR",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response
    finally:
        db.close()
 
 
def retrieve_invoice_pdf(invoice_id):
    """
    The function `retrieve_invoice_pdf` retrieves and saves an invoice PDF from Stripe API or creates a
    custom invoice PDF if the PDF URL is not available.

    :param invoice_id: The `retrieve_invoice_pdf` function you provided seems to be a Python function
    that retrieves and saves an invoice PDF from a Stripe invoice. It first checks if the invoice has a
    PDF URL, and if not, it creates a custom PDF with invoice details. If a PDF URL is available, it
    downloads
    :return: The function `retrieve_invoice_pdf` returns the file path of the invoice PDF that was
    either created or downloaded successfully. If there was an error during the process, it returns
    `None`.
    """
    try:
        db = SessionLocal()
        destination_path = "invoices"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
        invoice = stripe.Invoice.retrieve(invoice_id)
        pdf_url = invoice.invoice_pdf
        # payment_history = db.query(PaymentHistory).filter(PaymentHistory.stripe_checkout_id == session_id).first()

        payments = (
            db.query(PaymentHistory)
            .filter(PaymentHistory.invoice_detail == invoice.id)
            .first()
        )
        next_payment_date = payments.next_payment_date
        plan_active = "inactive"
        if (
            payments
            and payments.next_payment_date
            and payments.next_payment_date > datetime.now().date()
        ):
            plan_active = "active"
        transaction_id = payments.stripe_payment_intent_id
        amount = payments.total_amount
        payment_date = payments.payment_date
        subscription_period = (
            next_payment_date - payment_date if next_payment_date else None
        )

        subscription_plan = (
            "Yearly"
            if subscription_period and subscription_period.days >= 365
            else "Monthly"
        )
        subscription_period_in_months = None

        if next_payment_date and payment_date:
            difference_in_days = (next_payment_date - payment_date).days

            subscription_period_in_months = round(difference_in_days / 30.4375)

            subscription_period = subscription_period_in_months
        subscription_period_str = (
            str(subscription_period) + " Months" if subscription_period else None
        )

        if pdf_url is None:
            utc_datetime = datetime.fromtimestamp(invoice.period_start, timezone.utc)
            invoice_date = utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
            invoice_data = {
                "Invoice Number": invoice.id,
                "Date": payment_date.strftime("%d %B %Y"),
                # "customer_info":invoice.customer_address,
                # "Customer Information":invoice.account_name,
                "Subscription Plan": subscription_plan,
                "Subscription Period": f"{payment_date.strftime('%d %B %Y')} - {next_payment_date.strftime('%d %B %Y')}",
                "Total Amount Paid": amount,
                "Transaction ID": transaction_id,
                # "Currency":invoice.currency,
                # "account_country":invoice.account_country,
                # "account_name": invoice.account_name,
                # "currency":invoice.currency,
                # "Customer":invoice.customer,
                "Subscription Expiry Date": next_payment_date.strftime("%d %B %Y"),
                "Status": plan_active,
            }
            file_path = os.path.join(
                destination_path, f"invoice_{invoice_id}_{timestamp}.pdf"
            )
            create_invoice_pdf(file_path, invoice_data)

            print("Custom invoice PDF created successfully.")
            return file_path
        else:
            response = requests.get(pdf_url)
            if response.status_code == 200:
                file_path = os.path.join(
                    destination_path, f"invoice_{invoice.id}_{timestamp}.pdf"
                )
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print("Invoice PDF saved successfully.")
            else:
                print(
                    f"Failed to download invoice PDF. Status code: {response.status_code}"
                )
        return f"invoice_{invoice.id}_{timestamp}.pdf"

    except stripe.error.StripeError as e:
        print(f"Failed to retrieve invoice PDF: {e}")
        return None


@payments.get("/download-invoice-pdf/{filename}")
async def get_invoice(
    filename: str,
    # user_data: dict = Depends(JWTBearer())
):
    """
    The function `get_invoice` retrieves and returns an invoice file specified by the filename
    parameter.
    """
    invoice_path = os.path.join("invoices", filename)
    if not os.path.exists(invoice_path):
        raise HTTPException(status_code=404, detail="Invoice not found")

    return FileResponse(invoice_path, filename=filename)


@payments.post("/currentplan")
def get_subscription(request: dict, db: Session = Depends(get_db)):
    # Check if the user is subscribed
    is_subscribed = (
        db.query(PaymentHistory.created_by_id)
        .filter(PaymentHistory.created_by_id == request["id"])
        .first()
    )
    if is_subscribed:
        return {"data": {"plan": "subscribed"}}

    else:
        # Get the user's creation date
        created_date = (
            db.query(User.created_at).filter(User.id == request["id"]).first()
        )
        created_date = created_date[0] if created_date else None

        if created_date:
            today_date = datetime.now()
            # Calculate the difference in days between today and the user's creation date
            time_period = (today_date - created_date).days

            if time_period < 30:
                return {
                    "data": {
                        "plan": "trial",
                        "expires_in": 30 - time_period,
                        "start_date": created_date,
                    }
                }
            else:
                return {
                    "data": {
                        "plan": "no subscription",
                        "trial_expired": created_date + timedelta(days=30),
                        "start_date": created_date,
                    }
                }

    # If the user is not subscribed
    return {"data": {"plan": "no subscription", "message": "User not subscribed"}}