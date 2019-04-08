FROM python:3
MAINTAINER Jakub Bentkowski <bentkowski.jakub@gmail.com>

RUN pip install flask flask-jsonpify flask-sqlalchemy flask-restful
RUN pip install flask-bootstrap
RUN pip install pika

COPY ./WebApp /app
WORKDIR /app

ENTRYPOINT ["python"]
CMD ["server.py"]