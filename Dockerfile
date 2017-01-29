FROM python:3.6.0-alpine

MAINTAINER Joseph Kahn

WORKDIR /code
ADD . /code

RUN apk add --no-cache --virtual .pg-drivers \
    gcc \
    musl-dev \
    linux-headers \
    postgresql-client \
    postgresql-dev \
    mariadb-client \
    mariadb-dev

RUN pip install -r ./requirements.txt

CMD ["python", "runtests.py"]
