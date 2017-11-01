"""
A standalone test runner script, configuring the minimum settings
required for tests to execute.
"""

import sys

import testing.postgresql


def _monkeypatch_create_btree_gist():
    """Monkeypatch migrations to install a prerequisite extension before they run"""
    from django.core.management.commands.migrate import Command as MigrateCommand
    sync_apps = MigrateCommand.sync_apps

    def patched_sync_apps(self, connection, *args):
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS btree_gist;')
        return sync_apps(self, connection, *args)

    MigrateCommand.sync_apps = patched_sync_apps


def run_tests():
    with testing.postgresql.Postgresql() as postgresql:
        # Minimum settings required for the app's tests.
        settings_dict = {
            'INSTALLED_APPS': ('tests',),
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': postgresql.dsn()['database'],
                    'USER': postgresql.dsn()['user'],
                    'HOST': postgresql.dsn()['host'],
                    'PORT': postgresql.dsn()['port'],
                },
            },
        }

        # Making Django run this way is a two-step process. First, call
        # settings.configure() to give Django settings to work with:
        from django.conf import settings
        settings.configure(**settings_dict)

        # Then, call django.setup() to initialize the application cache
        # and other bits:
        import django
        if hasattr(django, 'setup'):
            django.setup()

        # Now we instantiate a test runner...
        from django.test.utils import get_runner
        TestRunner = get_runner(settings)

        _monkeypatch_create_btree_gist()

        # And then we run tests and return the results.
        test_runner = TestRunner(verbosity=1, interactive=True)
        failures = test_runner.run_tests(['tests'])

    sys.exit(bool(failures))


if __name__ == '__main__':
    run_tests()
