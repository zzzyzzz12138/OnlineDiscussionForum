from socket import *
import sys
import os

if len(sys.argv) != 3:
    print("\n===== Error usage, python3 UDPClient.py SERVER_IP SERVER_PORT ======\n")
    exit(0)

serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
serverAddress = (serverHost, serverPort)

# available commands: number of parameters
AVAILABLE_COMMANDS = {
    "LST": 0,  # List Threads
    "XIT": 0,  # Exit
    "CRT": 1,  # Create Thread
    "RDT": 1,  # Read Thread
    "RMV": 1,  # Remove Thread
    "MSG": 2,  # Post Message
    "DLT": 2,  # Delete Message
    "UPD": 2,  # Upload File
    "DWN": 2,  # Download File
    "EDT": 3   # Edit Message
}

def display_commands():
    print("\n===== Available Commands =====")
    print("CRT <threadtitle> - Create Thread")
    print("MSG <threadtitle> <message> - Post Message")
    print("DLT <threadtitle> <message number> - Delete Message")
    print("EDT <threadtitle> <message number> <message> - Edit Message")
    print("LST - List Threads")
    print("RDT <threadtitle> - Read thread")
    print("UPD <threadtitle> <filename> - Upload file")
    print("DWN <threadtitle> <filename> - Download file")
    print("RMV <threadtitle> - Remove thread")
    print("XIT - Exit")
    print("================================\n")

def clean_udp_socket(sock):
    sock.setblocking(False)
    try:
        while True:
            sock.recvfrom(1024)
    except BlockingIOError:
        pass
    finally:
        sock.setblocking(True)

def upload_file_to_server(udpSocket, serverAddress, serverHost, parameters):
    try:
        threadtitle, filename = parameters.split()

        if not os.path.isfile(filename):
            print("===== Error: File not found on client side.")
            return

        # send UPD command to server
        udpSocket.sendto(f"UPD {threadtitle} {filename}".encode(), serverAddress)

        # handle the server response, as it may contain multiple lines
        response_lines = []
        while True:
            data, _ = udpSocket.recvfrom(1024)
            if not data:
                break
            response_lines += data.decode().strip().splitlines()
            if any(line.startswith("PORT") or line.startswith("Error") for line in response_lines):
                break

        for line in response_lines:
            print(f"[recv] {line}")

        if any(line.startswith("Error") for line in response_lines):
            return

        port_line = next((line for line in response_lines if line.startswith("PORT")), None)
        if not port_line:
            print("===== Error: Did not receive PORT from server =====")
            return

        tcp_port = int(port_line.split()[1])

        # create TCP socket for file transfer
        tcp_socket = socket(AF_INET, SOCK_STREAM)
        tcp_socket.connect((serverHost, tcp_port))
        with open(filename, "rb") as f:
            while True:
                data = f.read(2048)
                if not data:
                    break
                tcp_socket.sendall(data)
        tcp_socket.close()

        # make sure to receive the ACK from the server
        final_ack, _ = udpSocket.recvfrom(1024)
        print(f"[recv] {final_ack.decode().strip()}")

    except Exception as e:
        print(f"===== Error in UPD client side: {e}")

def download_file_from_server(udpSocket, serverAddress, serverHost, parameters):
    try:
        threadtitle, filename = parameters.split()

        # send DWN command to server
        udpSocket.sendto(f"DWN {threadtitle} {filename}".encode(), serverAddress)

        # similar to UPD, handle the server response as it may contain multiple lines
        response_lines = []
        while True:
            data, _ = udpSocket.recvfrom(1024)
            if not data:
                break
            response_lines += data.decode().strip().splitlines()

            if any(line.startswith("PORT") or line.startswith("Error") for line in response_lines):
                break

        for line in response_lines:
            print(f"[recv] {line}")

        if any(line.startswith("Error") for line in response_lines):
            return

        port_line = next((line for line in response_lines if line.startswith("PORT")), None)
        if not port_line:
            print("===== Error: Did not receive PORT from server =====")
            return

        tcp_port = int(port_line.split()[1])

        # create tcp connection and download the file
        tcp_socket = socket(AF_INET, SOCK_STREAM)
        tcp_socket.connect((serverHost, tcp_port))
        with open(filename, "wb") as f:
            while True:
                data = tcp_socket.recv(2048)
                if not data:
                    break
                f.write(data)
        tcp_socket.close()

        # make sure to receive the ACK from the server
        final_ack, _ = udpSocket.recvfrom(1024)
        print(f"[recv] {final_ack.decode().strip()}")

    except Exception as e:
        print(f"===== Error in DWN client side: {e}")

