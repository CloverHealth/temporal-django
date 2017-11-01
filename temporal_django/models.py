import datetime

from django.db import models


class EntityClock(models.Model):
    """Model for a clock table"""
    class Meta:
        abstract = True

    tick = models.IntegerField()
    timestamp = models.DateTimeField()


class FieldHistory(models.Model):
    """Model for a column/field history table"""
    entity = None  # type: models.ForeignKey
    effective = None  # type: psql_extras.DateTimeRange
    vclock = None  # type: psql_extras.NumericRange

    class Meta:
        abstract = True


class Clocked(models.Model):
    """
    Clocked Mixin gives you the default implementations of working with clocked data

    Use with add_clock to handle temporalizing your model:
    """
    class Meta:
        abstract = True

    vclock = models.IntegerField(default=0)
    """The current clock tick for this object"""

    clock = None  # type: models.ForeignKey
    """The clock history of this object"""

    temporal_options = None  # type: ClockedOption
    """Configuration and state for the temporal behaviors of this object"""

    activity = None  # type: models.Model
    """Use this to set the activity for the next save"""

    @property
    def first_tick(self) -> EntityClock:
        """The clock object for the earliest tick of this object's history"""
        return self.clock.first()

    @property
    def latest_tick(self) -> EntityClock:
        """The clock object for the most recent tick of this object's history"""
        return self.clock.last()

    @property
    def date_created(self) -> datetime.datetime:
        first_tick = self.first_tick
        if first_tick:
            return first_tick.timestamp

    @property
    def date_modified(self) -> datetime.datetime:
        latest_tick = self.latest_tick
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
