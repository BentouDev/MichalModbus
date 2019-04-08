## Dependencies
### Flask webapp
```sh
$ python3 -m pip install flask flask-jsonpify flask-sqlalchemy flask-restful
$ python3 -m pip install flask-bootstrap
$ python3 -m pip install pika
```

### Modbus server
```sh
$ python3 -m pip install pymodbus
$ python3 -m pip install pika
```

## Run
### Web application
```sh
python3 WebApp/server.py
```
### Modbus server
```sh
python3 Modbus/server.py
```
