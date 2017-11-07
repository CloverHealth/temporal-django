from django.test import TestCase
from django.db import IntegrityError

from .models import TestModel, TestModelActivity, NoActivityModel, AnotherTestModel


class ActivityTests(TestCase):
    def test_no_activity(self):
        """A model without a supplied activity should be able to be created and edited"""
        obj = NoActivityModel(title='Test', num=1)
        obj.save()

        created_obj = NoActivityModel.objects.first()
        self.assertEqual(created_obj.title, 'Test')

        created_obj.num = 2
        created_obj.save()

        edited_obj = NoActivityModel.objects.first()
        self.assertEqual(edited_obj.num, 2)

    def test_missing_activity(self):
        """
        If a model has an activity, you shouldn't be able to create or edit an object without
        supplying one.
        """
        obj = TestModel(title='Test', num=1)
        with self.assertRaisesMessage(ValueError, 'activity is required'):
            obj.save()

    def test_superfluous_activity(self):
        """
        If a model has no activity, you shouldn't be able to save if you've attached one.abs

        This is to avoid user expectation mismatch of thinking that their activities are being
        associated correctly.
        """
        act = TestModelActivity(desc='Create the object')
        act.save()

        obj = NoActivityModel(title='Test', num=1)
        obj.activity = act
        with self.assertRaisesMessage(ValueError, 'no activity model'):
            obj.save()

    def test_no_same_model_activity_reuse(self):
        """You shouldn't be able to re-use an activity for the same model"""
        act = TestModelActivity(desc='Create the object')
        act.save()

        obj = TestModel(title='Test', num=1)
        obj.activity = act
        obj.save()

        created_obj = TestModel.objects.first()

        created_obj.title = 'Test 2'
        created_obj.activity = act

        with self.assertRaises(IntegrityError):
            # We don't have a fancy error message because it'd be inefficient to check for this
            # use case. Intead we'll let the DB catch it and blow up.
            created_obj.save()

    def test_activity_with_multiple_models(self):
        """
        While you can't re-use a single activity for the same object, you should definitely
        be able to re-use one for multiple models.
        """

        act = TestModelActivity(desc='Create two objects!')
        act.save()

        obj1 = TestModel(title='Test', num=1)
        obj2 = AnotherTestModel(title='Test')

        obj1.activity = act
        obj2.activity = act

        obj1.save()
        obj2.save()

        self.assertEqual(obj1.first_tick().activity, act)
        self.assertEqual(obj2.first_tick().activity, act)

        # Make sure it didn't do something silly like duplicate the activity.
        self.assertEquals(TestModelActivity.objects.count(), 1)

    def test_activity_with_multiple_objects(self):
        """
        While you can't re-use a single activity for the same object, you should definitely
        be able to re-use one for multiple objects of the same type.
        """

        act = TestModelActivity(desc='Create two objects!')
        act.save()

        obj1 = TestModel(title='Test 1', num=1)
        obj2 = TestModel(title='Test 2', num=2)

        obj1.activity = act
        obj2.activity = act

        obj1.save()
        obj2.save()

        self.assertEqual(obj1.first_tick().activity, act)
        self.assertEqual(obj2.first_tick().activity, act)

        # Make sure it didn't do something silly like duplicate the activity.
        self.assertEquals(TestModelActivity.objects.count(), 1)
