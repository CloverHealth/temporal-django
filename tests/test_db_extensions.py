from django.db import connection
from django.test import TransactionTestCase
from django.db.utils import IntegrityError

from temporal_django.db_extensions import GistExclusionConstraint

from .models import NoActivityModel


class MigrationTests(TransactionTestCase):
    def test_downgrade_gist_exclusion_constraint(self):
        """Make sure we can downgrade the GiST exclusion constraints that we're adding"""

        # Make sure the exclusion constraint exists

        obj = NoActivityModel(title='abc', num=0)
        obj.save()

        # Now try to create a bad history row
        model = NoActivityModel.temporal_options.history_models['num']
        history_row = model.objects.first()
        bad_history_row = model(
            entity_id=obj.id,
            effective=history_row.effective,
            vclock=history_row.vclock,
            num=1)

        with self.assertRaisesMessage(IntegrityError, 'violates exclusion constraint'):
            bad_history_row.save()

        for constraint in model._meta.indexes:
            if isinstance(constraint, GistExclusionConstraint):
                with connection.schema_editor() as editor:
                    editor.remove_index(model, constraint)

        # Verify that we've successfully removed the constraints by inserting that row:
        bad_history_row.save()
