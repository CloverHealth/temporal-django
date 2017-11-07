# Setup

From within the example directory, set up a database and virtual environment.

```sh
createdb temporal_example_project
psql temporal_example_project -c 'CREATE EXTENSION IF NOT EXISTS btree_gist;'
pyenv virtualenv 3.6.2 temporal-django-example
pyenv local temporal-django-example
pip install -r requirements.txt
./manage.py migrate
```

Run the server

```py
./manage.py runserver
```
