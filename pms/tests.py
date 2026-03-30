from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Booking, Customer, Room, Room_type


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class EditBookingDatesViewTest(TestCase):
    def setUp(self):
        self.room_type = Room_type.objects.create(name="Single", price=100.0, max_guests=2)
        self.room = Room.objects.create(name="101", description="Test room", room_type=self.room_type)
        self.customer = Customer.objects.create(name="Test User", email="test@test.com", phone="123456789")
        self.booking = Booking.objects.create(
            checkin=date(2026, 6, 1),
            checkout=date(2026, 6, 5),
            room=self.room,
            guests=1,
            customer=self.customer,
            total=400.0,
            code="ABC12345",
            state=Booking.NEW,
        )
        self.url = reverse("edit_booking_dates", kwargs={"pk": self.booking.id})

    def test_get_prefills_current_dates(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-06-01")
        self.assertContains(response, "2026-06-05")

    def test_free_dates_saves_correctly(self):
        response = self.client.post(self.url, {"checkin": "2026-07-01", "checkout": "2026-07-05"})
        self.assertRedirects(response, "/")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checkin, date(2026, 7, 1))
        self.assertEqual(self.booking.checkout, date(2026, 7, 5))
        self.assertEqual(self.booking.total, 400.0)  # 4 days * 100

    def test_free_dates_recalculates_total(self):
        response = self.client.post(self.url, {"checkin": "2026-07-01", "checkout": "2026-07-03"})
        self.assertRedirects(response, "/")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.total, 200.0)  # 2 days * 100

    def test_same_current_dates_not_blocked(self):
        """Booking must not conflict with itself."""
        response = self.client.post(self.url, {"checkin": "2026-06-01", "checkout": "2026-06-05"})
        self.assertRedirects(response, "/")

    def test_occupied_dates_shows_error(self):
        """Dates occupied by another booking must show the exact error."""
        other_customer = Customer.objects.create(name="Other", email="other@test.com", phone="987654321")
        Booking.objects.create(
            checkin=date(2026, 8, 1),
            checkout=date(2026, 8, 5),
            room=self.room,
            guests=1,
            customer=other_customer,
            total=400.0,
            code="XYZ12345",
            state=Booking.NEW,
        )
        response = self.client.post(self.url, {"checkin": "2026-08-01", "checkout": "2026-08-05"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay disponibilidad para las fechas seleccionadas")

    def test_checkout_before_checkin_shows_error(self):
        response = self.client.post(self.url, {"checkin": "2026-06-10", "checkout": "2026-06-05"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La fecha de checkout debe ser posterior al checkin.")

    def test_checkout_equal_checkin_shows_error(self):
        response = self.client.post(self.url, {"checkin": "2026-06-05", "checkout": "2026-06-05"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La fecha de checkout debe ser posterior al checkin.")

    def test_deleted_booking_for_same_room_does_not_block(self):
        """A cancelled booking must not block date availability."""
        other_customer = Customer.objects.create(name="Deleted", email="del@test.com", phone="000000000")
        Booking.objects.create(
            checkin=date(2026, 9, 1),
            checkout=date(2026, 9, 5),
            room=self.room,
            guests=1,
            customer=other_customer,
            total=400.0,
            code="DEL12345",
            state=Booking.DELETED,
        )
        response = self.client.post(self.url, {"checkin": "2026-09-01", "checkout": "2026-09-05"})
        self.assertRedirects(response, "/")
