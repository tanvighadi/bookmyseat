BookMySeat - Movie Booking System
BookMySeat is a movie ticket booking web application built with Django.  
It allows users to browse movies, select theaters, reserve seats, complete payments, and view booking confirmations.  

---

Key Features
1. Browse & Filter Movies – Search by genre, language, or keywords.

2. Watch Trailers – View embedded YouTube trailers directly.

3. Seat Reservation Timeout – Seats are held for 5 minutes until payment is confirmed.
If payment succeeds within 5 minutes → seats are booked.
If payment fails or timeout expires → seats are automatically released.

4. Stripe Checkout Integration – Secure online payments with retry option.

5. Email Confirmation – Automatic booking confirmation sent to the user’s email.

6. Admin Dashboard – Interactive analytics with Chart.js:
Total revenue
Most popular movies
Busiest theaters
Detailed tables

---

Tech Stack
Backend: Django (Python)
Frontend: Bootstrap + Chart.js
Database: SQLite
Payments: Stripe Checkout
Email: SendGrid 

---

IMP Notes
Staff Access: Every registered user is automatically marked as staff (is_staff=True) for access to the analytics dashboard.

Admin URL: /admin/

Dashboard URL: /admin/dashboard/ shows analytics.

Payment Flow: Use Stripe test cards to simulate transactions.
✅ Success: 4242 4242 4242 4242
❌ Failure: 4000 0000 0000 0002

Email Confirmation: Check the registered email inbox (and spam folder) for booking details.

Seat Reservation: Reserved seats auto‑release after 5 minutes if payment is not completed.