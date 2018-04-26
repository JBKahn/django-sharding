from setuptools import setup, find_packages

version = '3.0.0'


def get_requirements(file_path):
    with open(file_path) as f:
        return [line for line in f if line and not line.startswith('-')]


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
    install_requires=get_requirements('requirements/common.txt') + ["django>=1.8,<3.0.0"],
    tests_require=get_requirements('requirements/development.txt'),
    license="BSD",
    zip_safe=False,
    keywords='django shard sharding library',
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ],
    test_suite='runtests.run_tests',
)
