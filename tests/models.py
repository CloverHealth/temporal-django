import uuid

from django.db import models

from temporal_django import Clocked, add_clock


class TestModelActivity(models.Model):
    """the activity class for changes to our test model"""
    desc = models.TextField()


@add_clock('title', 'num', activity_model=TestModelActivity)
class TestModel(Clocked):
    """A test model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    num = models.IntegerField()


@add_clock('title', activity_model=TestModelActivity)
class AnotherTestModel(Clocked):
    """Another test model using the same activity model as the first"""
    title = models.CharField(max_length=100)


@add_clock('title', 'num')
class NoActivityModel(Clocked):
    """A test model with no activity model"""
    title = models.CharField(max_length=100)
    num = models.IntegerField()


@add_clock('vegetable', 'animal', 'mineral')
class IAmTheVeryModelOfAModernLongNamedTemporalIveInformationVegetableAnimalAndMineral(Clocked):
    """
    A test model with a very long name

    This is here to make sure truncating table/constraint/index names works correctly.
    """
    vegetable = models.TextField()
    animal = models.TextField()
    mineral = models.TextField()
