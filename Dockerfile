FROM python:slim

# use build  variables (ENV variable), copy ENV argument to .env file inside of the container
# copy frontend and backend directories into the container on the same level as the .env file
ARG ENV
COPY ${ENV} .env
COPY ./frontend ./frontend
COPY ./backend ./backend
# tell vite to add /static/ prefix to all static files
ENV VITE_IN_DOCKER="true"

# updates and installs required packages
RUN apt-get update -y && apt-get install pipenv npm nodejs -y

# goes into frontend to build
WORKDIR /frontend
# installed node modules and builds the frontend
RUN npm install && npm run build
# goes into backend to set up backend and gunicorn workers
WORKDIR /backend
# sets python path for pipenv and creates virtual environment
RUN pipenv --python /usr/bin/python3 && pipenv install
# collects static files and creates key club bot group
RUN pipenv run python3 manage.py collectstatic --no-input

# removes unecessary dirs to save space
RUN rm -rf ./dist
WORKDIR /
RUN rm -rf ./frontend

WORKDIR /backend
# creates a gunicorn server bind to 0.0.0.0:8000 with 3 workers
CMD ["pipenv", "run", "gunicorn", "base.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]