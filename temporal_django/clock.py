"""
Functions for adding a clock and history fields to a model.

Implements the add_clock function which takes a Clocked model and builds the appropriate
EntityClock and FieldHistory models, and attaches the ClockedOption.
"""
import hashlib
import sys
import typing
import uuid

from django.contrib.postgres.fields.ranges import DateTimeRangeField, IntegerRangeField
from django.db import models
from django.db.models.signals import post_init
from django.utils import timezone
import psycopg2.extras as psql_extras

from .db_extensions import GistIndex, GistExclusionConstraint

from .models import (Clocked, EntityClock, FieldHistory)
from .clocked_option import InternalClockedOption


def add_clock(*fields, activity_model=None, temporal_schema='public'):
    """
    This decorator adds a clock model and field history to a Django model.

    The model must inherit from Clocked.

    Args:
        *fields (typing.List[str]): A list of field names for which to track history
        activity_model (models.Model): The model to associate with each clock tick
        temporal_schema (typing.Optional[str]): The schema into which to put your temporal tables
    """
    def make_temporal(cls):
        assert issubclass(cls, Clocked), 'add temporal_django.Clocked to %s' % cls.__name__

        model_fields = set([f.name for f in cls._meta.fields])
        for field in fields:
            assert field in model_fields, '%s is not a field on %s' % (field, cls.__name__)

        history_models = {f: _build_field_history_model(cls, f, temporal_schema) for f in fields}
        clock_model = _build_entity_clock_model(cls, temporal_schema, activity_model)

        cls.temporal_options = InternalClockedOption(
            cls,
            temporal_fields=fields,
            history_models=history_models,
            clock_model=clock_model,
            activity_model=activity_model,
        )

        post_init.connect(_save_initial_state_post_init, sender=cls)
        _disable_bulk_create(cls)

        return cls

    return make_temporal


def _build_entity_clock_model(
        cls: typing.Type[Clocked],
        schema: str,
        activity_model: models.Model = None) -> EntityClock:
    """
    Build a Django model for the clock of a given model

    Args:
        cls (typing.Type[Clocked]): class to refer back to
        schema (str): schema to use for history table
        activity_model (models.Model): model to use to record metadata for a tick

    Returns:
        EntityClock: Clock model for the given model
    """
    clock_table_name = _truncate_identifier("%s_clock" % cls._meta.db_table)

    unique_constraints = ('tick', 'entity')
    if activity_model:
        unique_constraints = (unique_constraints, ('entity', 'activity'))

    attrs = dict(
        tick=models.IntegerField(),
        entity=models.ForeignKey(
            cls,
            related_name='clock',
            related_query_name='clocks'
        ),
        timestamp=models.DateTimeField(auto_now_add=True),
        activity=models.ForeignKey(activity_model) if activity_model else None,
        Meta=type('Meta', (), {
            'db_table': clock_table_name,
            'unique_together': unique_constraints,
        }),
        __module__=cls.__module__
    )

    clock_class_name = '%sClock' % cls.__name__
    clock_model = type(clock_class_name, (EntityClock,), attrs)
    setattr(sys.modules[cls.__module__], clock_class_name, clock_model)

    return clock_model


def _build_field_history_model(cls: typing.Type[Clocked], field: str, schema: str) -> FieldHistory:
    """
    Build a Django model for the temporal history of a given field

    Args:
        cls (typing.Type[Clocked]): class to refer back to
        field (str): field for which to to build a history class
        schema (str): schema to use for history table

    Returns:
        FieldHistory: History model for the given field
    """
    class_name = "%s%s_%s" % (cls.__name__, 'History', field)
    table_name = _truncate_identifier('%s_%s_%s' % (cls._meta.db_table, 'history', field))

    gist_exclusion_key = 'entity_id'
    if isinstance(cls._meta.pk, models.UUIDField):
        # Due to a limitation of postgres, UUIDs cannot be used in a GiST index
        gist_exclusion_key = '(entity_id::text)'

    attrs = dict(
        id=models.UUIDField(primary_key=True, default=uuid.uuid4),
        entity=models.ForeignKey(cls),
        effective=DateTimeRangeField(default=psql_extras.DateTimeRange(timezone.now(), None)),
        vclock=IntegerRangeField(),
        Meta=type('Meta', (), {
            'db_table': table_name,
            'indexes': [
                GistIndex(
                    fields=['effective'],
                    name=_truncate_identifier('ix_' + table_name + '_effective')
                ),
                GistExclusionConstraint(
                    fields=['(%s) WITH =, effective WITH &&' % gist_exclusion_key],
                    name=_truncate_identifier(table_name + '_excl_effective'),
                ),
                GistExclusionConstraint(
                    fields=['(%s) WITH =, vclock WITH &&' % gist_exclusion_key],
                    name=_truncate_identifier(table_name + '_excl_vclock'),
                )
            ]
        }),
        __module__=cls.__module__,
    )

    attrs[field] = next(f for f in cls._meta.fields if f.name == field)

    model = type(class_name, (FieldHistory,), attrs)
    setattr(sys.modules[cls.__module__], class_name, model)
    return model


def _save_initial_state_post_init(sender: typing.Type[Clocked], instance: Clocked, **kwargs):
    """
    After initializing a Clocked object, record initial field values.

    We'll use this to decide when to update a temporal history field on save.

    Args:
        sender (typing.Type[Clocked])
        instance (Clocked)
    """
    fields = sender.temporal_options.temporal_fields
    instance._state.previous = {f: instance._meta.get_field(f).value_from_object(instance) for f in fields}


def _disable_bulk_create(cls: typing.Type[Clocked]):
    """
    Try to break the bulk_create function. It's pretty incompatible with temporal entities.
    """

    def disabled_bulk_create(*args, **kwargs):
        raise ValueError(
            'You cannot use bulk_create on temporal models. ' +
            'If you are SURE that you know what you\'re doing, you can use unsafe_bulk_create')

    cls.objects.unsafe_bulk_create = cls.objects.bulk_create
    cls.objects.bulk_create = disabled_bulk_create


def _truncate_identifier(ident, max_len=63):
    if len(ident) > max_len:
        return "%s_%s" % (
            ident[0:max_len - 8],
            hashlib.md5(ident.encode('utf-8')).hexdigest()[-4:]
        )
    return ident
