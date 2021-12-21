# -*- coding: utf-8 -*-
# mids_pack.py
from socket import *
import sys
import threading  # for Thread()
import os
BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル
# mid_name = sys.argv[1]  # 中間サーバのホスト名あるいはIPアドレスを表す文字列
# mid_port = sys.argv[2] # 中間サーバのポート
# server_name = sys.argv[3] # サーバのホスト名
# server_port =  int(sys.argv[4]) # サーバのポート

server_name = sys.argv[1]
server_port = int(sys.argv[2])
my_name = sys.argv[3] # 自身のサーバ名
my_port = int(sys.argv[4]) # 自身のポート

# 応答コードの受け取り
def rec_res(soc):
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
    with open(rec_file_name,'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

# 中間とサーバとのやり取り
def interact_with_server(server_name, server_port, req_msg, req):
    server_socket_to_mid = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    server_socket_to_mid.connect((server_name, server_port)) # 中間管理サーバとサーバとの接続

    print('Sending to server: {0}'.format(req_msg)) 

    print('server_name: ', server_name)
    print('server_port: ', server_port)

    server_socket_to_mid.send(req_msg.encode()) # 転送管理サーバがサーバに対してGET要求を送信

    rep = rec_res(server_socket_to_mid) # サーバーからの応答の受け取り

    print('server_rep: ', rep)
    print('request: ', req)

    # 中間サーバからサーバのある中間サーバへに対しての要求
    if req == "SET":
        sentence = f"DEC{server_name}\n" # 自分の名前を添えてDECコマンドをサーバのある中間へ送信
        server_socket_to_mid.send(sentence.encode()) # 
        rep = rec_res(server_socket_to_mid) # SETの応答の受け取り
        rep = f"{rep[0:3]}{server_name}\n"# 返ってきたDECコマンドに自分の名前をつける
        print(rep)

    # SIZE, GET, REPのサーバへの通信
    else:
        server_socket_to_mid.send(req_msg.encode())
        rep = rec_res(server_socket_to_mid)
        # GET要求だった場合ファイル受け取り
        if req == "GET" :
            receive_server_file(server_socket_to_mid)
    server_socket_to_mid.close()
    return rep

# クライアント、中間、サーバのやり取り
def interact_relay_mid_TCP(cl_soc):

    # ---clientとのやり取り-----
    req_msg = rec_res(cl_soc) # クライアントからの要求受け取り
    print('Received: {0}'.format(req_msg)) 
    req = req_msg[0:3] # 要求の種類

    if(req == "SET"):
        server_name = req_msg[4:8]
        server_port = int(req_msg[8:14])
        # 自身がサーバなら
        if my_name == server_name:
            print("I'm Server")
            rep_msg = f"DEC{my_name}\n" # サーバ名をつけて返す
            cl_soc.send(rep_msg.encode())
        # 自身がサーバでないなら
        else:
            mid_port = my_port # 中間管理サーバのポート番号は共通
            rep_msg = interact_with_server(server_name, mid_port, req_msg, req)
            cl_soc.send(rep_msg.encode())

            print("Sending to client: {0}".format(rep_msg))
    
    elif req == "DEC":
        rep_msg = f"DEC{my_name}" # サーバのある中間サーバ
        cl_soc.send(rep_msg.encode())
        print('Sending to client: {0}'.format(rep_msg))
    # 
    elif req == "IAM":
        server_name = req_msg[4:8]
        server_port = int(req_msg[8:14])
        pass

    # ---- serverとのやり取り----
    rep_msg = interact_with_server(server_name, server_port, req_msg, req)
    print('Sending to client: {0}'.format(rep_msg))
    cl_soc.send(rep_msg.encode()) # サーバからの応答文字列をそのままクライアントに送る

    # 要求の種類がGETだった場合、ファイルをクライアント側に転送
    if req == "GET":
        openfile("midreceived_data.dat", cl_soc)

    print("Finish sending")
    cl_soc.close()

def openfile(file_name, soc) :
    path = os.getcwd()
    path +="/"
    path +=file_name
    print(path)
    with open(path, 'rb') as f:
        s = f.read()
        soc.send(s) # 1文字ずつ送る
        
        # for line in f:
        #    soc.sendall(line) # 1列ずつ送る

def main():
    # -----転送管理サーバを経由してサーバとクライアントの通信をする----  
    my_socket = socket(AF_INET, SOCK_STREAM)
    my_socket.bind(('', my_port)) # 自身のポートをソケットに対応づける
    my_socket.listen(6)

    print('The server is ready to receive')
    
    while True:
        # スレッドを作り、そこで動かす関数と引数をスレッドに与える
        #   argsに与えるのはタプル(xxx, xxx, ...)でないといけないので、
        #   たとえ引数が一つであっても、括弧で囲い、かつ、ひとつめの要素のあとにカンマを入れる。
        connection_socket, addr = my_socket.accept()
        client_handler = threading.Thread(target=interact_relay_mid_TCP, args=(connection_socket,))
        client_handler.start()  # スレッドを開始
        
if __name__ == '__main__':

    print("mid_name:",my_name)
    print("mid_port:",my_port)    
    
    main()
    