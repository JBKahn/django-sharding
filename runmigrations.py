from runtests import *  # noqa


def run_migrations(*test_args):
    from django.core.management import call_command

    call_command('makemigrations', 'tests')

if __name__ == '__main__':
    run_migrations()
