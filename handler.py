import client
import server


def main():
    prev_server_ip = ""
    prev_server_port = "" 
    print("1. - Client\n2. - Server")
    mode = input()
    match mode:
        case "1":
            addr = client.client_main(None,None)
            prev_server_ip,prev_server_port = addr
        case "2":
            addr = server.server_main(None)
            prev_server_ip,prev_server_port = addr

        case other:
            print("Incorrect choice")
            exit(0)
    while True:
        if mode == "1":
            mode = "2"
            addr = server.server_main(prev_server_port)
            prev_server_ip,prev_server_port = addr

        if mode == "2":
            mode = "1"
            addr = client.client_main(prev_server_ip,prev_server_port)
            prev_server_ip,prev_server_port = addr
main()