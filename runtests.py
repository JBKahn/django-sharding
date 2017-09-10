import os
import sys

try:
    import django
    from django.conf import settings
    from django.test.utils import get_runner
except ImportError:
    import traceback
    traceback.print_exc()
    raise ImportError("To fix this error, run: pip install -r requirements-test.txt")


sys.path.append(os.path.dirname(__file__))
django.setup()


def run_tests(*test_args):
    if not test_args:
        test_args = ['tests']

    from django.core.management import call_command

    call_command('makemigrations', 'tests')

    # Run tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    location = (os.environ.get('TRAVIS') and "postgres and mysql") or "sqlite"
    print("I am running tests on {}".format(location))  # noqa

    failures = test_runner.run_tests(test_args, interactive=False)

    if failures:
        sys.exit(bool(failures))

    sys.exit(0)


if __name__ == '__main__':
    run_tests(*sys.argv[1:])
