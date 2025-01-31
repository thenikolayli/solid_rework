# build stage
FROM python:slim AS build

# copies necessary files for build, sets VITE_IN_DOCKER to true to let vite
# know to add /static/ prefix to all file locations
# sets up build .env variables
ARG ENV
COPY ${ENV} .env
COPY ./frontend /frontend
COPY ./backend /backend
ENV VITE_IN_DOCKER="true"

# updates and installs required packages
RUN apt-get update -y && apt-get install pipenv npm -y

# installs node modules and builds the frontend assets
WORKDIR /frontend
RUN npm install && npm run build

# creates and installes virtual environment, collects static
# sets python path for pipenv and creates virtual environment within backend directory
WORKDIR /backend
RUN pipenv --python /usr/bin/python3 && pipenv install --ignore-pipfile
RUN pipenv run python3 manage.py collectstatic --no-input

# main stage
FROM python:slim AS main

# copies necessary files for main and sets PATH variable (so it knows where to find installed python dependencies)
COPY --from=build /backend /backend

# builds env
WORKDIR /backend
RUN apt-get update -y && apt-get install pipenv -y
RUN pipenv --python /usr/bin/python3 && pipenv install --ignore-pipfile

# creates a gunicorn server bind to 0.0.0.0:8000 with 3 workers
CMD ["pipenv", "run", "gunicorn", "base.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]