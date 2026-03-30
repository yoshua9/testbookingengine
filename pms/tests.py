from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Room, Room_type

SIMPLE_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


def create_room_type(name="Individual", max_guests=1, price=20.0):
    return Room_type.objects.create(name=name, max_guests=max_guests, price=price)


def create_room(name, room_type):
    return Room.objects.create(name=name, room_type=room_type, description="")


@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class RoomsFilterViewTest(TestCase):

    def setUp(self):
        rt = create_room_type()
        create_room("Room 1.1", rt)
        create_room("Room 1.2", rt)
        create_room("Room 2.1", rt)

    def test_no_filter_returns_all_rooms(self):
        response = self.client.get(reverse("rooms"))
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.context["rooms"]]
        self.assertIn("Room 1.1", names)
        self.assertIn("Room 1.2", names)
        self.assertIn("Room 2.1", names)

    def test_explicit_empty_name_returns_all_rooms(self):
        response = self.client.get(reverse("rooms"), {"name": ""})
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.context["rooms"]]
        self.assertIn("Room 1.1", names)
        self.assertIn("Room 1.2", names)
        self.assertIn("Room 2.1", names)

    def test_partial_filter_returns_only_matching_rooms(self):
        response = self.client.get(reverse("rooms"), {"name": "Room 1"})
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.context["rooms"]]
        self.assertIn("Room 1.1", names)
        self.assertIn("Room 1.2", names)
        self.assertNotIn("Room 2.1", names)

    def test_filter_with_no_match_returns_empty_list(self):
        response = self.client.get(reverse("rooms"), {"name": "XYZ"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(list(response.context["rooms"])), 0)

    def test_filter_is_case_insensitive(self):
        response = self.client.get(reverse("rooms"), {"name": "room 1"})
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.context["rooms"]]
        self.assertIn("Room 1.1", names)
        self.assertIn("Room 1.2", names)
        self.assertNotIn("Room 2.1", names)

    def test_name_filter_is_kept_in_context(self):
        response = self.client.get(reverse("rooms"), {"name": "Room 1"})
        self.assertEqual(response.context["name_filter"], "Room 1")

    def test_room_type_filter_returns_only_matching_rooms(self):
        rt_double = create_room_type(name="Doble", max_guests=2, price=30.0)
        create_room("Room 2.1", rt_double)
        response = self.client.get(reverse("rooms"), {"room_type": "Doble"})
        rooms = list(response.context["rooms"])
        names = [r["name"] for r in rooms]
        self.assertIn("Room 2.1", names)
        self.assertNotIn("Room 1.1", names)
        self.assertNotIn("Room 1.2", names)

    def test_room_type_filter_is_case_insensitive(self):
        rt_double = create_room_type(name="Doble", max_guests=2, price=30.0)
        create_room("Room 2.1", rt_double)
        response = self.client.get(reverse("rooms"), {"room_type": "doble"})
        names = [r["name"] for r in response.context["rooms"]]
        self.assertIn("Room 2.1", names)

    def test_name_and_room_type_filters_combine(self):
        rt_double = create_room_type(name="Doble", max_guests=2, price=30.0)
        create_room("Room 2.1", rt_double)
        create_room("Suite 1", rt_double)
        response = self.client.get(reverse("rooms"), {"name": "Room", "room_type": "Doble"})
        names = [r["name"] for r in response.context["rooms"]]
        self.assertIn("Room 2.1", names)
        self.assertNotIn("Suite 1", names)
        self.assertNotIn("Room 1.1", names)

    def test_room_type_filter_is_kept_in_context(self):
        response = self.client.get(reverse("rooms"), {"room_type": "Doble"})
        self.assertEqual(response.context["room_type_filter"], "Doble")

    def test_explicit_empty_room_type_returns_all_rooms(self):
        response = self.client.get(reverse("rooms"), {"room_type": ""})
        names = [r["name"] for r in response.context["rooms"]]
        self.assertEqual(len(names), 3)
