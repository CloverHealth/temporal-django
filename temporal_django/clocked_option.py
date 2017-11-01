"""
Implements the private ClockedOption API, which is ultimately responsible for handling
writing history.
"""
import typing

from django.db import models, connection, transaction
from django.db.models.signals import pre_save, post_save, pre_delete
from django.utils import timezone
import psycopg2.extras as psql_extras

from .models import (Clocked, EntityClock, FieldHistory, ClockedOption)


class InternalClockedOption(ClockedOption):
    def __init__(self,
                 target_class: typing.Type[Clocked],
                 history_models: typing.Dict[str, FieldHistory],
                 temporal_fields: typing.List[str],
                 clock_model: EntityClock,
                 activity_model: typing.Optional[models.Model] = None):
        self.history_models = history_models
        self.temporal_fields = temporal_fields
        self.clock_model = clock_model
        self.activity_model = activity_model

        pre_save.connect(receiver=self.pre_save_receiver, sender=target_class)
        post_save.connect(receiver=self.post_save_receiver, sender=target_class)
        pre_delete.connect(receiver=self.pre_delete_receiver, sender=target_class)

    def pre_save_receiver(self, sender, instance=None, **kwargs):
        """receiver for pre_save signal on a Clocked subclass"""
        # We'll check this in the post_save receiver to see if we need to set
        # the initial clock/history
        instance._state.temporal_add = instance._state.adding

    def post_save_receiver(self, sender, instance=None, **kwargs):
        """receiver for post_save signal on a Clocked subclass"""
        self._record_history(instance)

    def pre_delete_receiver(self, sender, **kwargs):
        """receiver for pre_delete signal on a Clocked subclass"""
        raise ValueError("You cannot delete temporal objects. Consider an is_deleted boolean.")

    @transaction.atomic
    def _record_history(self, clocked: Clocked):
        """
        Record all history for a given clocked object

        Args:
            clocked (Clocked): instance of clocked object
        """

        #
        # Check for activity misuse
        #
        if clocked.temporal_options.activity_model is not None and clocked.activity is None:
            raise ValueError('An activity is required when saving a %s' %
                             type(clocked).__name__)
        if clocked.temporal_options.activity_model is None and clocked.activity is not None:
            raise ValueError('There is no activity model for %s; you cannot supply an activity' %
                             type(clocked).__name__)

        #
        # Determine which fields have changed
        #
        changed_fields = {}
        for field, history_model in self.history_models.items():
            new_val = clocked._meta.get_field(field).value_from_object(clocked)
            if clocked._state.temporal_add or (new_val != clocked._state.previous[field]):
                changed_fields[(field, history_model)] = new_val

        if not changed_fields:
            return

        #
        # Increment the clock and build the effective and vclock ranges for the next tick
        #
        timestamp = timezone.now()
        clocked.vclock += 1
        new_tick = clocked.vclock

        #
        # Create the EntityClock for this tick
        #
        clock_model = type(clocked).temporal_options.clock_model
        if clocked.temporal_options.activity_model is not None:
            clock = clock_model(entity=clocked, activity=clocked.activity, tick=new_tick)
        else:
            clock = clock_model(entity=clocked, tick=new_tick)
        clock.save()

        #
        # Create the field history for this tick
        #
        for (field, history_model), new_val in changed_fields.items():
            if new_tick > 1:
                # This is an update. Record the upper bounds of the previous tick
                with connection.cursor() as cursor:
                    # TODO: Try to rewrite with the ORM
                    query = """
                        update {}
                        set vclock=int4range(lower(vclock), %s),
                            effective=tstzrange(lower(effective), %s)
                        where entity_id=%s and lower(vclock)=%s
                        """.format(connection.ops.quote_name(history_model._meta.db_table))
                    cursor.execute(query, [new_tick, timestamp, clocked.pk, new_tick - 1])

            hist = history_model(**{field: new_val},
                                 entity=clocked,
                                 vclock=psql_extras.NumericRange(new_tick, None),
                                 effective=psql_extras.DateTimeTZRange(timestamp, None))
            hist.save()

            # Update the stored state for this field to detect future changes
            clocked._state.previous[field] = new_val

        # Reset the activity so it can't be accidentally reused easily
        clocked.activity = None

        # Update the vclock value without triggering a recursive `record_history`
        type(clocked).objects \
            .filter(**{clocked._meta.pk.name: getattr(clocked, clocked._meta.pk.name)}) \
            .update(vclock=new_tick)
