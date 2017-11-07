import datetime

from django.db.utils import IntegrityError
from django.test import TestCase
from freezegun import freeze_time

from .models import (
    TestModel,
    TestModelActivity,
    Stub,
    TestModelActivityWithRelationship,
    TestModelWithActivityWithRelationship,
    TestModelActivityWithEfficientRelationship,
    TestModelWithActivityWithEfficientRelationship,
    NoActivityModel,
)


class ClockedTests(TestCase):
    def test_date_created_and_modified(self):
        """The date_created and date_modified properties should work"""
        with freeze_time('2017-10-31'):
            obj = TestModel(title='Test', num=1)

            self.assertIsNone(obj.date_created())
            self.assertIsNone(obj.date_modified())

            obj.save(activity=TestModelActivity(desc='Create the object'))

            created_obj = TestModel.objects.first()
            self.assertEqual(created_obj.title, 'Test')
            self.assertEqual(created_obj.date_created(), datetime.datetime(2017, 10, 31))
            self.assertEqual(created_obj.date_created(), created_obj.date_modified())

        with freeze_time('2017-11-01'):
            created_obj.title = 'Test 2'
            created_obj.save(activity=TestModelActivity(desc='Edit the object'))

            edited_obj = TestModel.objects.first()

            self.assertEqual(edited_obj.title, 'Test 2')
            self.assertEqual(edited_obj.date_created(), datetime.datetime(2017, 10, 31))
            self.assertEqual(edited_obj.date_modified(), datetime.datetime(2017, 11, 1))

    def test_first_and_latest_tick(self):
        """The first_tick and latest_tick models should also work"""
        obj = TestModel(title='Test', num=1)
        obj.save(activity=TestModelActivity(desc='Create the object'))

        created_obj = TestModel.objects.first()
        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.first_tick().tick, created_obj.vclock)

        created_obj.title = 'Test 2'
        created_obj.save(activity=TestModelActivity(desc='Edit the object'))

        edited_obj = TestModel.objects.first()

        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.latest_tick().tick, 2)
        self.assertEqual(created_obj.latest_tick().tick, edited_obj.vclock)

    def test_no_changes_no_tick(self):
        """Verify that if you don't change anything, but do a save, that no tick is created"""
        obj = TestModel(title='Test', num=1)
        obj.save(activity=TestModelActivity(desc='Create the object'))

        created_obj = TestModel.objects.first()
        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.first_tick().tick, created_obj.vclock)

        created_obj.save(activity=TestModelActivity(desc='Edit the object'))

        edited_obj = TestModel.objects.first()

        self.assertEqual(created_obj.first_tick().tick, 1)
        self.assertEqual(created_obj.latest_tick().tick, 1)
        self.assertEqual(created_obj.latest_tick().tick, edited_obj.vclock)

    def test_temporal_timeline_results(self):
        """Verify that the results of the timeline are as expected"""

        # Re-use the data from this test:
        with freeze_time('2017-10-31'):
            obj = TestModel(title='Test', num=1)
            obj.save(activity=TestModelActivity(desc='Create the object'))

        with freeze_time('2017-11-01'):
            obj.title = 'Test 2'
            obj.save(activity=TestModelActivity(desc='Edit the object'))

        with freeze_time('2017-11-02'):
            obj = TestModel.objects.first()
            obj.num = 5
            obj.save(activity=TestModelActivity(desc='Do a third edit'))

        with self.assertNumQueries(3):  # One query for the object, one for each field
            timeline = obj.temporal_timeline()

        self.assertEqual(len(timeline), 3)

        # Verify correct order of history
        self.assertEqual(timeline[0].clock.timestamp, datetime.datetime(2017, 10, 31))
        self.assertEqual(timeline[1].clock.timestamp, datetime.datetime(2017, 11, 1))
        self.assertEqual(timeline[2].clock.timestamp, datetime.datetime(2017, 11, 2))

        # Verify fields changed are sparse:
        self.assertEqual(timeline[0].changed_fields['title'].value, 'Test')
        self.assertEqual(timeline[0].changed_fields['num'].value, 1)
        self.assertEqual(timeline[1].changed_fields['title'].value, 'Test 2')
        self.assertNotIn('num', timeline[1].changed_fields)  # Tick 2 didn't change the number
        self.assertEqual(timeline[2].changed_fields['num'].value, 5)
        self.assertNotIn('title', timeline[2].changed_fields)  # Tick 3 didn't change the title

    def test_temporal_timeline_temporal_queryset_options(self):
        """
        Make sure that we can specify additional select_relateds via a static method on models in order to
        reduce query count when activities contain a ForeignKey.
        """
        stub = Stub(title='Test stub')
        stub.save()

        obj = TestModelWithActivityWithRelationship(title='Test object')
        obj.save(activity=TestModelActivityWithRelationship(stub=stub))

        with self.assertNumQueries(3):  # One query for the clock, one for the field, one for the stub.
            timeline = obj.temporal_timeline()
            with self.assertNumQueries(1):
                self.assertEqual(timeline[0].clock.activity.stub.title, 'Test stub')

        obj = TestModelWithActivityWithEfficientRelationship(title='Test object')
        obj.save(activity=TestModelActivityWithEfficientRelationship(stub=stub))

        with self.assertNumQueries(2):  # One query for the clock, one for the field.
            timeline = obj.temporal_timeline()

            # This time, the stub gets loaded with a join and doesn't cause another query.
            with self.assertNumQueries(0):
                self.assertEqual(timeline[0].clock.activity.stub.title, 'Test stub')

    def test_temporal_timeline_no_activity(self):
        """Make sure that the temporal_timeline still functions for models with no activity"""

        obj = NoActivityModel(title='Object', num=1)
        obj.save()

        timeline = obj.temporal_timeline()
        self.assertIsNone(timeline[0].clock.activity)

    def test_atomic_save(self):
        """
        Verify that saves are atomic

        If we crash down in the temporal update, the original object shouldn't save.
        """

        # Create a bogus scenario that will fail:
        obj = NoActivityModel(title='Object', num=1)
        obj.save()

        with self.assertRaises(IntegrityError):
            obj.vclock = 0
            obj.title = 'No save!'
            obj.save()

        # retrieve the object from the db and verify nothing was saved
        saved_obj = NoActivityModel.objects.first()
        self.assertEqual(saved_obj.title, 'Object')
        self.assertEqual(saved_obj.clock.count(), 1)
        self.assertEqual(saved_obj.title_history.count(), 1)
