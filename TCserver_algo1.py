# -*- coding: utf-8 -*-
# TCserver_1 algorithm1

from socket import *
import sys
import threading  # for Thread()
import os
import time

BUFSIZE = 1024
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル
server_name = '' # サーバの名前
server_file_name = '' # サーバに要求するファイル名
server_port = 60623 # サーバのポート
key = '' # クライアントで生成されるkey

# 応答コードの受け取り
def rec_res(soc):
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        if(bytes([b]) == b'\n'):
            rec_str = recv_bytearray.decode()
            break
        recv_bytearray.append(b)
    print('received')
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
# SIZE 
def SIZE(soc, file_name):
    # 要求
    msg = f'SIZE {file_name}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request SIZE')
    
    # 応答の受け取り
    rec_res(soc)
    soc.close()

# GET(ALL)
def GET_all(soc, file_name, key):
    # 要求
    msg = f'GET {file_name} {key} ALL\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET ALL')
    
    # 応答の受け取り
    rec_res(soc)
    receive_server_file(soc)
    soc.close()

# GET(PARTIAL)
def GET_part(soc,file_name, key, sB, eB):
    # 要求
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET PARTIAL')

    # 応答の受け取り
    rec_res(soc)
    receive_server_file(soc)
    soc.close()    

def rec_info(my_name, my_port):
    # クライアントからの接続があったら、それを受け付け、
    # そのクライアントとの通信のためのソケットを作る
    my_socket = socket(AF_INET, SOCK_STREAM)
    my_socket.bind(('', my_port))
    my_socket.listen(1)
    
    print(f'{my_name} is ready to receive')

    connection_socket, addr = my_socket.accept()
    server_name = rec_res(connection_socket) # サーバ名の受け取り

    server_file_name = rec_res(connection_socket) # サーバに要求するファイル名の受け取り
    
    key = rec_res(connection_socket) # keyの受け取り

    connection_socket.close()
    
    return server_name, server_file_name, key

def openfile(file_name,soc) :
    path=os.getcwd()
    print(path)
    path +="/"
    path +=file_name
    with open(path) as f:
        s = f.read()
        soc.send(s.encode())

if __name__ == '__main__':

    my_name = 'pbl1' # 自身のホスト名
    my_port = 53601 # 接続待ち受けポート番号

    server_name, server_file_name, key = rec_info(my_name, my_port) # GET要求に必要な情報の受け取り
    
    print('server_name:', server_name)
    print('server_file_name:', server_file_name)
    print('key:',key)

    get_socket = socket(AF_INET, SOCK_STREAM)
    get_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    GET_all(get_socket, server_file_name, key) # サーバに対してGET要求




    
