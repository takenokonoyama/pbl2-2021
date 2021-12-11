# -*- coding: utf-8 -*-
# mids.py

from socket import *
import threading  # for Thread()
import os

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル

mid_name = os.uname()[1] # 中間サーバのホスト名あるいはIPアドレスを表す文字列

server_name = 0 # サーバのホスト名
server_port = 0 # サーバのポート

mid_port = 53010

def rec_res(soc):
    # 応答コードの受け取り
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        recv_bytearray.append(b)
        if(bytes([b]) == b'\n'):
            rec_str = recv_bytearray.decode()
            break
    print('received response')

    return rec_str

def receive_server_file(soc):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

def mid_server(server_name, server_port,sentence,com):#中間サーバとサーバの通信
    mid_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    mid_socket.connect((server_name, server_port))#中間、サーバとのコネクト
    print('Sending to server: {0}'.format(sentence))
    print(server_name)
    print(server_port)

    if com =="SET":
        sentence=f"DEC{mid_name}\n"
        mid_socket.send(sentence.encode())  
        rep = rec_res(mid_socket)
        rep = f"{rep[0:7]}{mid_name}\n"
    else:
        mid_socket.send(sentence.encode())  
        rep = rec_res(mid_socket)
    print(rep)
    print(com)

    if com =="GET" :
        receive_server_file(mid_socket)
        return rep

    mid_socket.close()
    return rep

def interact_with_client_TCP(soc):
    global server_name
    global server_port
    print("inter")
    sentence = rec_res(soc)
    print('Received: {0}'.format(sentence)) 
    print(sentence[0:3])
    com=sentence[0:3] 
    
    if com=="SET":
        server_name = sentence[4:8]
        server_port = int(sentence[8:14])
        print('server_name:',server_name) # サーバ名
        print('server_port:',server_port) # サーバポート番号
        if mid_name == server_name:
            print("I am Server")

            rep_sentence=f"DEC{mid_name}\n"
            soc.send(rep_sentence.encode())
        else :    
            rep_sentence=mid_server(server_name, mid_port,sentence,com)
            print('Sending to client: {0}'.format(rep_sentence))
            soc.send(rep_sentence.encode())

    elif com =="DEC":
        rep_sentence=f"DEC{mid_name}\n"
        print('Sending to client: {0}'.format(rep_sentence))
        soc.send(rep_sentence.encode())
    elif com =="IAM" :
        server_name = sentence[4:8]
        server_port = int(sentence[8:14])
        pass
        
    else: #SIZE,GET,REP
        print(server_name,type(server_name))
        print(server_port,type(server_port))
        rep_sentence=mid_server(server_name, server_port,sentence,com)
        print('Sending to client: {0}'.format(rep_sentence))
        soc.send(rep_sentence.encode())

        if com=="GET":
            #"midreceived_data.dat"を送りたい
            #現状ファイルの中身を一度開いて一文字ずつ送ってる
            openfile("midreceived_data.dat",soc)

        print("Finish Sending")
    soc.close()

def openfile(file_name,soc) :
    path=os.getcwd()
    print(path)
    path +="/"
    path +=file_name
    with open(path,'rb') as f:
        s = f.read()
        soc.send(s)

def main_TCP(): #クライアントと中間サーバの通信
    mid_socket = socket(AF_INET, SOCK_STREAM) # ソケットを作る
    mid_socket.bind(('', mid_port))
    mid_socket.listen(6) #並列で6台まで処理できる
    print('The server is ready to receive by TCP')
    while True:
        # クライアントからの接続があったら、それを受け付け、
        # そのクライアントとの通信のためのソケットを作る
        connection_socket, addr = mid_socket.accept()  
        client_handler = threading.Thread(target=interact_with_client_TCP, args=(connection_socket,))
        client_handler.start()  # スレッドを開始

if __name__ == '__main__':
    print("mid_name:",mid_name)
    print("mid_port:",mid_port)
    main_TCP()