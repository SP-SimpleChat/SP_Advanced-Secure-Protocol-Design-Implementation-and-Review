-----------------------------------------------
Group Memebers [in alphabetical order]
Chuangfan Zhang (a1930874)
Songke He (a1948524)
Weiyu Chen (a1915265)
Zhen Yu (a1901357)


---------------------------------------------------------------------------
                            Requirements
---------------------------------------------------------------------------
1. Python 3.10+ recommended
2. tqdm >= 4.66
3. pycryptodome>=3.20

---------------------------------------------------------------------------
                             How to Run
---------------------------------------------------------------------------
1. Create a virtual enviroment (recommended)
    * For Window user run 
            --> python -m venv .venv
            --> .\.venv\Scripts\activate

    * For macOs/Linux run 
            --> source .venv/bin/activate
            --> python3 -m venv .venv

2. Run the server (local only!)
    --> python server/echo_server.py

3. Run the client 
    --> python client/client.py --host 127.0.0.1 --port 9000 --nick Alice 

----------------------------------------------------------------------------------------------------------------------------------
                     Notes 
-----------------------------------------------------------------------------------------------------------------------------------
    * Files you accept are saved to ./downloads/
    * By default, incoming files are NOT auto-downloaded. You must /accept them. 
        --> auto-accept (unsafe) automatically accepts and writes incoming files. 
        --> send-wait N (seconds) makes the sender pause before streaming file 
            chunks, giving receivers time to /accept in manual mode 
                * eg: python client/client.py --host 127.0.0.1 --port 9000 --nick Alice [--auto-accept] [--send-wait 2]



---------------------------------------------------------------------------
                     Available commands 
---------------------------------------------------------------------------
    * /join <room>              --> join a chat room 
    * /who                      --> list members in the current room
    * /msg <message>            --> send message to the chat room 
    * /send <path>              --> sending a file 
    * /send dm:<nick> <path>    --> sending file via dm 
    * /accept <file_id>         --> accept a pending incoming file 
    * /reject <file_id>         --> reject a pending incoming file 
    * /leave                    --> leave current room 
    * /quit                      --> disconnect 

    *Examples (Alice and Bob):
        # Terminal A  
            python client/client.py --nick Alice 
            /join room1 
            /send path/to/file.bin 
        
        # Terminal B 
            python client/client.py --nick Bob
            /join room1
            # sees: "Incoming file id=<FID>, size=<N>B 
            /accept <FID> or /reject <FID>

---------------------------------------------------------------------------
        ___                            _              _   _ 
        |_ _|_ __ ___  _ __   ___  _ __| |_ __ _ _ __ | |_| |
        | || '_ ` _ \| '_ \ / _ \| '__| __/ _` | '_ \| __| |
        | || | | | | | |_) | (_) | |  | || (_| | | | | |_|_|
        |___|_| |_| |_| .__/ \___/|_|   \__\__,_|_| |_|\__(_)
                    |_|                                    

--------------------------------------------------------------------------
                Deliberate Educational Vulnerability
---------------------------------------------------------------------------
    For the Secure Programming peer review task, this project 
    intentionally includes a controlled vulnerability in 
                    `server/echo_server.py` 
    (missing room authorization). Please review and test it **only 
    in a safe local environment**, as described in the assignment 
    instructions.


--------------------------------------------------------------------------
                            Contact / Support 
---------------------------------------------------------------------------
    * If there is any problem please write us an email using 
     our student id as above as a whole and we will find a way 
     to help you. Thank you! 
---------------------------------------------------------------------------