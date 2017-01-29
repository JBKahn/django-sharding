FROM python:3.6

MAINTAINER Joseph Kahn

WORKDIR /code
ADD . /code

RUN pip install -r ./requirements.txt

CMD ["python", "runtests.py"]
