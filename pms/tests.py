import datetime

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Booking, Customer, Room, Room_type

SIMPLE_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_room_type(name="Individual", max_guests=1, price=20.0):
    return Room_type.objects.create(name=name, max_guests=max_guests, price=price)


def create_room(name, room_type):
    return Room.objects.create(name=name, room_type=room_type, description="")


def create_customer(name="John Doe", email="john@example.com", phone="123456789"):
    return Customer.objects.create(name=name, email=email, phone=phone)


def create_booking(room, customer, state=Booking.NEW, checkin=None, checkout=None):
    checkin = checkin or datetime.date.today()
    checkout = checkout or checkin + datetime.timedelta(days=1)
    return Booking.objects.create(
        room=room,
        customer=customer,
        state=state,
        checkin=checkin,
        checkout=checkout,
        guests=1,
        total=room.room_type.price,
        code="ABC12345",
    )


# ---------------------------------------------------------------------------
# Dashboard — Occupancy rate widget + date range selector
# ---------------------------------------------------------------------------

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class DashboardOccupancyTest(TestCase):

    def setUp(self):
        self.rt = create_room_type()
        self.room = create_room("Room 1.1", self.rt)
        self.customer = create_customer()
        self.today = datetime.date.today()
        self.today_str = self.today.strftime('%Y-%m-%d')

    def test_dashboard_defaults_to_today_for_both_dates(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["date_from"], self.today_str)
        self.assertEqual(response.context["date_to"], self.today_str)

    def test_dashboard_accepts_date_range_from_query_string(self):
        response = self.client.get(reverse("dashboard"), {
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
        })
        self.assertEqual(response.context["date_from"], "2024-01-01")
        self.assertEqual(response.context["date_to"], "2024-01-31")

    def test_invalid_dates_fall_back_to_today(self):
        response = self.client.get(reverse("dashboard"), {
            "date_from": "bad",
            "date_to": "also-bad",
        })
        self.assertEqual(response.context["date_from"], self.today_str)
        self.assertEqual(response.context["date_to"], self.today_str)

    def test_inverted_range_is_corrected(self):
        response = self.client.get(reverse("dashboard"), {
            "date_from": "2024-01-31",
            "date_to": "2024-01-01",
        })
        self.assertEqual(response.context["date_from"], "2024-01-01")
        self.assertEqual(response.context["date_to"], "2024-01-31")

    def test_occupancy_rate_is_zero_with_no_bookings(self):
        response = self.client.get(reverse("dashboard"), {
            "date_from": self.today_str,
            "date_to": self.today_str,
        })
        self.assertEqual(response.context["dashboard"]["occupancy_rate"], 0.0)

    def test_occupancy_rate_is_zero_when_no_rooms_exist(self):
        Room.objects.all().delete()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["dashboard"]["occupancy_rate"], 0.0)

    def test_occupancy_rate_calculates_correctly_for_range(self):
        room2 = create_room("Room 1.2", self.rt)
        room3 = create_room("Room 1.3", self.rt)
        room4 = create_room("Room 1.4", self.rt)
        tomorrow = self.today + datetime.timedelta(days=1)
        create_booking(self.room, self.customer, checkin=self.today, checkout=tomorrow)
        create_booking(room2, self.customer, checkin=self.today, checkout=tomorrow)
        create_booking(room3, self.customer, checkin=self.today, checkout=tomorrow)
        response = self.client.get(reverse("dashboard"), {
            "date_from": self.today_str,
            "date_to": self.today_str,
        })
        # 3 confirmed overlapping / 4 rooms = 75.0%
        self.assertEqual(response.context["dashboard"]["occupancy_rate"], 75.0)

    def test_cancelled_bookings_are_excluded_from_occupancy(self):
        tomorrow = self.today + datetime.timedelta(days=1)
        create_booking(self.room, self.customer, state=Booking.DELETED,
                       checkin=self.today, checkout=tomorrow)
        response = self.client.get(reverse("dashboard"), {
            "date_from": self.today_str,
            "date_to": self.today_str,
        })
        self.assertEqual(response.context["dashboard"]["occupancy_rate"], 0.0)

    def test_booking_outside_range_is_excluded(self):
        last_week = self.today - datetime.timedelta(days=7)
        last_week_end = self.today - datetime.timedelta(days=3)
        create_booking(self.room, self.customer, checkin=last_week, checkout=last_week_end)
        response = self.client.get(reverse("dashboard"), {
            "date_from": self.today_str,
            "date_to": self.today_str,
        })
        self.assertEqual(response.context["dashboard"]["occupancy_rate"], 0.0)

    def test_occupancy_rate_is_in_dashboard_context(self):
        response = self.client.get(reverse("dashboard"))
        self.assertIn("occupancy_rate", response.context["dashboard"])
