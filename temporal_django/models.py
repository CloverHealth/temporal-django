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


TimelineFieldHistory = typing.NamedTuple('TimelineFieldHistory', [
    ('value', typing.Any),
    ('label', str),
])


TimelineTick = typing.NamedTuple('TimelineTick', [
    ('clock', EntityClock),
    ('changed_fields', typing.Dict[str, TimelineFieldHistory])
])


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

    def temporal_timeline(self) -> typing.List[TimelineTick]:
        """
        Returns a timeline of field changes grouped by clock tick

        The return format is a list of clock ticks with per-field history for each:

        {
            clock: Clocked,
            changed_fields: {
                [field_name]: {
                    value: any,
                    label: str
                }
            }
        }
        """
        temporal_options = type(self).temporal_options
        timeline = []
        field_history = {
            field: getattr(self, '%s_history' % field).all()
            for field in
            temporal_options.temporal_fields
        }

        if temporal_options.activity_model:
            clock_query = self.clock.select_related('activity')
            if hasattr(temporal_options.activity_model, 'temporal_queryset_options'):
                temporal_options.activity_model.temporal_queryset_options(clock_query)
            clock_query = clock_query.all()
        else:
            clock_query = self.clock.all()

        for clock in clock_query:
            changed_fields = {}
            for field, history in field_history.items():
                for field_history_item in history:
                    if field_history_item.vclock.lower == clock.tick:
                        changed_fields[field] = TimelineFieldHistory(
                            value=getattr(field_history_item, field),
                            label=type(self)._meta.get_field(field).verbose_name,
                        )

            timeline.append(TimelineTick(clock=clock, changed_fields=changed_fields))

        return timeline


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
