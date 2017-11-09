.. _overview:


Overview
========

Temporal Django lets you track changes to objects over time and require that changes be documented with
metadata about when and why changes were made.

It was designed for auditable systems at Clover Health, where temporal history is used in workflow
systems that require documented history of changes that can be frequently accessed by day-to-day users
as well as auditors.


Temporal concepts
-----------------

Temporal Django works on the concept of an object clock: each change is a **tick** in the clock, and each
tick can have additional information about what changed, when, and why. A model whose changes we track in
Temporal is called a **clocked** model.

The tick is a per-object monotonically increasing integer. When an object is created, that's tick 1. The first
edit after creation is tick 2, etc. In the data model the tick is sometimes called ``vclock``, which is short
for "version clock".

Each tick can have custom associated metadata called the **activity**; this can be used to record information
like the author of the change, a reason for the change, or configuration around how the change should be
displayed in the system's audit logs. Temporal Django doesn't have an opinion on what metadata is recorded
about a tick other than a timestamp.

Temporal Django records history in a sparse model, because it was designed for working on broad tables with
lots of columns. An edit to a single field will only record the change to that one field, but will still
increment the clock tick.


Data model
----------

Temporal Django creates one additional table and model per clocked model, the ``EntityClock``, and one
additional table and model per tracked field, the per-field ``FieldHistory``.

It will also add a new field called ``vclock`` to the clocked model, which is used to record the current tick.

The ``EntityClock`` model records the ticks and their timestamps, and has a foreign key to the activity. A
clocked model's ``EntityClock`` model will be named ``{model_name}Clock``; the corresponding table will be
``{table_name}_clock``.

Each tracked model field will have a ``FieldHistory`` model. It records the value of a single field over time
and the range of ticks and timestamps for which it was active. The models are named
``{model_name}History_{field_name}``; the tables are ``{table_name}_history_{field_name}``.


Example model
-------------

To take a simple example model::

    from temporal_django import add_clock, Clocked

    @add_clock('name', 'color', activity_model=AnimalActivity)
    class Animal(Clocked)
        name = TextField()
        color = TextField()

        class Meta:
            table_name = 'animals'

Temporal will add ``vclock = IntegerField()`` to the ``Animal`` model and will implicitly create these
additional models::

    class AnimalClock(EntityClock):
        tick = models.IntegerField()
        entity = models.ForeignKey(Animal, related_name='clock', related_query_name='clocks')
        timestamp = models.DateTimeField()
        activity = models.ForeignKey(AnimalActivity)

        class Meta:
            table_name = 'animals_clock'

    class AnimalHistory_name(FieldHistory):
        name = models.TextField()
        entity = models.ForeignKey(Animal, related_name='name_history'),
        effective = DateTimeRangeField(),
        vclock = IntegerRangeField(),

        class Meta:
            table_name = 'animals_history_name'

    class AnimalHistory_color(FieldHistory):
        color = models.TextField()
        entity = models.ForeignKey(Animal, related_name='color_history'),
        effective = DateTimeRangeField(),
        vclock = IntegerRangeField(),

        class Meta:
            table_name = 'animals_history_color'

Operations
----------

Creating an object will add rows to all of the tables to record the initial values, and will set the clock
tick to 1.

Saving an object will add a new ``EntityClock`` row and add rows to the ``FieldHistory`` tables for any
changed field.

The ``effective`` and ``vclock`` ranges on ``FieldHistory`` will have a null upper bound for new rows. When
saving a change, the ranges for the now-expired row will have their upper bound set.

Temporal Django does not support deletion of objects. Consider adding an ``is_deleted`` boolean to your
models and tracking its value over time with Temporal.

All temporal operations are atomic. Consistency of ranges is enforced with exclusion constraints, where for a
single entity, overlapping ``vclock`` or ``effective`` ranges are forbidden. Clock ticks for a single entity
have uniqueness constraints preventing a single tick from occurring twice, or from an activity being re-used.

Example operations
------------------

Saving a ``turtle = Animal(name='Turtle', color='green')`` will perform the following operations atomically:

1. Save the ``Animal``
2. Save the provided ``AnimalActivity``
3. Create a new ``AnimalClock`` with ``tick=1`` and (for example) ``timestamp='2017-11-08 12:00:00+00'``. It
   will be linked to both the new ``Animal`` and the new ``AnimalActivity``
4. Create a new ``AnimalHistory_color`` and ``AnimalHistory_name`` with ``tick=int4range[1, null)``,
   ``effective=tstzrange['2017-11-08 12:00:00+00', null)`` and respectively ``color='green'``
   and ``name='turtle'``. These will be linked to the ``Animal``

Saving a subsequent change to ``turtle.color = 'gold'`` will:

1. Save the update to the ``Animal`` and increment its ``vclock``.
2. Save the provided ``AnimalActivity``
3. Create a new ``AnimalClock`` with a tick of 2 and the current timestamp, linked to the original ``Animal``
   and the new ``AnimalActivity``
4. Cap off the previous ``AnimalHistory_color``'s ``vclock`` and ``effective`` range to the current tick and
   timestamp. The value of ``vclock`` for example will be ``int4range[1, 2)``.
5. Add an ``AnimalHistory_color`` (for example, with a ``vclock`` of ``int4range[2, null)`` and a
   ``color='gold'``)
6. Leave ``AnimalHistory_name`` unchanged for this tick because the value did not change.
