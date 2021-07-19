FROM python:3.7-stretch

RUN apt update && apt install -y netcat

# set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# set work directory
WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/requirements.txt

RUN pip install --upgrade pip && \
    pip install "psycopg2==2.8.6" && \
    pip install -r requirements.txt

COPY . /usr/src/app/

ARG CI_COMMIT_SHORT_SHA

ENV COMMIT_SHA=${CI_COMMIT_SHORT_SHA}

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
