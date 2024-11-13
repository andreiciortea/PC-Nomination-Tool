# PC-Nomination-Tool

This repository hosts a [Django](https://www.djangoproject.com/) project that implements a
programme committee (PC) nomination tool. This website allows users to nominate PC members, checking in
the background that the nominated individuals have not already been nominated, so as to avoid the usual
overhead of finding duplicates in long lists of nominations.

The tool was originally developed for ECAI-2024, the 27th European Conference on Artificial Intelligence, where it was successfully used to assemble a list of over 5,000 nominees.

## Presentation of the Tool

### Nominating Potential PC Members

This tool is used to nominate PC members. After entering their name, users arrive at this page:

![Screenshot of the Nomination Page](readme_imgs/nom_nomination.png?raw=true)

Using this form, users can enter the details of a person. These are matched
against the database in the background, warning the user if they are potentially entering the details
of someone who has already been nominated.

![Screenshot of the Nomination Page with Duplicates Showing](readme_imgs/nom_duplicates.png?raw=true)

The identity of a person is linked to their DBLP page URL (as the other details need not be unique).
When entering the name of someone, the DBLP API is queried to suggest pre-filled information:

![Screenshot of the Nomination Page with DBLP Results](readme_imgs/nom_DBLP.png?raw=true)

### Administrating the Nominations

On the page `manage`, several admin tools are proposed.

- You can import nominations as a CSV file.
- You can export the nomination database as a CSV file.
- You can check whether there are potential duplicates: database entries representing the same person
but with different email addresses.
- You can explore in a big table with all nominated individuals.

This page is only accessible to users that are logged in via Django. You typically only want admins to have a Django account for this project.

## Development/Deployment

This project is ready to be deployed on a server by anyone who has basic knowledge of how to deploy
Django applications. In the following we present few steps to get started.

### Local Settings

A local setting file `confutils\local_settings.py` is required for the website to work. It should
look like this:

```
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret! And update this fake one!
SECRET_KEY = 'secret'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# For production, update with the actual URL host
# ALLOWED_HOSTS = [""]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'confutils.db'),
    },
}

STATIC_ROOT = "static/"

FILE_UPLOAD_MAX_MEMORY_SIZE = 40 * 1024 * 1024
````

### Python Setup

Next, install the required python libraries. Additional libraries may be needed depending on your
database engine.

```shell
pip install -r requirements.txt
```

### Database Setup

To create the databases, run the following commands:

```shell
python manage.py makemigrations
python manage.py migrate
python manage.py initialise_db
```

### Super Admin

Create a super admin to have access to the admin pages:

```shell
python manage.py createsuperuser
```

### Serve the Website Locally

To serve the website on your local machine run:

```
python manage.py runserver
```

### Server Deployment

Follow any good Django deployment tutorial to deploy this project on a server.
