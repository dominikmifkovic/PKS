import socket
import zlib
import time
import os
import random
from threading import Thread

def to_bin(stream):
	bit_stream = ""
	for byte in stream:
		binary = bin(byte)[2:]
		if len(binary) < 8:
			binary = "0"*(8-len(binary)) + binary
		bit_stream += binary
	return bit_stream

def keepalive():
    repeats = 0
    while not client_main.disconnected:
        if client_main.disconnected == 1:
            return
        sock.settimeout(1)
        if not client_main.disconnected and not sending_data:
            sock.sendto(create_packet("0000","00010000",bytes("0","Latin-1"),0,0),(server_ip,server_port))
        if repeats == 0 and not client_main.disconnected and not sending_data and typing == 0:
            print("Keep alive request sent to " + str(server_ip) + " at port " + str(server_port) + ". Awaiting confirmation...")
        try:
            if not client_main.disconnected and not sending_data:
                keep,buff = sock.recvfrom(1024)
                bit_data = to_bin(keep)
                if bit_data[32:36] == "0000" and bit_data[36:44] == "01010000":
                    repeats = 0
                    if typing == 0:
                        print("Keep alive request successful.")    
        except:
            if repeats > 0 and repeats < 5 and not client_main.disconnected and not sending_data and typing == 0:
                print("Keep alive request sent again to " + str(server_ip) +  " at port " + str(server_port) + " (" + str(repeats) + "). Awaiting confirmation...")
            if repeats == 5 and not client_main.disconnected and not sending_data:
                print("Connection lost.")
                client_main.disconnected = 1
                return
            repeats += 1
        if client_main.disconnected == 1:
            return
        time.sleep(5)
    return


def connect_to_server():
    repeats = 0
    while True:
        sock.settimeout(1)
        sock.sendto(create_packet("0000","10000000",bytes("0","Latin-1"),0,0),(server_ip,server_port))
        if repeats == 0:
            print("Connection request sent to " + str(server_ip) + " at port " + str(server_port) + ". Awaiting confirmation...")
            time.sleep(5)
        try:
            init,buff = sock.recvfrom(1024)
            if  to_bin(init)[32:36] == "0000" and to_bin(init)[36:44] == "11000000":
                print("Connection successful\n")
                return 1
        except:
            if repeats > 0 and repeats < 5:
                print("Connection request sent again to " + str(server_ip) + " at port " + str(server_port) + " (" + str(repeats+1) + "). Awaiting confirmation...")
                time.sleep(5)
            if repeats == 5:
                print("Connection unsuccessful.")
                return 0
            repeats += 1
       

def create_packet(type,flags,data,datalen,fragnum):
    checksum = zlib.crc32(data)
    if random.randint(1,10000) == 1:
        checksum +=1
        pass
    data = data.decode("Latin-1")
    data = ''.join(format(ord(i), '08b') for i in data)
    packet = str('{0:032b}'.format(checksum))
    packet += str('{0:04b}'.format(int(type,2)))
    packet += str('{0:08b}'.format(int(flags,2)))
    packet += str('{0:020b}'.format(datalen))
    packet += str('{0:032b}'.format(fragnum))
    packet += data
    packet = bytes(int(packet[i : i + 8],2) for i in range(0, len(packet), 8))
    return packet

