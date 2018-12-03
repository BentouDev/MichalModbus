## Dependencies
```sh
$ python3 -m pip install pymodbus
$ python3 -m pip install flask flask-jsonpify flask-sqlalchemy flask-restful
$ python3 -m pip install blynk-library-python
$ python3 -m pip install flask-bootstrap
```

## Run
```sh
python3 server.py
```

## Usage
```
# try to connect to modbus server at given ip address
/connect?address=192.168.0.1 
```

```
# disconnect from current modbus server
/disconnect
```
