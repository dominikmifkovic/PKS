import socket
import struct
import zlib
import time
import random
import os
#flags IAEKNRCS
#
received = []

def to_bin(stream):
	bit_stream = ""
	for byte in stream:
		binary = bin(byte)[2:]
		if len(binary) < 8:
			binary = "0"*(8-len(binary)) + binary
		bit_stream += binary
	#for byte in stream:
	#	bit_stream += bin(byte)[2:].zfill(8)
	return bit_stream

def create_packet(type,flags,data,datalen,fragnum):
	checksum = zlib.crc32(data)
	data = data.decode("Latin-1")
	#data = ''.join(format(ord(i), '08b') for i in data)
	#while len(data) < datalen:
	#	data = "0" + data
	packet = str('{0:032b}'.format(checksum))
	packet += str('{0:04b}'.format(int(type,2)))
	packet += str('{0:08b}'.format(int(flags,2)))
	packet += str('{0:020b}'.format(datalen))
	packet += str('{0:032b}'.format(fragnum))
	packet += data
	packet = bytes(int(packet[i : i + 8],2) for i in range(0, len(packet), 8))
	return packet

def receive_data(data,addr):
	while True:
		data,addr = sock.recvfrom(4096)
		bit_data = to_bin(data)
		if bit_data[32:36] == "0000" and bit_data[36:44] == "00000010":
			sock.sendto(create_packet("0000","01000010",bytes("0","Latin-1"),0,0),(addr))
			break
		elif bit_data[32:36] == "0010" and bit_data[36:44] == "00001000" and int.from_bytes(data[0:4],"big",signed=False) == zlib.crc32(data[12:]):
			received.append(bit_data)
			print ("Received Packet:",int(bit_data[64:96],2)," from",addr)
			#print(bit_data)
			sock.sendto(create_packet("0010","01001000",bytes("0","Latin-1"),int(bit_data[44:64],2),int(bit_data[64:96],2)),(addr)) #type-message flags-N,A
	message = b""
	for bit_stream in received:
		bitmessage = bit_stream[96:]
		message += bytearray([int(bitmessage[i:i+8], 2) for i in range(0, len(bitmessage), 8)])
	print(message)
	print("Message from client: " + message.decode("Latin-1"))
	server_main.receiving = 0		
	received.clear()

def receive_file(data,addr,path):
	while True:
		data,addr = sock.recvfrom(4096)
		bit_data = to_bin(data)
		if bit_data[32:36] == "0000" and bit_data[36:44] == "00000010":
			sock.sendto(create_packet("0000","01000010",bytes("0","Latin-1"),0,0),(addr))
			break
		elif bit_data[32:36] == "0100" and bit_data[36:44] == "00001000" and int.from_bytes(data[0:4],"big",signed=False) == zlib.crc32(data[12:]):
			received.append(bit_data)
			print ("Received Packet:",int(bit_data[64:96],2)," from",addr)
			#print(bit_data)
			sock.sendto(create_packet("0100","01001000",bytes("0","Latin-1"),int(bit_data[44:64],2),int(bit_data[64:96],2)),(addr)) #type-message flags-N,A
		data = ""
	contents_of_file = b""
	for bit_stream in received:
		bitmessage = bit_stream[96:]
		contents_of_file += bytearray([int(bitmessage[i:i+8], 2) for i in range(0, len(bitmessage), 8)])
	with open(path, 'wb') as file:
		file.write(contents_of_file)
	print("File saved at " + os.path.abspath(path))
	server_main.receiving = 0
	received.clear()

def server_main(auto_port):
	global sock
	sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	global hostname
	filename = ""
	hostname=socket.gethostname()
	global server_ip
	global received
	server_ip = socket.gethostbyname(hostname)
	print("This server ip: " + str(server_ip))
	global server_port
	if auto_port == None:
		print("Enter server port:")
		server_port = input()
		server_port = int(server_port)
	else:
		print(auto_port)
		server_port = auto_port
	sock.bind((server_ip,server_port))
	print("Server is listening at port " + str(server_port) + "...")
	client_connected = 0
	swapping = 0
	lost_connection = 0
	ka_active = 0
	exiting = 0
	global client_ip
	client_ip = ""
	server_main.receiving = 0
	while not swapping:
		sock.settimeout(6)
		try:
			data,addr = sock.recvfrom(4096)
			client_ip,buff = addr
			bit_data = to_bin(data)
			if bit_data[32:36] == "0000" and bit_data[36:44] == "10000000":
				sock.sendto(create_packet("0000","11000000",bytes("0","Latin-1"),0,0),(addr))
				print(str(addr) + " connected.")
				client_connected = 1
				ka_active = 1
				lost_connection = 0
			if bit_data[32:36] == "0000" and bit_data[36:44] == "00100000":
				sock.sendto(create_packet("0000","01100000",bytes("0","Latin-1"),0,0),(addr))
				print(str(addr) + " disconnected. Exiting...")
				exiting = 1
			if bit_data[32:36] == "0010" and bit_data[36:44] == "00001000": #type-message flags-N
				ka_active = 0
				if server_main.receiving == 0:
					print("Message incoming! Fragment size: " + str(int(bit_data[44:64],2)))
					server_main.receiving = 1
				receive_data(data,addr)
				ka_active = 1
			if bit_data[32:36] == "0100" and bit_data[36:44] == "00001000": #type-message flags-N
				ka_active = 0
				if server_main.receiving == 0:
					print("File incoming! Fragment size: " + str(int(bit_data[44:64],2)))
					filename = bit_data[96:]
					filename = bytearray([int(filename[i:i+8], 2) for i in range(0, len(filename), 8)])
					filename = filename.decode("Latin-1")
					server_main.receiving = 1
				receive_file(data,addr,filename)
				ka_active = 1
			if bit_data[32:36] == "0000" and bit_data[36:44] == "00010000" and client_connected and not swapping:
				ka_active = 1
				lost_connection=0
				print("Keep alive request arrived from " + str(addr) + ". Sending confirmation...")
				sock.sendto(create_packet("0000","01010000",bytes("0","Latin-1"),0,0),(addr))
			if bit_data[32:36] == "0000" and bit_data[36:44] == "00000001":
				ka_active = 0
				swapping = 1
				
		except:
			if client_connected and ka_active:
				lost_connection += 1
				if lost_connection < 5:
					print("Client " + str(server_ip) + " not responding.")
			if lost_connection == 5:
				print("Client " + str(server_ip) + " lost connection.")
				print("Server is listening at port " + str(server_port) + "...")
				lost_connection = 0
				ka_active = 0
				client_connected = 0
		finally:
			if swapping:
				print("Swap request arrived from " + str(addr) + ". Sending confirmation...")
				sock.sendto(create_packet("0000","01000001",bytes(str("0"),"Latin-1"),0,0),(addr))
				client_connected = 0
				break
			if exiting:
				exit(0)
	sock.close()
	return (client_ip,server_port)
			