from django.db import models
from temporal_django import add_clock, Clocked

from django.contrib.auth.models import User


class ItemActivity(models.Model):
    description = models.TextField()
    author = models.ForeignKey(User, blank=True, null=True)

    @staticmethod
    def temporal_queryset_options(queryset):
        return queryset.select_related('activity__author')


@add_clock('title', 'number', 'effective_date', activity_model=ItemActivity)
class Item(Clocked):
    title = models.CharField(max_length=100)
    number = models.IntegerField()
    effective_date = models.DateField()
