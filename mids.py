# -*- coding: utf-8 -*-
# mids.py

from socket import *
import sys
import threading  # for Thread()
import os

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル

mid_name = sys.argv[1]  # 中間サーバのホスト名あるいはIPアドレスを表す文字列
server_name = sys.argv[2] # サーバのホスト名
server_port =  int(sys.argv[3]) # サーバのポート

mid_port = 53013

def rec_res(soc):
    # 応答コードの受け取り
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        if(bytes([b]) == b'\n'):
            recv_bytearray.append(b)
            rec_str = recv_bytearray.decode()
            break
        recv_bytearray.append(b)
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
    sentence = rec_res(soc)
    print('Received: {0}'.format(sentence)) 
    print(sentence[0:3])
    com=sentence[0:3] 

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
    with open(path) as f:
        s = f.read()
        soc.send(s.encode())

def main_TCP(): #クライアントと中間サーバの通信
    mid_socket = socket(AF_INET, SOCK_STREAM) # ソケットを作る
    mid_socket.bind((mid_name, mid_port))
    mid_socket.listen(6) #並列で6台まで処理できる
    print('The server is ready to receive by TCP')
    while True:
        # クライアントからの接続があったら、それを受け付け、
        # そのクライアントとの通信のためのソケットを作る
        connection_socket, addr = mid_socket.accept()  
        client_handler = threading.Thread(target=interact_with_client_TCP, args=(connection_socket,))
        client_handler.start()  # スレッドを開始

"""
def main_UDP():
    server_socket = socket(AF_INET, SOCK_DGRAM) #UDP
    server_socket.bind(('', server_port))
    print('The server is ready to receive by UDP')
    interact_with_client_UDP(server_socket)

def interact_with_client_UDP(soc):
    print(soc)

"""

if __name__ == '__main__':
    main_TCP()