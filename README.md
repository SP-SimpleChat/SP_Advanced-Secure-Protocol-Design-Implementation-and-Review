# SP_Advanced-Secure-Protocol-Design-Implementation-and-Review
This is a repository created for the Secure Programming assignments whereas students in the group needs to implement a Secure Protocol. 


## Introduction 
- Our goal is to implement a simple lightweight secure chat protocol. This protocol will be WebSocket based or TCP based. In this document it will discuss the protocol design and its structure. 

- Language used for Implementation: Python, JSON 

## Everything in a nutshell: 
- Basically, we are making a WebSocket in python that allows many clients to connect on one server. Later we need to make sure all the text, files, picture or user password are secured. 


## Group Memebers [in alphabetical order] 
- Chuangfan Zhang  (a1930874)
- Songke He (a1948524)
- Weiyu Chen (a1915265)
- Zhen Yu (a1901357) 

## Assignment Objectives
- Conceptualising and standardising a secure communication protocol for a distributed overlay multi-party chat system.
- There cannot be any central server handling all the communication. Rather, the system must be robust to any node or device failure. 
- Develop an application that adheres to a designed protocol (us) and incorporates advanced secure coding practices.  
- Intentionally backdoor your own implementation in an ethical way so that other groups have security flaws to find. 
- Perform peer reviews and engage in both manual and automated code analysis to identify vulnerabilities and backdoors.  
- Critically reflect on the design and implementation process, including evaluating the protocol, the security measures implemented, the quality of the feedback received, a reflection on your own learning and possible coding mistakes.
- Have fun at an ethical hackathon to identify and exploit vulnerabilities in a controlled setting, enhancing your understanding of real-world cybersecurity challenges.

## 📂 Project Structure
SP_Advanced-Secure-Protocol-Design-Implementation-and-Review/
├── client/
│ └── client.py # 命令行客户端
├── server/
│ └── echo_server.py # 本地测试服务器
├── requirements/ # 依赖目录
├── src/ # 其他源码
└── README.md



---

## 🚀 How to Run

### 1. Create virtual environment (recommended)
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
2. Run the test server
bash

python server/echo_server.py
3. Run the client
bash

python client/client.py --host 127.0.0.1 --port 9000 --nick hsk
4. Available commands
bash

/join <room>     # join a chat room
/msg <message>   # send message to the room
/leave           # leave current room
/quit            # disconnect
