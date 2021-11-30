# -*- coding: utf-8 -*-
# client.py

from socket import *
import time
import sys
import pbl2

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
client_name = sys.argv[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
server_name = sys.argv[2] # サーバのホスト名
server_port =  int(sys.argv[3]) # サーバのポート
server_file_name = sys.argv[4] # ファイル名
token_str = sys.argv[5] # トークン文字列
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル
# SIZE要求
def SIZE_req(soc, file_name):
    msg = f'SIZE {file_name}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request SIZE')

# GET要求(ALL)
def GET_req_all(soc, file_name,token_str):
    key = pbl2.genkey(token_str)
    msg = f'GET {file_name} {key} ALL\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET ALL')

# GET要求(PARTIAL)
def GET_req_part(soc,file_name,token_str,sB, eB):
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET PARTIAL')

# REP要求
def REP_req(soc, file_name, token_str):
    key = pbl2.genkey(token_str) # keyの作成
    repkey_out = pbl2.repkey(key, rec_file_name) # repkeyの作成
    msg = f'REP {file_name} {repkey_out}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request REP')

# 応答の受け取り
def rec_res(soc):
    # 応答コードの受け取り
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        if(bytes([b]) == b'\n'):
            rec_str = recv_bytearray.decode()
            break
        recv_bytearray.append(b)
    print('received response')
    print(rec_str)

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

if __name__ == '__main__':
    
    print('server_name:',server_name)
    print('server_post:',server_port)

    print()
    
    # SIZE 要求 
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    SIZE_req(client_socket, server_file_name)
    rec_res(client_socket)
    client_socket.close()
    
    print()

    # GET(ALL) 要求
    # 要求を2つ以上行う場合、ソケットをもう一度作る必要がある
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    GET_req_all(client_socket, server_file_name, token_str)
    rec_res(client_socket)
    receive_server_file(client_socket) # ファイルダウンロード
    client_socket.close()

    print()

    # GET(PARTIAL) 要求
    # client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    # client_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    # GET_req_part(client_socket, server_file_name, token_str, 0, 10)
    # rec_res(client_socket)
    # receive_server_file(client_socket) # ファイルダウンロード
    # client_socket.close()

    print()

    # REP要求
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    REP_req(client_socket, server_file_name, token_str)
    rec_res(client_socket)
    client_socket.close() # ソケットを閉じる