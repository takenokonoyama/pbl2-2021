import socket,os,sys,time
import threading,json,hashlib
os.chdir(os.path.dirname(sys.argv[0]))

def user_service_thread(sock_conn, client_addr):
    try:
        while True:
            data_len = sock_conn.recv(15)
            if not data_len:
                print("客户端断开连接")
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
            print("我是客户端的请求",req)
            #此时req为字典，是用户发送过来的请求

            if req["op"] == 1:
                print("客户要下载文件")
                #下载传文件请求


                if req["look"] == 0:
                #查看可下载文件大小请求
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
                    #下载文件请求
                    print("客户要下载文件........")
                    filename = os.path.dirname(sys.argv[0])+"/"+req["file_name"]
                    print(filename)

                    #下载目标是文件,其中file_size变成了字符串

                    try:
                        file_size = str(os.path.getsize(filename))
                        file_type = 0
                        send_data =  {"op":1,"file_name":req["file_name"],"file_type":file_type,"file_size":file_size}
                        send_data = json.dumps(send_data)
                        #send_data变成了json字符串
                        send_data_size =str(len(send_data.encode())).encode()+ b' '*(15-len(str(len(send_data.encode())).encode()))
                        print('下载传送的,',send_data_size)
                        sock_conn.send(send_data_size)
                        sock_conn.send(send_data.encode())
                        with open(filename, "rb") as f:
                            while True:
                                data = f.read(1024)
                                if len(data) == 0:
                                    break
                                sock_conn.send(data)
                        print("我发完了")
                        sock_conn.close()


                    except:
                        send_data =  {"op":1,"file_name":0}
                        send_data = json.dumps(send_data)
                        #send_data变成了json字符串
                        send_data_size =str(len(send_data.encode())).encode()+ b' '*(15-len(str(len(send_data.encode())).encode()))
                        sock_conn.send(send_data_size)
                        sock_conn.send(send_data.encode())
                        sock_conn.close()


    except:
        print("客户端(%s:%s)断开连接！" % client_addr)
        sock_conn.close()


sock_listen = socket.socket()
sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock_listen.bind(("127.0.0.1",9988))
sock_listen.listen(5)
while True:
        sock_conn, client_addr = sock_listen.accept()
        print("客户端(%s:%s)已连接！" % client_addr)
        threading.Thread(target=user_service_thread, args=(sock_conn, client_addr)).start()

