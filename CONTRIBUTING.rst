Testing and Development
-----------------------

This package uses `Tox <https://tox.readthedocs.io/en/latest/>`_ to run tests on
multiple versions of Python.

Setup
~~~~~

To set up your development environment, you'll need to install a few things.
For Python version management, we use `pyenv-virtualenv <https://github.com/pyenv/pyenv-virtualenv>`_.
Follow the installation instructions there, and then in the *root directory* of
this repo run:

.. code-block:: sh

    # Install all the Python versions this package supports. This will take some
    # time.
    pyenv install 3.5.3
    pyenv install 3.6.3

    pyenv local 3.6.3 3.5.3

    # Install the development dependencies
    pip3 install -Ur dev-requirements.txt

Running the Tests
~~~~~~~~~~~~~~~~~

To run the unit tests for all supported versions of Python, run ``tox``. If you
made a change to the package requirements (in ``setup.py`` or ``test_requirements.txt``)
then you'll need to rebuild the environment. Use ``tox -r`` to rebuild them and
run the tests.

Updating Version Numbers
~~~~~~~~~~~~~~~~~~~~~~~~

Once development is done, as your *last commit* on the branch you'll want to
change the version number and create a tag for deployment. Please do this via
the ``bumpversion`` command. More information on ``bumpversion`` and its usage
can be found `here <https://pypi.python.org/pypi/bumpversion>`_, but in most
cases you'll run one of the following commands. Assuming the current version is
1.2.3:

.. code-block:: sh

    # Change the version to 1.2.4
    bumpversion patch

    # Change the version to 1.3.0
    bumpversion minor

    # Change the version to 2.0.0
    bumpversion major
