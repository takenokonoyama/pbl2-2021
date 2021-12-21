import socket,os,sys,time
import threading,json,hashlib
os.chdir(os.path.dirname(sys.argv[0]))

def user_service_thread(sock_conn, client_addr):
    try:
        while True:
            data_len = sock_conn.recv(15)
            if not data_len:
                print("client disconnected")
                break
            data_len = data_len.decode().rstrip()
            data_len = int(data_len)
            recv_size = 0
            json_data = b""
            while recv_size < data_len:
                tmp = sock_conn.recv(data_len - recv_size)
                if tmp == 0:
                    break
                json_data += tmp
                recv_size += len(tmp)    
            json_data = json_data.decode()
            req = json.loads(json_data)
            print("i am a client request",req)
            #此时req as a request sent by user

            if req["op"] == 1:
                print("clients wants to downloas files")
                #download file request


                if req["look"] == 0:
                #view download file size request
                    filename = os.path.dirname(sys.argv[0]) + "/" + req["file_name"]
                    try:
                        with open(filename,'rb') as f:
                            data = f.read()
                    except:
                        data = ''

                    send_data = {"op":0,"file_name":len(data),"file_type":1}
                    send_data = json.dumps(send_data)
                    send_data_size = str(len(send_data.encode())).encode()+b' '*(15-len(str(len(send_data.encode())).encode()))
                    sock_conn.send(send_data_size)
                    sock_conn.send(send_data.encode())
                if req["look"] == 1:
                    #download file request
                    print("client to download file........")
                    filename = os.path.dirname(sys.argv[0])+"/"+req["file_name"]
                    print(filename)

                    #the download target is the file  file size change to a string

                    try:
                        file_size = str(os.path.getsize(filename))
                        file_type = 0
                        send_data =  {"op":1,"file_name":req["file_name"],"file_type":file_type,"file_size":file_size}
                        send_data = json.dumps(send_data)
                        #send_data became a joson string
                        send_data_size =str(len(send_data.encode())).encode()+ b' '*(15-len(str(len(send_data.encode())).encode()))
                        print('download sent,',send_data_size)
                        sock_conn.send(send_data_size)
                        sock_conn.send(send_data.encode())
                        with open(filename, "rb") as f:
                            while True:
                                data = f.read(1024)
                                if len(data) == 0:
                                    break
                                sock_conn.send(data)
                        print("i am done")
                        sock_conn.close()


                    except:
                        send_data =  {"op":1,"file_name":0}
                        send_data = json.dumps(send_data)
                        #send_data变成了json字符串 change to json string
                        send_data_size =str(len(send_data.encode())).encode()+ b' '*(15-len(str(len(send_data.encode())).encode()))
                        sock_conn.send(send_data_size)
                        sock_conn.send(send_data.encode())
                        sock_conn.close()


    except:
        print("client(%s:%s)disconnect！" % client_addr)
        sock_conn.close()


sock_listen = socket.socket()
sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock_listen.bind(("127.0.0.1",9988))
sock_listen.listen(5)
while True:
        sock_conn, client_addr = sock_listen.accept()
        print("client(%s:%s)disconnet！" % client_addr)
        threading.Thread(target=user_service_thread, args=(sock_conn, client_addr)).start()

