from setuptools import setup, find_packages

from django_sharding import VERSION

with open('./requirements/common.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.strip().startswith('-r')]

with open('./requirements/development.txt') as f:
    test_requirements = [line.strip() for line in f if line.strip() and not line.strip().startswith('-r')]

setup(
    name='django_sharding',
    version=VERSION,
    description="""A sharding app to include in your project so that you can shard your data.""",
    long_description=open('README.md').read(),
    author='JBKahn',
    author_email='josephbkahn@gmail.com',
    url='https://github.com/JBKahn/django-sharding',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    tests_require=test_requirements,
    license="BSD",
    zip_safe=False,
    keywords='django shard sharding library',
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
        'Programming Language :: Python :: 3.6'
    ],
    test_suite='runtests.run_tests',
)
