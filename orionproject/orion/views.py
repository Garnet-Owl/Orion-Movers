from django.shortcuts import render, redirect
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from .models import Mover, Rating, Order, Customer, CustomUser
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RatingForm, PaymentForm, MoverCreationForm, UserCreationForm, CustomUserCreationForm, MoverForm, OrderForm
import stripe
from .verify import verify_identity, submit_background_check, send_verification_code, check_verification_code
from django.contrib.auth import login


def create_user(request):
    # if the request is a GET, display the user creation form
    if request.method == "GET":
        form = UserCreationForm()
        return render(request, "create_user.html", {"form": form})
    # if the request is a POST, validate and save the form data
    elif request.method == "POST":
        form = UserCreationForm(request.POST)
        # if the form is valid, create a new user instance and send verification codes to email and phone
        if form.is_valid():
            user = form.save(commit=False) # don't save to database yet
            user.is_active = False # deactivate the user until verification is complete
            email = form.cleaned_data["email"]
            phone_number = form.cleaned_data["phone_number"]
            send_verification_code(email, "email") # send email verification code using Twilio Verify
            send_verification_code(phone_number, "sms") # send phone verification code using Twilio Verify
            user.save() # save the user to database
            # store the user id in the session and redirect to the verification page
            request.session["user_id"] = user.id
            return redirect("verify_user")
        else:
            # if the form is invalid, display the errors and the form again
            return render(request, "create_user.html", {"form": form})




@login_required # require the user to be logged in
def create_mover(request):
    # if the request is a GET, display the mover creation form
    if request.method == "GET":
        form = MoverCreationForm()
        return render(request, "create_mover.html", {"form": form})
    # if the request is a POST, validate and save the form data
    elif request.method == "POST":
        form = MoverCreationForm(request.POST)
        # if the form is valid, create a new mover instance and verify identity and submit background check
        if form.is_valid():
            mover = form.save(commit=False) # don't save to database yet
            mover.user = request.user # associate the mover with the current user
            vehicle = form.cleaned_data["vehicle"]
            identity_document = form.cleaned_data["identity_document"]
            verify_identity(identity_document) # verify identity using a third-party service
            submit_background_check(identity_document) # submit background check using a third-party service
            mover.save() # save the mover to database
            messages.success(request, "Your mover account has been created and is pending verification.")
            return redirect("home")
        else:
            # if the form is invalid, display the errors and the form again
            return render(request, "create_mover.html", {"form": form})


def match_movers(request):
    # if the request is a GET, display the customer location form
    if request.method == "GET":
        return render(request, "match_movers.html")
    # if the request is a POST, get the customer location and find the nearest movers
    elif request.method == "POST":
        # get the customer IP address from the request headers
        ip_address = request.META.get("REMOTE_ADDR")
        # use a third-party API to get the geolocation data from the IP address
        geolocation_data = abstract_api.ip_geolocation(ip_address)
        # create a Point object from the latitude and longitude values
        customer_location = Point(geolocation_data["latitude"], geolocation_data["longitude"])
        # create or update a Customer object with the IP address and location
        customer, created = Customer.objects.update_or_create(
            ip_address=ip_address,
            defaults={"location": customer_location}
        )
        # find the movers that have verified identity and background check
        verified_movers = Mover.objects.filter(identity_verified=True, background_check=True)
        # order the movers by distance to the customer location
        nearest_movers = verified_movers.annotate(distance=Distance("location", customer_location)).order_by("distance")
        # render the results in a template
        return render(request, "match_results.html", {"customer": customer, "movers": nearest_movers})


@login_required # require the user to be logged in
def order_moving_service(request):
    # if the request is a GET, display the order form with the available movers
    if request.method == "GET":
        # get the customer location from the Customer model
        customer = request.user.customer
        customer_location = customer.location
        # find the movers that have verified identity and background check
        verified_movers = Mover.objects.filter(identity_verified=True, background_check=True)
        # order the movers by distance to the customer location
        nearest_movers = verified_movers.annotate(distance=Distance("location", customer_location)).order_by("distance")
        # create an order form with the nearest movers as choices for the mover field
        form = OrderForm(movers=nearest_movers)
        return render(request, "order_moving_service.html", {"form": form})
    # if the request is a POST, validate and save the order data
    elif request.method == "POST":
        form = OrderForm(request.POST)
        # if the form is valid, create a new order instance and calculate the total cost
        if form.is_valid():
            order = form.save(commit=False) # don't save to database yet
            order.customer = request.user.customer # associate the order with the current customer
            mover = form.cleaned_data["mover"] # get the selected mover from the form data
            start_address = form.cleaned_data["start_address"] # get the start address from the form data
            end_address = form.cleaned_data["end_address"] # get the end address from the form data
            start_time = form.cleaned_data["start_time"] # get the start time from the form data
            end_time = form.cleaned_data["end_time"] # get the end time from the form data
            # use a third-party API to get the distance between the start and end addresses
            distance = abstract_api.distance(start_address, end_address)
            # use a third-party API to get the duration of the moving service based on the start and end times
            duration = abstract_api.duration(start_time, end_time)
            # calculate the total cost based on the mover's rate, distance, and duration
            total_cost = mover.rate * distance * duration
            order.total_cost = total_cost # set the total cost attribute of the order
            order.save() # save the order to database
            messages.success(request, "Your order has been placed and is pending confirmation.")
            return redirect("home")
        else:
            # if the form is invalid, display the errors and the form again
            return render(request, "order_moving_service.html", {"form": form})


