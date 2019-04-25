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
	request = None

	def cache_request(self, req):
		self.request = req

	def force_close(self):
		if self.client != None:
			self.client.close()

	def resize_buffer(self, size):
		if len(self.REGISTER_CACHE) > size:
			return self.REGISTER_CACHE
		result = [0x0]*(size+1)
		for i in range(len(self.REGISTER_CACHE)):
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
		if id >= len(self.REGISTER_CACHE):
			self.REGISTER_CACHE = self.resize_buffer(id)

	def set_float(self, id, value):
		self.ensure_cache(id + 4)

		print(' [info] Attempt to sent float ' + str(value))

		encoded_float = struct.pack('f', value)
		if len(encoded_float) < 4:
			print (' [error] Float byte format failed for: ' + str(value))
		else:
			print ( ' [info] Packed float: ' + encoded_float)
			decoded_float = struct.unpack('hh', encoded_float) # as two shorts
			for i in range(2):
				self.REGISTER_CACHE[id + i] = decoded_float[i]
				i = i + 1

	def set_byte(self, id, value):
		self.ensure_cache(id)
		print (' [sanity] len: ' + str(len(self.REGISTER_CACHE)) + " vs: " + str(id))
		if self.REGISTER_CACHE[id] != value:
			print (' [debug] set register [' + str(id) + '] to ' + str(value))
			self.REGISTER_CACHE[id] = value # Set as it is