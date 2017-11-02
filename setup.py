"""Setup script for temporal-django"""

import sys
import setuptools

SETUP_DEPENDENCIES = []
if {'pytest', 'test', 'ptr'}.intersection(sys.argv):
    SETUP_DEPENDENCIES.append('pytest-runner')

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Framework :: Django :: 1.11',
    'Framework :: Django',
    'Intended Audience :: Developers',
    'Intended Audience :: Financial and Insurance Industry',
    'Intended Audience :: Healthcare Industry',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Database :: Front-Ends',
    'Topic :: Database',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development',
]

setuptools.setup(
    name='temporal-django',
    version='0.0.1',
    zip_safe=False,
    description='Temporal models for Django ORM',
    long_description='file: README.rst',
    author='Clover Health Engineering',
    author_email='engineering@cloverhealth.com',
    url='https://github.com/cloverhealth/temporal-django',
    packages=['temporal_django'],
    license='BSD',
    platforms=['any'],
    keywords='django postgresql orm temporal',
    classifiers=CLASSIFIERS,
    python_requires='>=3.5',
    install_requires=[
        'psycopg2>=2.6.2',
        'Django>=1.11.0',
        'typing>=3.5.2,<4.0.0;python_version<"3.5"'
    ],
    setup_requires=SETUP_DEPENDENCIES,
    test_suite='tests.runtests.run_tests',
)