def use_command(udpSocket, serverAddress):
    while True:
        clean_udp_socket(udpSocket) # Clean the socket to avoid blocking, as UDP is a state-less protocol and may have old data
        display_commands()  # Display all available commands
        user_input = input("Enter your command: ").strip()

        # handle empty input
        if not user_input:
            print("===== Error: Command cannot be empty =====")
            continue

        # spliet command and it parameters
        parts = user_input.split(" ", 1)
        command = parts[0]

        # handle invalid command
        if command not in AVAILABLE_COMMANDS:
            print("===== Error: Invalid command =====")
            continue

        # handle commands by checking the number of their parameters
        expected_parameters = AVAILABLE_COMMANDS[command]
        if expected_parameters == 0:
            parameters = ""
        elif len(parts) < 2:
            print(f"===== Error: '{command}' requires {expected_parameters} parameter(s) =====")
            continue
        else:
            parameters = parts[1]
            # handle special case for MSG and EDT commands, cause MSG and EDT may have space in the message
            if command not in ["MSG", "EDT"] and len(parameters.split()) < expected_parameters:
                print(f"===== Error: '{command}' requires {expected_parameters} parameter(s) =====")
                continue

        # send command to server
        full_message = f"{command} {parameters}".strip()

        if command not in("UPD", "DWN", "RMV", "XIT"):
            udpSocket.sendto(full_message.encode(), serverAddress)

        # handle UPD command separately
        if command == "UPD":
            upload_file_to_server(udpSocket, serverAddress, serverHost, parameters)
            continue

        # handle DWN command separately
        if command == "DWN":
            download_file_from_server(udpSocket, serverAddress, serverHost, parameters)
            continue
        
        # handle RMV command separately
        if command == "RMV":
            try:
                # send command
                udpSocket.sendto(f"{command} {parameters}".encode(), serverAddress)

                # receive response
                response, _ = udpSocket.recvfrom(1024)
                print(f"[recv] {response.decode().strip()}")

            except Exception as e:
                print(f"===== Error in RMV client side: {e}")
            continue

        if command == "XIT":
            try:
                # send XIT command to the server
                udpSocket.sendto("XIT".encode(), serverAddress)
                response, _ = udpSocket.recvfrom(1024)
                print(f"[recv] {response.decode().strip()}")
            except Exception as e:
                print(f"===== Error during logout: {e}")

            # user log out, break the while loop    
            break 

        response, _ = udpSocket.recvfrom(2048)
        print("[server]:\n", response.decode())

def login_process(udpSocket, serverAddress):
    udpSocket.sendto("login".encode(), serverAddress)

    # receive user credentials request
    data, _ = udpSocket.recvfrom(1024)
    receivedMessage = data.decode()

    if receivedMessage == "user credentials request":
        print("[recv] please enter your username")
        username = input("Username: ")
        udpSocket.sendto(username.encode(), serverAddress)

        # receive the login status
        data, _ = udpSocket.recvfrom(1024)
        next_message = data.decode()

        # check if the user is already logged in
        if next_message == "user already logged in":
            print("[recv] this user is logged in already")
            return False

        # user if not logged in
        elif next_message == "password request":
            password = input("Password: ")
            udpSocket.sendto(password.encode(), serverAddress)

            result, _ = udpSocket.recvfrom(1024)
            result = result.decode()

            if result == "login success":
                print("[recv] Login successful")
                return True
            elif result == "login failed":
                print("[recv] wrong password")
                return False

        # new user registration
        elif next_message == "new user":
            print("[recv] new user, please enter your password")
            password = input("New Password: ")
            udpSocket.sendto(password.encode(), serverAddress)

            result, _ = udpSocket.recvfrom(1024)
            result = result.decode()
            if result == "registered and logged in":
                print("[recv] new user registered and logged in")
                return True

    else:
        print("[recv] wrong response:", receivedMessage)
        return False
    
def main():
    # use UDP socket
    udpSocket = socket(AF_INET, SOCK_DGRAM)
    print("===== UDP Client Started =====")

    while True:
        user_input = input(">>>(enter: login) ").strip()

        if user_input.lower() == "login":
            if login_process(udpSocket, serverAddress):
                print("Welcome.")
                use_command(udpSocket, serverAddress)
                break
            else:
                print("Login failed. Try again.")
        else:
            print("Please login first using: login")

    udpSocket.close()
    print("===== Client Exiting =====")

if __name__ == "__main__":
    main()
