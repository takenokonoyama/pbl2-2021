# -*- coding: utf-8 -*-
# client.py

from socket import *
import time
import sys
import pbl2
import os


BUFSIZE = 1024 # 受け取る最大のファイルサイズ
client_name = os.uname()[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
server_name = sys.argv[1] # サーバのホスト名
server_port =  int(sys.argv[2]) # サーバのポート
server_file_name = sys.argv[3] # ファイル名
token_str = sys.argv[4] # トークン文字列
mid_name = sys.argv[5] # 中間サーバのホスト名
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル


mid_port = 53010


# 応答の受け取り
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
    print(rec_str)
    return rec_str

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
def GET_all(soc, file_name,token_str):
    # 要求
    key = pbl2.genkey(token_str)
    msg = f'GET {file_name} {key} ALL\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET ALL')
    
    # 応答の受け取り
    rec_res(soc)
    receive_server_file(soc)
    soc.close()

# GET(PARTIAL)
def GET_part(soc,file_name,token_str,sB, eB):
    # 要求
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET PARTIAL')

    # 応答の受け取り
    rec_res(soc)
    receive_server_file(soc)
    soc.close()    

# REP
def REP(soc, file_name, token_str):
    key = pbl2.genkey(token_str) # keyの作成
    repkey_out = pbl2.repkey(key, rec_file_name) # repkeyの作成
    msg = f'REP {file_name} {repkey_out}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request REP')
    
    # 応答の受け取り
    rec_res(soc)
    soc.close()

# serverからのfileの受け取り
def receive_server_file(soc):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

def BC():
    ADDRESS = {"pbl1","pbl2","pbl3","pbl4"}#,"pbl5","pbl6","pbl7"}
    client_socket = socket(AF_INET, SOCK_STREAM) 
    print("BC")
    command1 = f'SET {server_name} {server_port}\n'
    command2 = f'IAM {server_name} {server_port}\n'
    for address in ADDRESS:
        if client_name != address :
            try :
                client_socket.connect((address, mid_port))
                client_socket.send(command1.encode())
                print("sending:","to",address,command1)
                rep=rec_res(client_socket)
                print(rep)
            except :
                print("Can't send to",address)
        else :
            try :
                client_socket.connect((address, mid_port))
                client_socket.send(command2.encode())
                print("sending:","to",address,command2)
            except :
                print("Can't send to",address)

    client_socket.close()

def commandMain(key):
    # SIZE 
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key == 1:
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    SIZE(client_socket, server_file_name) # SIZEコマンド

    # GET(ALL)
    # 要求を2つ以上行う場合、ソケットをもう一度作る必要がある
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key == 1:
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    
    GET_all(client_socket, server_file_name, token_str) # GET(ALL)コマンド

    # GET(PARTIAL)
    # client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    # client_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    # GET_part(client_socket, server_file_name, token_str, 0, 10) # GET(PARTIAL)コマンド


    # REP
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key == 1:
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    REP(client_socket, server_file_name, token_str) # REPコマンド

if __name__ == '__main__':
    BC()
    print('server_name:',server_name) # サーバ名
    print('server_port:',server_port) # サーバポート番号 
    print()
    print('mid_name:',mid_name) # 中間サーバ名
    print('mid_port:',mid_port) # 中間サーバポート番号 
    print()
    commandMain(1)

    