def client_mode():
    global sending_data
    global typing
    typing = 0
    sending_data = 0
    if connect_to_server():
        thread = Thread(target=keepalive)
        thread.start()
        while True:
            if client_main.disconnected == 1:
                break 
            print("1. - Send message\n2. - Send file\n3. - Swap modes\n4 - Disconnect and exit")
            mode = input()
            if client_main.disconnected == 1:
                break
            match mode:
                case "1":
                    typing = 1
                    print("Enter message: ")
                    data = input()
                    print("Specify fragment size in bytes (min 1 / max 1400): ")
                    fragsize = input()
                    fragsize = int(fragsize)
                    sending_data = 1
                    data = bytes(data,"Latin-1")
                    split_data = [data[i:i + fragsize] for i in range(0, len(data), fragsize)]
                    x = 0
                    packet = create_packet("0010","00001000",bytes(str(len(split_data)),"Latin-1"),fragsize,x)
                    sock.sendto(packet,(server_ip,server_port))
                    for fragment in split_data:
                        #flags IAEKNRCS
                        x+=1
                        print(fragment)
                        packet = create_packet("0010","00001000",fragment,fragsize,x)
                        sock.sendto(packet,(server_ip,server_port))
                        print("Sending packet " + str(x))
                        while True:
                            sock.settimeout(5)
                            try:  
                                received,buffer = sock.recvfrom(1024)
                                if to_bin(received)[36:44] == "01001000" and int(to_bin(received)[64:96],2) == x:
                                    break
                            except:
                                print("Sending packet " + str(x) + " again")
                                packet = create_packet("0010","00001000",fragment,fragsize,x)
                                sock.sendto(packet,(server_ip,server_port)) 
                        received = ""                    
                    sock.sendto(create_packet("0000","00000010",bytes("0","Latin-1"),0,0),(server_ip,server_port))
                    sending_data = 0
                    typing = 0


                case "2":
                    typing = 1
                    print("Enter path to the file: ")
                    path = input()
                    path = os.path.basename(path)
                    data = ""
                    try:
                        with open(path, 'rb') as file:
                            data = file.read()
                    except:
                        print("File not found.")
                        continue
                    print("Specify fragment size in bytes (min 1 / max 1400): ")
                    fragsize = input()
                    fragsize = int(fragsize)
                    sending_data = 1
                    #data = bytes(data,"Latin-1")
                    split_data = [data[i:i + fragsize] for i in range(0, len(data), fragsize)]
                    x = 0
                    packet = create_packet("0100","00001000",bytes(path,"Latin-1"),fragsize,x)
                    sock.sendto(packet,(server_ip,server_port))
                    print("Sending file " + os.path.abspath(path))
                    for fragment in split_data:
                        #flags IAEKNRCS
                        x+=1
                        packet = create_packet("0100","00001000",fragment,fragsize,x)
                        sock.sendto(packet,(server_ip,server_port))
                        print("Sending packet " + str(x))
                        while True:
                            sock.settimeout(5)
                            try:  
                                received,buffer = sock.recvfrom(1024)
                                if to_bin(received)[36:44] == "01001000" and int(to_bin(received)[64:96],2) == x:
                                    break
                            except:
                                print("Sending packet " + str(x) + " again")
                                sock.sendto(create_packet("0100","00001000",fragment,fragsize,x),(server_ip,server_port))
                        received = ""
                    sock.sendto(create_packet("0000","00000010",bytes("0","Latin-1"),0,0),(server_ip,server_port))
                    sending_data = 0
                    typing = 0

                case"3":
                    packet = create_packet("0000","00000001",bytes(str("0"),"Latin-1"),0,0)
                    sock.sendto(packet,(server_ip,server_port))
                    print("Request to swap sent successfuly.")
                    sock.settimeout(5)

                    try:  
                        received,buffer = sock.recvfrom(1024)
                        if to_bin(received)[36:44] == "01000001":
                            print("Request to swap successful.")
                            
                        else:
                            print("Sending Request to swap again")
                            sock.sendto(packet,(server_ip,server_port)) 
                    except:
                        pass
                    finally:
                        client_main.disconnected = 1
                        return

                case "4":
                    client_main.disconnected = 1
                    sock.sendto(create_packet("0000","00100000",bytes(str("0"),"Latin-1"),0,0),(server_ip,server_port))
                    print("Disconnected from " + str(server_ip))       
                    exit(0)
    client_main(auto_ip_temp,auto_port_temp)

            

def client_main(auto_ip,auto_port):
    global auto_ip_temp, auto_port_temp
    auto_ip_temp = auto_ip
    auto_port_temp = auto_port
    global sock 
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    global server_ip
    global server_port
    if auto_ip==None:
        print("Server ip:")
        server_ip = input()
    else:
        server_ip = auto_ip
    if auto_port == None:
        print("Server port:") 
        server_port = input()
        server_port = int(server_port)
    else:
        server_port = auto_port
    global server_address
    server_address = server_ip,server_port
    client_main.disconnected = 0
    client_mode()
    return (server_ip,server_port)