import os
import sys


def run_tests(*test_args):
    if not test_args:
        test_args = ['tests']

    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'

    import django
    from django.conf import settings
    from django.core.management import call_command
    from django.test.utils import get_runner

    django.setup()

    call_command('makemigrations', 'tests')

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(test_args)
    sys.exit(bool(failures))


if __name__ == '__main__':
    run_tests(*sys.argv[1:])
