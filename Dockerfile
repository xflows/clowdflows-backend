FROM python:3.7-alpine

# set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# set work directory
WORKDIR /usr/src/app

RUN apk add --no-cache \
            # Pillow deps
            jpeg-dev zlib-dev \
            # Psycopg2 deps
            postgresql-dev \
            openssl-dev libffi-dev

COPY ./Pipfile /usr/src/app/Pipfile
COPY ./Pipfile.lock /usr/src/app/Pipfile.lock

RUN apk add --no-cache --virtual .build-deps build-base linux-headers && \
                       pip install --upgrade pip && \
                       pip install pipenv && \
                       pip install psycopg2 && \
                       pipenv install --system --dev && \
                       apk del .build-deps

COPY . /usr/src/app/

ARG CI_COMMIT_SHORT_SHA

ENV COMMIT_SHA=${CI_COMMIT_SHORT_SHA}

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
