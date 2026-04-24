import json
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Count, Sum, F
from django.utils.safestring import mark_safe
from datetime import timedelta
import stripe
from .models import Movie, Theater, Seat, Booking
from django.urls import reverse

stripe.api_key = settings.STRIPE_SECRET_KEY


def movie_list(request):
    movies = Movie.objects.all()
    genre = request.GET.get('genre')
    language = request.GET.get('language')
    search_query = request.GET.get('search')

    if genre and genre != "All":
        movies = movies.filter(genre__iexact=genre)
    if language and language != "All":
        movies = movies.filter(language__iexact=language)
    if search_query:
        movies = movies.filter(name__icontains=search_query)

    return render(request, 'movies/movie_list.html', {
        'movies': movies,
        'selected_genre': genre,
        'selected_language': language,
        'search_query': search_query,
    })


def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {
        'movie': movie,
        'theaters': theaters
    })


@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theater)

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        if not selected_seats:
            return render(request, "movies/seat_selection.html", {
                'theater': theater,
                'seats': seats,
                'error': "No seat selected"
            })

        seat_numbers = []
        for seat_id in selected_seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theater)
            if seat.is_booked or seat.is_reserved():
                return render(request, "movies/seat_selection.html", {
                    'theater': theater,
                    'seats': seats,
                    'error': f"Seat {seat.seat_number} is already reserved or booked."
                })
            # Reserve for 5 minutes
            seat.reserved_until = timezone.now() + timedelta(minutes=5)
            seat.save()
            seat_numbers.append(seat.seat_number)

        ticket_price = theater.ticket_price
        total_price = ticket_price * len(seat_numbers)

        request.session['seat_numbers'] = ", ".join(seat_numbers)
        request.session['total_price'] = float(total_price)
        request.session['theater_id'] = theater.id
        request.session['movie_id'] = theater.movie.id

        return redirect('payment_page', booking_id=theater.id)

    return render(request, 'movies/seat_selection.html', {
        'theater': theater,
        'seats': seats
    })


@login_required(login_url='/login/')
def payment_page(request, booking_id):
    theater = get_object_or_404(Theater, id=booking_id)
    total_price = request.session.get('total_price')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': f"{theater.movie.name} - {theater.name}",
                },
                'unit_amount': int(float(total_price) * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(
            reverse('booking_success', args=[booking_id])
        ),
        cancel_url=request.build_absolute_uri(
            reverse('payment_failed', args=[booking_id])
        ),
    )

    return render(request, "movies/payment_page.html", {
        "movie_name": theater.movie.name,
        "theater_name": theater.name,
        "seat_numbers": request.session.get('seat_numbers'),
        "ticket_price": theater.ticket_price,
        "total_price": total_price,
        "booking_id": booking_id,
        "STRIPE_SESSION_ID": session.id,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    })


@login_required(login_url='/login/')
def booking_success(request, booking_id):
    theater = get_object_or_404(Theater, id=booking_id)
    seat_numbers = request.session.get('seat_numbers').split(", ")
    booking_list = []

    for seat_number in seat_numbers:
        seat = Seat.objects.get(seat_number=seat_number, theater=theater)
        # Only book if reserved and not expired
        if seat.reserved_until and seat.reserved_until > timezone.now() and not seat.is_booked:
            booking = Booking.objects.create(
                user=request.user,
                seat=seat,
                movie=theater.movie,
                theater=theater
            )
            seat.is_booked = True
            seat.reserved_until = None
            seat.save()
            booking_list.append(booking)

    html_content = render_to_string("emails/booking_confirmation.html", {
        "user_name": request.user.username,
        "movie_name": theater.movie.name,
        "theater_name": theater.name,
        "seat_numbers": ", ".join(seat_numbers),
        "ticket_price": theater.ticket_price,
        "total_price": request.session.get('total_price'),
        "show_date": theater.time.date(),
        "show_time": theater.time.strftime("%I:%M %p"),
    })

    send_mail(
        subject="Your BookMySeat Ticket Confirmation",
        message="Your booking is confirmed. Please check the HTML version for full details.",
        from_email="fs23if025@gmail.com",
        recipient_list=[request.user.email],
        html_message=html_content
    )

    return render(request, "movies/booking_success.html", {
        "booking_list": booking_list,
        "seat_numbers": ", ".join(seat_numbers),
        "total_price": request.session.get('total_price'),
        "show_date": theater.time.date(),
        "show_time": theater.time.strftime("%I:%M %p"),
    })


@login_required(login_url='/login/')
def payment_failed(request, booking_id):
    theater = get_object_or_404(Theater, id=booking_id)
    seat_numbers = request.session.get('seat_numbers').split(", ")

    # Seats will auto-release after 5 minutes due to reserved_until timeout.

    return render(request, "movies/payment_failed.html", {
        "movie_name": theater.movie.name,
        "theater_name": theater.name,
        "seat_numbers": ", ".join(seat_numbers),
        "ticket_price": theater.ticket_price,
        "total_price": request.session.get('total_price'),
        "booking_id": booking_id,
        "user": request.user,
    })


# ADMIN DASHBOARD VIEW 
@login_required(login_url='/login/')
def admin_dashboard(request):
    total_revenue = Booking.objects.aggregate(
        revenue=Sum(F('theater__ticket_price'))
    )['revenue'] or 0

    popular_movies = Movie.objects.annotate(
        bookings_count=Count('booking')
    ).order_by('-bookings_count')[:5]

    busy_theaters = Theater.objects.annotate(
        bookings_count=Count('booking')
    ).order_by('-bookings_count')[:5]

    movie_labels = [m.name for m in popular_movies]
    movie_data = [m.bookings_count for m in popular_movies]

    theater_labels = [t.name for t in busy_theaters]
    theater_data = [t.bookings_count for t in busy_theaters]

    context = {
        "total_revenue": total_revenue,
        "popular_movies": popular_movies,
        "busy_theaters": busy_theaters,
        "movie_labels": mark_safe(json.dumps(movie_labels)),
        "movie_data": mark_safe(json.dumps(movie_data)),
        "theater_labels": mark_safe(json.dumps(theater_labels)),
        "theater_data": mark_safe(json.dumps(theater_data)),
    }
    return render(request, "movies/admin_dashboard.html", context)
