from socket import *
import threading
import random
import os
import time

serverHost = "127.0.0.1"

import sys
if len(sys.argv) != 2:
    print("\n===== Usage: python3 hybrid_server.py SERVER_PORT ======\n")
    exit(0)
udpPort = int(sys.argv[1])
serverAddress = (serverHost, udpPort)

CREDENTIALS_FILE = "credentials.txt"
activeUsers = {} 

# read credentials from file
def read_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    with open(CREDENTIALS_FILE, 'r') as f:
        lines = f.readlines()
    return dict(line.strip().split(' ') for line in lines if line.strip())

def process_login(client_addr, udp_sock):
    try:
        udp_sock.sendto("user credentials request".encode(), client_addr)

        # reveive username
        username_data, _ = udp_sock.recvfrom(1024)
        username = username_data.decode().strip()

        # check if username is already logged in, if so, send a message and return
        #if client_addr in activeUsers: # only check client is not enough as it will not stop another user try to login with the same unsername
        if username in activeUsers.values():
            udp_sock.sendto("user already logged in".encode(), client_addr)
            return
        
        credentials = read_credentials()

        # if username exists in the credentials file, check password
        if username in credentials:
            udp_sock.sendto("password request".encode(), client_addr)
            password_data, _ = udp_sock.recvfrom(1024)
            password = password_data.decode().strip()

            if password == credentials[username]:
                # if password is correct, add user to activeUsers
                activeUsers[client_addr] = username
                udp_sock.sendto("login success".encode(), client_addr)
                print(f"[login] User {username} logged in from {client_addr}")
            else:
                # wrong password
                udp_sock.sendto("login failed".encode(), client_addr)

        # new user registration
        else:
            udp_sock.sendto("new user".encode(), client_addr)
            password_data, _ = udp_sock.recvfrom(1024)
            password = password_data.decode().strip()

            with open(CREDENTIALS_FILE, 'a') as f:
                f.write(f"{username} {password}\n")
            activeUsers[client_addr] = username
            udp_sock.sendto("registered and logged in".encode(), client_addr)
            print(f"[register] New user {username} registered and logged in")

    except Exception as e:
        print(f"===== login process error: {e}")

def process_CRT(message, udp_socket, client_addr):
    try:
        parts = message.strip().split(" ")  # split command and threadtitle
        if len(parts) != 2:
            # send error message to client
            udp_socket.sendto("Error: Invalid CRT format.".encode(), client_addr)
            return

        threadTitle = parts[1]

        #print("[debug] activeUsers:", activeUsers)

        # read the username from activeUsers
        username = activeUsers.get(client_addr)
        if not username:
            udp_socket.sendto("Error: User not recognized.".encode(), client_addr)
            return

        # check if threadtitle already exists
        if os.path.exists(threadTitle):
            udp_socket.sendto(f"Thread {threadTitle} already exists.".encode(), client_addr)
        
        # create a new thread
        else:
            # The first line of the thread file should be the username of the creator
            with open(threadTitle, "w") as f:
                f.write(f"{username}\n")

            udp_socket.sendto(f"Thread {threadTitle} created.".encode(), client_addr)
            print(f"[CRT] Thread '{threadTitle}' created by {username}")

    except Exception as e:
        print(f"===== Error in CRT: {e}")  

