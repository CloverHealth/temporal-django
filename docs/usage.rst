.. _usage:


Usage
========

Django Temporal has a fairly small API. Everything starts with creating a clocked model.


Creating a clocked model
-------------------------

A model can be made Temporal with the ``@add_tick`` decorator and the ``Clocked`` mixin.

``@add_tick`` takes a list of field names to track and an optional ``activity_model`` kwarg if you need to
require additional information about changes to the model.

::

    from temporal_django import add_tick, Clocked
    from django.db.models import Model, TextField


    @add_tick('my_field', 'my_other_field')
    class MyModel(Clocked):
        """A clocked model with no activity"""
        my_field = TextField()
        my_other_field = TextField()
        an_untracked_field = TextField()


    class MyActivity(Model):
        reason_for_change = TextField()


    @add_tick('my_field', activity_model=MyActivity)
    class MyOtherModel(Clocked):
        """A clocked model with an activity"""
        my_field = TextField()

Saving history
--------------

If your model has no activity model, saving is the same as a plain ol' Django model::

    obj = MyModel(my_field='Initial value')
    obj.save()

If you do have an activity model, you have to pass it as an argument to the save method::

    obj = MyOtherModel(my_field='Initial value')
    obj.save(activity=MyActivity(reason_for_change='Creating an object'))


Retrieving a timeline
---------------------

Clocked models provide several methods for accessing history of fields and the model as whole. If your goal
is to retrieve a timeline of changes, the ``Clocked.temporal_timeline`` method will efficiently retrieve
the entire history of the model::

    timeline = my_obj.temporal_timeline()
    for timeline_entry in timeline:
        print('%s on %s' % ('Edited' if timeline_entry.tick > 1 else 'Created',
                            timeline_entry.clock.timestamp)
        for field_name, field_history in timeline_entry.changed_fields:
            print('Set %s to %s' % (field_name, field_history.value))

Clocked models also provide convenience methods for accessing the first and latest tick, and the dates created
and modified::

    first_tick = my_obj.first_tick()  # type: EntityClock
    latest_tick = my_obj.latest_tick()  # type: EntityClock

    date_created = my_obj.date_created()  # type: datetime.datetime
    date_modified = my_obj.date_modified()  # type: datetime.datetime

These will all query the EntityClock under the hood.

Efficiently retrieving activities
---------------------------------

A common use case for activities is to document who made a change. You might have an activity model that looks
like this::

    class UserActivity(Model):
        reason_for_change = TextField()
        author = ForeignKey(User)

If you were to use ``temporal_timeline()`` to retrieve this history for display, you'd probably want to load
the user as well, so you could display their name in the timeline. By default, this wouldn't be loaded
efficiently. When you go to access the ``author.username``, it would have to lazy load the author at that
point, and would cause one query per change. With large numbers of changes this could become very slow.

When querying history, Temporal will look for a static method called ``temporal_queryset_options`` and chain
this when building its query. In this case, you would do something like this to tell temporal to use a join
to eager load the user in a single query::

    class UserActivity(Model):
        reason_for_change = TextField()
        author = ForeignKey(User)

        @staticmethod
        def temporal_queryset_options(queryset):
            return queryset.select_related('activity__author')

Using this method, temporal can retrieve the whole timeline of changes using ``n+1`` queries, where ``n`` is
the number of fields being tracked.


Directly querying history
-------------------------

You can query the ``EntityClock`` and ``FieldHistory`` models directly using ORM relationships::

    my_obj.clock.all()
    my_obj.my_field_history.all()

If you need to query history across objects (say, to answer questions like "What were all of the claims with
a status of Pending one week ago?") you can access the ``EntityClock`` and ``FieldHistory`` models from
the ``temporal_options`` class var of a Clocked model::

    # Get all the clock ticks for all entities:
    MyModelClock = MyModel.temporal_options.clock_model
    MyModelClock.objects.all()

    # Find fields/entities that had a value of 'Pending' exactly a week ago:
    ClaimHistory_status = Claim.temporal_options.history_models['status']
    ClaimHistory_status.objects \
        .select_related('entity') \
        .filter(effective__contains=timezone.now() - datetime.timedelta(weeks=1),
                status='Pending')


Unsupported use
---------------

Migrating an existing model to temporal is not currently supported out of the box unless the table is empty.
You would have to manually construct clock and field history instances.

The Django ORM does not provide hooks for bulk updates, so we do not track history when using the queryset
methods ``bulk_create`` or ``update``. ``bulk_create`` would create models without appropriate initial ticks
and is thus disabled for clocked models. ``update`` can still be used, but should only be used to update
untracked fields.
