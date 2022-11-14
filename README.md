# ClowdFlows3 backend

This document describes how to setup ClowdFlows3 backend without Docker. 
For a Docker-based installation please use [this repository](https://github.com/xflows/cf3.ijs.si)
as a template.


Please note that a working ClowdFlows3 installation also requires the frontend which 
is available [here (clowdflows-webapp)](https://github.com/xflows/clowdflows-webapp).



## Prerequisites ##

- python 3.6 or newer (3.7.15 is recommended)


## Steps

### Create a virtual environment ###


```bash
python -m venv cf-venv
```

### Get the code ###

```bash
git clone  https://github.com/xflows/clowdflows-backend.git
```


### Install requirements ###

```bash
cd clowdflows-backend
pip install -r requirements.txt
```


### Configure project ###

Edit `clowdflows-backend/mothra/settings.py` if needed. Note that by default, SQLite is used.
It is advised to replace it with Postgres for better performance. 
Find and modify Django's `DATABASES` variable in this file as described in [this guide](https://docs.djangoproject.com/en/1.11/ref/databases/).


### Prepare the  database

```bash
source cf-venv/bin/activate
python manage.py migrate
python manage.py import_all
python manage.py collectstatic --noinput
python manage.py createsuperuser
```


### Run the development server ##

```bash
python manage.py runserver
```

If the frontend server is already running with default configuration, you can open [http://localhost:8080/](http://localhost:8080/) and log in using admin credentials.


### Extra: Enable workflow packages ###

Install any extra ClowdFlows3 packages and add corresponding entries into the `packages/packages.py`. 
