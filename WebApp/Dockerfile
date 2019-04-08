FROM library/ubuntu:artful
MAINTAINER Jakub Bentkowski <bentkowski.jakub@gmail.com>

RUN apt-get update \
    && apt-get install -y \
    git \
    python-pip \
    python-dev \
    build-essential 

RUN git clone https://github.com/BentouDev/MichalModbus.git src
RUN pip install flask flask-jsonpify flask-sqlalchemy flask-restful
RUN pip install flask-bootstrap
RUN pip install pika

ENTRYPOINT ["src/WebApp/server.py"]