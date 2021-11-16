# -*- coding: utf-8 -*-
# client.py

from socket import *
import time
import sys
import pbl2

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
server_name = sys.argv[1]  # サーバのホスト名あるいはIPアドレスを表す文字列
server_port =  int(sys.argv[2]) # サーバのポート
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル

# serverとのやり取り
def interact_with_server(s):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = s.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む
    s.close()  # 最後にソケットをクローズ

# SIZE要求
def SIZE_req(s, f):
    msg = f'SIZE {f}\n' # 要求メッセージ
    s.send(msg.encode())

# GET要求(ALL)
def GET_req_all(s, f, ts):
    key = pbl2.genkey(ts)
    msg = f'GET {f} {key} ALL\n' # 要求メッセージ
    s.send(msg.encode())

# GET要求(PARTIAL)
def GET_req_part(s, f, ts, sB, eB):
    key = pbl2.genkey(ts)
    msg = f'GET {f} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ
    s.send(msg.encode())

# REP要求
def REP_req(s, f, ts):
    key = pbl2.genkey(ts) 
    repkey_out = pbl2.repkey(key, f)
    msg = f'REP {f} {repkey_out}\n' # 要求メッセージ
    s.send(msg.encode())

if __name__ == '__main__':
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((server_name, server_port))  # サーバのソケットに接続する

    client_socket.close()