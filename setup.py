from setuptools import setup, find_packages

version = '1.0.0'


setup(
    name='django_sharding',
    version=version,
    description="""A sharding app to include in your project so that you can shard your data.""",
    long_description=open('README.md').read(),
    author='JBKahn',
    author_email='josephbkahn@gmail.com',
    url='https://github.com/JBKahn/django-sharding',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['Django>=1.8', 'dj-database-url==0.4.1'],
    tests_require=['psycopg2==2.6.2', 'mysqlclient==1.3.7', 'mock==2.0.0', 'django_nose==1.4.4', 'tox==2.3.1'],
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
    ],
    test_suite='runtests.run_tests',
)
