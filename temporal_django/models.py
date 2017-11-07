import datetime
import typing  # noqa

from django.db import models
from django.contrib.postgres.fields import DateTimeRangeField, IntegerRangeField


class EntityClock(models.Model):
    """Model for a clock table"""
    tick = models.IntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        abstract = True


class FieldHistory(models.Model):
    """Model for a column/field history table"""
    entity = None  # type: models.ForeignKey
    effective = DateTimeRangeField()
    vclock = IntegerRangeField()

    class Meta:
        abstract = True


class Clocked(models.Model):
    """
    Clocked Mixin gives you the default implementations of working with clocked data

    Use with add_clock to handle temporalizing your model:
    """

    vclock = models.IntegerField(default=0)
    """The current clock tick for this object"""

    clock = None  # type: models.ForeignKey
    """The clock history of this object"""

    temporal_options = None  # type: typing.ClassVar[ClockedOption]
    """Configuration and state for the temporal behaviors of this model"""

    activity = None  # type: models.Model
    """Use this to set the activity for the next save"""

    class Meta:
        abstract = True

    def first_tick(self) -> EntityClock:
        """The clock object for the earliest tick of this object's history"""
        return self.clock.first()

    def latest_tick(self) -> EntityClock:
        """The clock object for the most recent tick of this object's history"""
        return self.clock.last()

    def date_created(self) -> datetime.datetime:
        """Returns the date and time this object was created"""
        first_tick = self.first_tick()
        if first_tick:
            return first_tick.timestamp

    def date_modified(self) -> datetime.datetime:
        """Returns the date and time this object was most recently modified"""
        latest_tick = self.latest_tick()
        if latest_tick:
            return latest_tick.timestamp


class ClockedOption:
    """Configuration and state of temporal behaviors on a clocked model"""

    history_models = None  # type: Dict[str, FieldHistory]
    """A lookup of field name to the temporal model"""

    temporal_fields = None  # type: List[str]
    """A list of fields that have history"""

    clock_model = None  # type: EntityClock
    """The model of the entity clock for this entity"""

    activity_model = None  # type: Optional[models.Model]
    """The model for activities for this entity"""
