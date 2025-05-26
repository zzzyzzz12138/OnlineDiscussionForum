# 🗨️ Online Discussion Forum Application

## 📌 Overview

This project implements a **custom discussion forum** application using a **client-server architecture** communicating over **UDP** and **TCP**. It is designed as part of the COMP3331/9331 Computer Networks course, focusing on socket programming, protocol design, and multi-client interaction in a non-HTTP environment.

The forum supports user authentication, thread and message management, and file transfer functionalities. The system uses **UDP** for most messaging operations and **TCP** for reliable file transfers, simulating the behavior of real-world networked applications.

## 🚀 Features

- ✅ **User authentication** with support for new account creation
- 📄 **Thread creation, listing, deletion**
- 💬 **Post, edit, and delete messages**
- 📂 **File upload and download** over TCP
- 📃 **Custom application-layer protocol**
- ⚙️ Configurable for **single-client** and **multi-client concurrent** operation

## 📁 File Structure
client.py # Client-side implementation
server.py # Server-side implementation
credentials.txt # Server-side user credentials store


## 🔧 Commands Supported

All command exchanges (except file transfer) use **UDP**:

- `CRT <thread_title>` – Create a new thread
- `LST` – List all threads
- `MSG <thread_title> <message>` – Post a message
- `RDT <thread_title>` – Read thread contents
- `DLT <thread_title> <msg_no>` – Delete a message
- `EDT <thread_title> <msg_no> <new_message>` – Edit a message
- `RMV <thread_title>` – Remove a thread
- `XIT` – Exit and log off

File transfer commands using **TCP**:

- `UPD <thread_title> <filename>` – Upload file to a thread
- `DWN <thread_title> <filename>` – Download file from a threa
