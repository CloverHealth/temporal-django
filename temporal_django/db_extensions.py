"""
Temporal relies on some postgres features that are not supported by Django out of the box

This file defines the new index and constraint types that we need.
"""
from django.db.models import Index


class GistIndex(Index):
    suffix = 'gist'
    max_name_length = 63

    def create_sql(self, model, schema_editor):
        return super(GistIndex, self).create_sql(model, schema_editor, using=' USING gist')


class GistExclusionConstraint(Index):
    """
    Generate a GiST exclusion constraint by lying to Django and saying that we're creating an index

    TODO: Figure out if there's a less hacky way to do this
          (but all things considered this doesn't seem so bad)
    """

    suffix = 'excl'
    max_name_length = 63

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_sql(self, model, schema_editor):
        add_constraint_sql = 'ALTER TABLE ONLY %s ADD CONSTRAINT %s EXCLUDE USING gist (%s);'
        table_name = model._meta.db_table
        return add_constraint_sql % (table_name, self.name, self.fields[0])

    def remove_sql(self, model, schema_editor):
        drop_constraint_sql = 'ALTER TABLE %s DROP CONSTRAINT %s;'
        table_name = model._meta.db_table
        return drop_constraint_sql % (table_name, self.name)