def process_MSG(message, udp_socket, client_addr):
    try:
        parts = message.strip().split(" ", 2)   # split command, threadtitle and message
        if len(parts) < 3:
            # send error message to client
            udp_socket.sendto("Error: Invalid MSG format.".encode(), client_addr)
            return

        threadTitle = parts[1]
        message_content = parts[2]

        # read the username from activeUsers
        username = activeUsers.get(client_addr)
        if not username:
            udp_socket.sendto("Error: User not recognized.".encode(), client_addr)
            return

        # check if threadtitle exists
        if not os.path.exists(threadTitle):
            udp_socket.sendto(f"Error: Thread {threadTitle} does not exist.".encode(), client_addr)
            return

        # skip the first line and get the message number
        with open(threadTitle, "r") as f:
            lines = f.readlines()
        message_number = len(lines)

        # write the message to the thread file
        with open(threadTitle, "a") as f:
            f.write(f"{message_number} {username}: {message_content}\n")

        udp_socket.sendto(f"Message posted to thread {threadTitle}.".encode(), client_addr)
        print(f"[MSG] {username} posted to {threadTitle}: {message_content}")

    except Exception as e:
        print(f"Error in MSG: {e}")    

def process_DLT(message, udp_socket, client_addr):
    try:
        parts = message.strip().split() # split command, threadtitle and message number
        if len(parts) != 3:
            # send error message to client
            udp_socket.sendto("Error: Invalid DLT format.".encode(), client_addr)
            return

        threadTitle = parts[1]
        message_number_str = parts[2] # check if message number is an integer
        
        # throw error if user input is not an integer
        if not message_number_str.isdigit():
            udp_socket.sendto("Error: Message number must be a integer.".encode(), client_addr)
            return

        message_number = int(message_number_str)

        # read the username from activeUsers
        username = activeUsers.get(client_addr)
        if not username:
            udp_socket.sendto("Error: User not recognized.".encode(), client_addr)
            return

        # check if threadtitle exists
        if not os.path.exists(threadTitle):
            udp_socket.sendto(f"Error: Thread {threadTitle} does not exist.".encode(), client_addr)
            return

        with open(threadTitle, "r") as f:
            lines = f.readlines()

        # check if message_number is valid
        if message_number <= 0 or message_number >= len(lines):
            udp_socket.sendto("Error: Invalid message number.".encode(), client_addr)
            return

        target_line = lines[message_number]

        # check if the message belongs to the current user
        expected_prefix = f"{message_number} {username}:"
        if not target_line.startswith(expected_prefix):
            udp_socket.sendto("Error: You can only delete your own message.".encode(), client_addr)
            return

        # delete the line
        del lines[message_number]

        # shift up all the remaining messages
        for i in range(1, len(lines)):
            if i >= message_number:
                content = lines[i].split(" ", 1)[1]
                lines[i] = f"{i} {content}"

        with open(threadTitle, "w") as f:
            f.writelines(lines)

        udp_socket.sendto(f"Message {message_number} deleted from thread '{threadTitle}'.".encode(), client_addr)
        print(f"[DLT] Message {message_number} deleted by {username} in thread '{threadTitle}'")

    except Exception as e:
        print(f"Error in DLT: {e}") 

def process_EDT(message, udp_socket, client_addr):
    try:
        parts = message.strip().split(" ", 3)   # split command, threadtitle, message number and new content
        if len(parts) < 4:
            # send error message to client
            udp_socket.sendto("Error: Invalid EDT format.".encode(), client_addr)
            return

        threadTitle = parts[1]
        message_number_str = parts[2]
        new_content = parts[3]

        # check if message number is an integer
        if not message_number_str.isdigit():
            udp_socket.sendto("Error: Message number must be an integer.".encode(), client_addr)
            return
        message_number = int(message_number_str)

        # read the username from activeUsers
        username = activeUsers.get(client_addr)
        if not username:
            udp_socket.sendto("Error: User not recognized.".encode(), client_addr)
            return

        # check if threadtitle exists
        if not os.path.exists(threadTitle):
            udp_socket.sendto(f"Error: Thread '{threadTitle}' does not exist.".encode(), client_addr)
            return

        with open(threadTitle, "r") as f:
            lines = f.readlines()

        # check if message_number is valid
        if message_number <= 0 or message_number >= len(lines):
            udp_socket.sendto("Error: Invalid message number.".encode(), client_addr)
            return

        original_line = lines[message_number].strip()

        # check if the message belongs to the current user
        expected_prefix = f"{message_number} {username}:"
        if not original_line.startswith(expected_prefix):
            udp_socket.sendto("Error: You can only edit your own message.".encode(), client_addr)
            return

        # edit the line
        new_line = f"{message_number} {username}: {new_content}\n"
        lines[message_number] = new_line

        with open(threadTitle, "w") as f:
            f.writelines(lines)

        udp_socket.sendto(f"Message {message_number} edited successfully.".encode(), client_addr)
        print(f"[EDT] Message {message_number} in thread '{threadTitle}' edited by {username}")

    except Exception as e:
        print(f"Error in EDT: {e}") 