@login_required # require the user to be logged in
def process_payment(request, order_id):
    # get the order instance by the order id
    order = Order.objects.get(id=order_id)
    # get the minimum deposit amount from the order total cost (assume 10%)
    deposit_amount = int(order.total_cost * 0.1)
    # set the stripe secret key from the settings.py file
    stripe.api_key = settings.STRIPE_SECRET_KEY
    # if the request is a GET, display the payment form with the order and deposit details
    if request.method == "GET":
        form = PaymentForm()
        return render(request, "process_payment.html", {"form": form, "order": order, "deposit_amount": deposit_amount})
    # if the request is a POST, validate and process the payment data
    elif request.method == "POST":
        form = PaymentForm(request.POST)
        # if the form is valid, get the payment information from the form data
        if form.is_valid():
            card_number = form.cleaned_data["card_number"]
            card_expiry_month = form.cleaned_data["card_expiry_month"]
            card_expiry_year = form.cleaned_data["card_expiry_year"]
            card_cvc = form.cleaned_data["card_cvc"]
            # create a stripe token using the payment information
            try:
                token = stripe.Token.create(
                    card={
                        "number": card_number,
                        "exp_month": card_expiry_month,
                        "exp_year": card_expiry_year,
                        "cvc": card_cvc,
                    },
                )
            except stripe.error.CardError as e:
                # handle card error and display a message to the user
                messages.error(request, e.user_message)
                return redirect("process_payment", order_id=order_id)
            # create a stripe charge using the token and the deposit amount
            try:
                charge = stripe.Charge.create(
                    amount=deposit_amount,
                    currency="usd",
                    source=token,
                    description=f"Deposit for order {order_id}",
                )
            except stripe.error.StripeError as e:
                # handle stripe error and display a message to the user
                messages.error(request, e.user_message)
                return redirect("process_payment", order_id=order_id)
            # if the charge is successful, update the order status and payment details
            if charge.paid:
                order.status = "confirmed"
                order.payment_id = charge.id
                order.payment_method = "stripe"
                order.save()
                messages.success(request, "Your payment has been processed and your order has been confirmed.")
                return redirect("home")
            else:
                # handle payment failure and display a message to the user
                messages.error(request, "Your payment could not be processed. Please try again.")
                return redirect("process_payment", order_id=order_id)
        else:
            # if the form is invalid, display the errors and the form again
            return render(request, "process_payment.html", {"form": form, "order": order, "deposit_amount": deposit_amount})


@login_required # require the user to be logged in
def rate_mover(request, mover_id):
    # get the mover instance by the mover id
    mover = Mover.objects.get(id=mover_id)
    # if the request is a GET, display the rating form with the mover details
    if request.method == "GET":
        form = RatingForm()
        return render(request, "rate_mover.html", {"form": form, "mover": mover})
    # if the request is a POST, validate and save the rating data
    elif request.method == "POST":
        form = RatingForm(request.POST)
        # if the form is valid, create a new rating instance and update the mover rating
        if form.is_valid():
            rating = form.save(commit=False) # don't save to database yet
            rating.user = request.user # associate the rating with the current user
            rating.mover = mover # associate the rating with the selected mover
            score = form.cleaned_data["score"] # get the score from the form data
            comment = form.cleaned_data["comment"] # get the comment from the form data
            rating.save() # save the rating to database
            # update the mover rating by calculating the average score of all ratings
            ratings = Rating.objects.filter(mover=mover) # get all ratings for the mover
            total_score = 0 # initialize the total score variable
            for r in ratings: # loop through all ratings
                total_score += r.score # add each score to the total score
            average_score = total_score / len(ratings) # calculate the average score by dividing the total score by the number of ratings
            mover.rating = average_score # set the mover rating attribute to the average score
            mover.save() # save the changes to database
            messages.success(request, "Your rating has been submitted and the mover rating has been updated.")
            return redirect("home")
        else:
            # if the form is invalid, display the errors and the form again
            return render(request, "rate_mover.html", {"form": form, "mover": mover})


def search_movers(request):
    # get the user input from the query parameter "q"
    q = request.GET.get("q")
    # if there is no user input, display all movers
    if not q:
        movers = Mover.objects.all()
        return render(request, "search_movers.html", {"movers": movers})
    # if there is user input, try to parse it as a location
    try:
        # use a third-party API to get the geolocation data from the user input
        geolocation_data = abstract_api.geocode(q)
        # create a Point object from the latitude and longitude values
        user_location = Point(geolocation_data["latitude"], geolocation_data["longitude"])
        # find the movers that have verified identity and background check
        verified_movers = Mover.objects.filter(identity_verified=True, background_check=True)
        # order the movers by distance to the user location
        nearest_movers = verified_movers.annotate(distance=Distance("location", user_location)).order_by("distance")
        # render the results in a template
        return render(request, "search_movers.html", {"movers": nearest_movers, "q": q})
    except:
        # if the user input is not a valid location, display an error message
        return render(request, "search_movers.html", {"error": "Invalid location. Please try again."})


