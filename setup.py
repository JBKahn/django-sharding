from setuptools import setup, find_packages

version = '0.0.1'


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
    install_requires=['Django>=1.8'],
    tests_require=[''],
    license="BSD",
    zip_safe=False,
    keywords='django shard sharding library',
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='runtests.run_tests',
)