def process_LST(udp_socket, client_addr):
    try:
        # list all threads in the current directory
        threads = [f for f in os.listdir() if os.path.isfile(f) and os.path.splitext(f)[1] == ''
                   and f != ".DS_Store"]

        if threads:
            thread_list = "\n".join(threads)
            udp_socket.sendto(f"current threads:\n{thread_list}".encode(), client_addr)
        else:
            udp_socket.sendto("No threads exist.".encode(), client_addr)

        print(f"[LST] Sent thread list to {client_addr}")

    except Exception as e:
        print(f"===== Error in LST: {e}")
    
def process_RDT(message, udp_socket, client_addr):
    try:
        parts = message.strip().split(" ", 1)   # split command and threadtitle
        if len(parts) != 2:
            udp_socket.sendto("Error: Invalid RDT format. Usage: RDT <threadtitle>".encode(), client_addr)
            return

        threadTitle = parts[1]

        # check if threadtitle exists
        if not os.path.exists(threadTitle):
            udp_socket.sendto(f"Error: Thread '{threadTitle}' does not exist.".encode(), client_addr)
            return

        # read the contents of the thread file, except the first line
        with open(threadTitle, "r") as f:
            lines = f.readlines()

        # check if there is no message in the thread
        if len(lines) <= 1:
            udp_socket.sendto(f"Thread '{threadTitle}' has no messages.".encode(), client_addr)
        else:
            content = "".join(lines[1:])  # skip the first line
            udp_socket.sendto(content.encode(), client_addr)

        print(f"[RDT] Sent contents of thread '{threadTitle}' to {client_addr}")

    except Exception as e:
        print(f"===== Error in RDT: {e}")

def process_UPD(message, udp_socket, client_addr):
    try:
        parts = message.strip().split() # split command, threadtitle and filename
        if len(parts) != 3:
            udp_socket.sendto("Error: Invalid UPD format.\n".encode(), client_addr)
            return

        threadTitle = parts[1]
        filename = parts[2]

        # read the username from activeUsers, used to add the upload record to the thread file
        username = activeUsers.get(client_addr)
        if not username:
            udp_socket.sendto("Error: User not recognized.\n".encode(), client_addr)
            return

        # check if thread exists
        if not os.path.exists(threadTitle):
            udp_socket.sendto(f"Error: Thread '{threadTitle}' does not exist.\n".encode(), client_addr)
            return

        # check if the file already exists in the thread
        save_name = f"{threadTitle}-{filename}"
        if os.path.exists(save_name):
            udp_socket.sendto(f"Error: File '{filename}' already uploaded to thread '{threadTitle}'.\n".encode(), client_addr)
            return

        # if everything is ok, transfer the file over TCP
        udp_socket.sendto("READY\n".encode(), client_addr)
        print(f"[UPD] Ready to receive file '{filename}' via TCP")

        time.sleep(0.01)    # for the client to receive the message, stayability
        receive_file_over_tcp(threadTitle, filename, udp_socket, client_addr)

        # write the username and upload record to the thread file
        with open(threadTitle, "a") as f:
            f.write(f"{username} uploaded {filename}\n")

        udp_socket.sendto(f"File '{filename}' uploaded to thread '{threadTitle}' successfully.\n".encode(), client_addr)
        print(f"[UPD] File '{filename}' uploaded and logged to thread '{threadTitle}'")

    except Exception as e:
        print(f"===== Error in UPD: {e}")

