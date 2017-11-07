import datetime

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

    def test_temporal_timeline_results(self):
        """Verify that the results of the timeline are as expected"""

        # Re-use the data from this test:
        with freeze_time('2017-10-31'):
            act = TestModelActivity(desc='Create the object')
            act.save()
            obj = TestModel(title='Test', num=1)
            obj.activity = act
            obj.save()

        with freeze_time('2017-11-01'):
            act = TestModelActivity(desc='Edit the object')
            act.save()
            obj.title = 'Test 2'
            obj.activity = act
            obj.save()

        with freeze_time('2017-11-02'):
            act = TestModelActivity(desc='Do a third edit')
            act.save()
            obj = TestModel.objects.first()
            obj.num = 5
            obj.activity = act
            obj.save()

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

        act = TestModelActivityWithRelationship(stub=stub)
        act.save()

        obj = TestModelWithActivityWithRelationship(title='Test object')
        obj.activity = act
        obj.save()

        with self.assertNumQueries(3):  # One query for the clock, one for the field, one for the stub.
            timeline = obj.temporal_timeline()
            with self.assertNumQueries(1):
                self.assertEqual(timeline[0].clock.activity.stub.title, 'Test stub')

        act = TestModelActivityWithEfficientRelationship(stub=stub)
        act.save()

        obj = TestModelWithActivityWithEfficientRelationship(title='Test object')
        obj.activity = act
        obj.save()

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
