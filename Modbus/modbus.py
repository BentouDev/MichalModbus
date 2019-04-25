from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import numpy, struct

def get_modbus(address):
	if not address:
		raise Exception("Unable to connect to modbus when no address!")
	else:
		modbus = ModbusClient(address, port=502, timeout=10)
		if not modbus.connect():
			raise Exception("Unable to connect to modbus, check log for errors")
		return modbus
	return None

class TwojStary:
	REGISTER_CACHE = [0x0]*10
	client = None

	def kurwa_resize(self, new_size):
		if len(self.REGISTER_CACHE) < size:
			return self.REGISTER_CACHE
		result = [0x0]*(size+1)
		for i in len(self.REGISTER_CACHE):
			result[i] = self.REGISTER_CACHE[i]
		return result

	def aquire_modbus(self, address):
		self.client = get_modbus(address)

	def send(self, UNIT):
		print(" [Debug] raw modbus packet " + str(self.REGISTER_CACHE))

		rr = self.client.write_registers(0x0, self.REGISTER_CACHE, unit=UNIT)
		self.client.close()
		self.client = None
		return rr

	def ensure_cache(self, id):
		if id > len(self.REGISTER_CACHE):
			self.REGISTER_CACHE = self.kurwa_resize(id)

	def set_float(self, id, value):
		self.ensure_cache(id + 4)

		encoded_float = struct.pack('f', value)

		for i in range(4):
			self.REGISTER_CACHE[id + i] = encoded_float[i]
			i = i + 1

	def set_byte(self, id, value):
		self.ensure_cache(id)
		if self.REGISTER_CACHE[id] != value:
			print (' [debug] set register [' + str(id) + '] to ' + str(value))
			self.REGISTER_CACHE[id] = value # Set as it is