def receive_file_over_tcp(thread, filename, udp_socket, client_addr, serverHost="127.0.0.1"):
    max_tries = 10
    tcp_sock = None
    port = None

    # every time a new file to be uploaded, randomly select a port number between 20000 and 30000
    # to prevent port collision
    for _ in range(max_tries):
        try:
            port = random.randint(20000, 30000)
            tcp_sock = socket(AF_INET, SOCK_STREAM)
            tcp_sock.bind((serverHost, port))
            tcp_sock.listen(1)
            break
        except OSError:
            continue
    else:
        udp_socket.sendto("Error: Cannot find available port.\n".encode(), client_addr)
        return False

    # send the port number to the client
    udp_socket.sendto(f"PORT {port}\n".encode(), client_addr)
    print(f"[TCP] Listening for file on port {port}.")

    # build the TCP connection
    conn, addr = tcp_sock.accept()
    print(f"[TCP] Connected by {addr}")

    # create and write the file
    server_file = f"{thread}-{filename}"
    file_created = False
    f = None

    try:
        while True:
            data = conn.recv(2048)
            if not data:
                break
            if not file_created:
                f = open(server_file, "wb")
                file_created = True
            f.write(data)
        print(f"[TCP] File received and saved as {server_file}")
        return True
    except Exception as e:
        print(f"[TCP Error] {e}")
        return False
    finally:
        if f:
            f.close()   # once the file is uploaded, close the tcp connection
        conn.close()
        tcp_sock.close()

def process_DWN(message, udp_socket, client_addr):
    try:
        parts = message.strip().split() # split command, threadtitle and filename
        if len(parts) != 3:
            udp_socket.sendto("Error: Invalid DWN format.\n".encode(), client_addr)
            return

        threadTitle = parts[1]
        filename = parts[2]
        full_filename = f"{threadTitle}-{filename}"

        # check if the thread and file exist
        if not os.path.exists(threadTitle):
            udp_socket.sendto(f"Error: Thread '{threadTitle}' does not exist.\n".encode(), client_addr)
            return

        if not os.path.exists(full_filename):
            udp_socket.sendto(f"Error: File '{filename}' was not found in thread '{threadTitle}'.\n".encode(), client_addr)
            return

        # if the file exists, send the file over TCP
        udp_socket.sendto("READY".encode(), client_addr)
        time.sleep(0.01)

        # send the file over TCP
        send_file_over_tcp(full_filename, udp_socket, client_addr)

        udp_socket.sendto(f"File '{filename}' downloaded successfully from thread '{threadTitle}'.\n".encode(), client_addr)
        print(f"[DWN] Sent file '{filename}' to {client_addr}")

    except Exception as e:
        print(f"===== Error in DWN: {e}")

def send_file_over_tcp(filepath, udp_socket, client_addr, serverHost="127.0.0.1"):
    # similar to UPD, randomly select a port number between 20000 and 30000
    max_tries = 10
    for _ in range(max_tries):
        try:
            port = random.randint(20000, 30000)
            tcp_sock = socket(AF_INET, SOCK_STREAM)
            tcp_sock.bind((serverHost, port))
            tcp_sock.listen(1)
            break
        except OSError:
            continue
    else:
        udp_socket.sendto("Error: Cannot find available port.\n".encode(), client_addr)
        return

    # send the port number to the client
    udp_socket.sendto(f"PORT {port}".encode(), client_addr)
    print(f"[TCP] Ready to send file on port {port}")

    # build the TCP connection
    conn, addr = tcp_sock.accept()
    print(f"[TCP] Sending to {addr}")

    # write the file
    try:
        with open(filepath, "rb") as f:
            while True:
                data = f.read(2048)
                if not data:
                    break
                conn.sendall(data)
        print(f"[TCP] File {filepath} sent successfully.")
    except Exception as e:
        print(f"[TCP Send Error] {e}")
    finally:
        conn.close()
        tcp_sock.close()

