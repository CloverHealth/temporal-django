import datetime

from django.test import TestCase
from freezegun import freeze_time

from .models import TestModel, TestModelActivity


class ClockedTests(TestCase):
    def test_date_created_and_modified(self):
        """The date_created and date_modified properties should work"""
        with freeze_time('2017-10-31'):
            act = TestModelActivity(desc='Create the object')
            act.save()

            obj = TestModel(title='Test', num=1)

            self.assertIsNone(obj.date_created())
            self.assertIsNone(obj.date_modified())

            obj.activity = act
            obj.save()

            created_obj = TestModel.objects.first()
            self.assertEqual(created_obj.title, 'Test')
            self.assertEqual(created_obj.date_created(), datetime.datetime(2017, 10, 31))
            self.assertEqual(created_obj.date_created(), created_obj.date_modified())

        with freeze_time('2017-11-01'):
            act = TestModelActivity(desc='Edit the object')
            act.save()

            created_obj.title = 'Test 2'
            created_obj.activity = act
            created_obj.save()

            edited_obj = TestModel.objects.first()

            self.assertEqual(edited_obj.title, 'Test 2')
            self.assertEqual(edited_obj.date_created(), datetime.datetime(2017, 10, 31))
            self.assertEqual(edited_obj.date_modified(), datetime.datetime(2017, 11, 1))

    def test_first_and_latest_tick(self):
        """The first_tick and latest_tick models should also work"""
        act = TestModelActivity(desc='Create the object')
        act.save()

        obj = TestModel(title='Test', num=1)
        obj.activity = act
        obj.save()

        created_obj = TestModel.objects.first()
        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.first_tick().tick, created_obj.vclock)

        act = TestModelActivity(desc='Edit the object')
        act.save()

        created_obj.title = 'Test 2'
        created_obj.activity = act
        created_obj.save()

        edited_obj = TestModel.objects.first()

        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.latest_tick().tick, 2)
        self.assertEqual(created_obj.latest_tick().tick, edited_obj.vclock)

    def test_no_changes_no_tick(self):
        """Verify that if you don't change anything, but do a save, that no tick is created"""
        act = TestModelActivity(desc='Create the object')
        act.save()

        obj = TestModel(title='Test', num=1)
        obj.activity = act
        obj.save()

        created_obj = TestModel.objects.first()
        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.first_tick().tick, created_obj.vclock)

        act = TestModelActivity(desc='Edit the object')
        act.save()
        created_obj.activity = act
        created_obj.save()

        edited_obj = TestModel.objects.first()

        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.latest_tick().tick, 1)
        self.assertEqual(created_obj.latest_tick().tick, edited_obj.vclock)
