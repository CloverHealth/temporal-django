from django.db import models
from django.test import TestCase

from temporal_django import Clocked, add_clock
from .models import TestModel, NoActivityModel


class MisuseTests(TestCase):
    def test_bulk_create(self):
        """
        bulk_create should fail on temporal models.

        The Django ORM doesn't send signals on bulk create, so we can't temporalize bulk creates.
        """
        obj1 = TestModel(title='Test 1', num=1, vclock=1)
        obj2 = TestModel(title='Test 2', num=2, vclock=1)

        with self.assertRaisesMessage(ValueError, 'cannot use bulk_create'):
            TestModel.objects.bulk_create([obj1, obj2])

    def test_no_delete(self):
        """
        You shouldn't be able to delete temporal objects. No destroying history.
        """
        obj = NoActivityModel(title='Test 1', num=1)
        obj.save()
        self.assertEquals(NoActivityModel.objects.count(), 1)

        with self.assertRaisesMessage(ValueError, 'cannot delete'):
            obj.delete()

    def test_temporal_field_not_in_model(self):
        """You shouldn't be able to try to define a temporal field that doesn't exist"""

        with self.assertRaisesMessage(AssertionError, 'not_a_field is not a field on BrokenModel'):
            @add_clock('not_a_field')
            class BrokenModel(Clocked):
                title = models.CharField(max_length=100)

    def test_missing_clocked(self):
        """You should get a clear message if you try to add a tick to a model without Clocked"""

        with self.assertRaisesMessage(AssertionError, 'add temporal_django.Clocked to UnclockedModel'):
            @add_clock('title')
            class UnclockedModel(models.Model):
                title = models.CharField(max_length=100)