def process_RMV(message, udp_socket, client_addr):
    try:
        parts = message.strip().split()     # split command, threadtitle
        if len(parts) != 2:
            udp_socket.sendto("Error: Invalid RMV format.".encode(), client_addr)
            return

        threadTitle = parts[1]

        # # check if thread exists
        if not os.path.exists(threadTitle):
            udp_socket.sendto(f"Error: Thread '{threadTitle}' does not exist.".encode(), client_addr)
            return

        # read the username from activeUsers
        username = activeUsers.get(client_addr)
        if not username:
            udp_socket.sendto("Error: User not recognized.".encode(), client_addr)
            return

        # check if the thread is created by this user by checking the first line of the thresd file
        with open(threadTitle, "r") as f:
            creator = f.readline().strip()

        if username != creator:
            udp_socket.sendto("Error: Only the thread creator can remove it.".encode(), client_addr)
            return

        # if the user mathches the username, remove the thread and all the corresponding file that starts with "threadTitle-"
        os.remove(threadTitle)
        for file in os.listdir():
            if file.startswith(f"{threadTitle}-"):
                os.remove(file)

        udp_socket.sendto(f"Thread '{threadTitle}' and its associated files have been removed.".encode(), client_addr)
        print(f"[RMV] Thread '{threadTitle}' deleted by {username}")

    except Exception as e:
        print(f"===== Error in RMV: {e}")

def process_XIT(udp_socket, client_addr):
    try:
        # check if the user is online by using client address as the key
        if client_addr in activeUsers:
            username = activeUsers.pop(client_addr)
            print(f"[XIT] User '{username}' logged out.")
            udp_socket.sendto("Goodbye!".encode(), client_addr)
        else:
            udp_socket.sendto("Error: User not logged in.".encode(), client_addr)
    except Exception as e:
        print(f"===== Error in XIT: {e}")


# keep listening for UDP messages and handle user commands
def udp_listener():
    udp_sock = socket(AF_INET, SOCK_DGRAM)
    udp_sock.bind((serverHost, udpPort))
    print(f"UDP server listening on {serverHost}:{udpPort}...")
    while True:
        data, client_addr = udp_sock.recvfrom(2048)
        message = data.decode().strip()
        print(f"[recv] From {client_addr}: {message}")

        # if not logged in, need to login first
        if client_addr not in activeUsers and not message == 'login':
            udp_sock.sendto("Please login first using: login".encode(), client_addr)
            continue

        if message == 'login':
            print("[recv] New login request")
            process_login(client_addr, udp_sock)
        elif message.startswith("CRT "):
            process_CRT(message, udp_sock, client_addr)
        elif message.startswith("MSG "):
            process_MSG(message, udp_sock, client_addr)
        elif message.startswith("DLT "):
            process_DLT(message, udp_sock, client_addr)
        elif message.startswith("EDT "):
            process_EDT(message, udp_sock, client_addr)
        elif message.startswith("LST"):
            process_LST(udp_sock, client_addr)
        elif message.startswith("RDT "):
            process_RDT(message, udp_sock, client_addr)
        elif message.startswith("UPD "):
            process_UPD(message, udp_sock, client_addr)
        elif message.startswith("DWN "):
            process_DWN(message, udp_sock, client_addr)
        elif message.startswith("RMV "):
            process_RMV(message, udp_sock, client_addr)
        elif message.strip() == "XIT":
            process_XIT(udp_sock, client_addr)

        else:
            udp_sock.sendto("Unrecognized command.".encode(), client_addr)


if __name__ == "__main__":
    print("\n===== Server is running =====")
    print("===== Waiting for connection request from clients.=====")
    udp_listener()
