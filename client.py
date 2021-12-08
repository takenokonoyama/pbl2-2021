# -*- coding: utf-8 -*-
# client.py

from socket import *
import time
import sys
import pbl2

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
my_name = sys.argv[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
my_port = 53602 # クライアントのポート
server_name = sys.argv[2] # サーバのホスト名
server_port =  int(sys.argv[3]) # サーバのポート
server_file_name = sys.argv[4] # サーバ側にあるファイル名
token_str = sys.argv[5] # トークン文字列
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル
mid_name = 'pbl2' # GET要求をするホストの名前
mid_port = 53601 # GET要求をするホストのポート

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
    print('received')
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
    # print(msg)
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

if __name__ == '__main__':

    
    # 情報の出力
    print('my name', my_name)
    print('my port', my_port)

    print('server name', server_name)
    print('server port', server_port)
    
    print('mid_name', mid_name)
    print('mid_port', mid_port)
    
    print()
    '''
    # ---------ネットワークの状態を調べる--------------
    n = 1
    mid_servers = ['pbl1', 'pbl2', 'pbl3', 'pbl4']
    mid_ports = [53601, 53602, 53603, 53604]
    for i in range(n):
        mid_socket = socket(AF_INET, SOCK_STREAM)
        mid_socket.connect((mid_servers[i], mid_ports[i]))
        a = 'aaaa'
        mid_socket.send(a.encode())
        print('Sending {0} to {1}'.format(a, mid_servers[i]))
    
    rep_socket = socket(AF_INET, SOCK_STREAM)  # TCPを使う待ち受け用のソケットを作る
    rep_socket.bind(('', my_port))  # ポート番号をソケットに対応づける
    rep_socket.listen(6)  # クライアントからの接続を待つ

    while True:
        # クライアントからの接続があったら、それを受け付け、
        # そのクライアントとの通信のためのソケットを作る
        connection_socket, addr = rep_socket.accept()
        # クライアントからバイト列を最大1024バイト受信し、
        # 文字列に変換（decode()）する。
        sentence = connection_socket.recv(1024).decode()  
        print('Recieved {0}'.format(sentence))
    '''
    
    # ---------ダウンロードしたファイルをルーティングした経路で送信---------

    get_socket = socket(AF_INET, SOCK_STREAM)
    get_socket.connect((mid_name, mid_port)) # 転送管理サーバのソケットに接続する
    
    GET_all(get_socket, server_file_name, token_str) # GET要求をするための情報を送信
    

    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    REP(server_socket, server_file_name, token_str) # REP
