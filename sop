import json,socket

def xiazai1(dpc):
        info = dpc.split()
        sock = socket.socket()
        # try:
        sock.connect(("127.0.0.1", 9988))
        filename = info[1]
        try:
                sock = socket.socket()
                sock.connect(("127.0.0.1",9988))
                if info[0] == 'get':
                        send_data = {"op":1,"look":1,"file_name":filename}
                else:
                        send_data = {"op":1,"look":0,"file_name":filename}
                send_data = json.dumps(send_data)
                send_data_size = str(len(send_data.encode())).encode()+b' '*(15-len(str(len(send_data.encode())).encode()))
                sock.send(send_data_size)
                sock.send(send_data.encode())

                data_size = sock.recv(15).decode().rstrip()
                print(data_size,"...............")


                data_size = int(data_size)
                data = sock.recv(data_size)
                data = json.loads(data.decode())
                if data["file_name"]==0:
                        print("该文件不存在！")
                        return
                else:
                        if data["file_type"] == 0:
                                filename = data["file_name"]
                                filesize = int(data["file_size"])

                                data_cont = b""
                                cont1=0

                                print("我要开始接收内容了")
                                while True:

                                        data = sock.recv(filesize-cont1)
                                        data_cont+=data
                                        cont1+=len(data)

                                        if cont1 == filesize:
                                                print("文件接收完毕")
                                                break
                                with open(filename,"wb") as op:
                                        op.write(data_cont)
                        else:
                                print('{}大小为：'.format(filename),data["file_name"])
        finally:
                sock.close()



a = input('请输入请求:')
xiazai1(a)









                


