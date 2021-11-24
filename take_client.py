# -*- coding: utf-8 -*-
# client.py

from socket import *
import time
import sys
import pbl2

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
server_name = sys.argv[1]  # サーバのホスト名あるいはIPアドレスを表す文字列
server_port =  int(sys.argv[2]) # サーバのポート
server_name = sys.argv[3] #ファイル名
server_name = sys.argv[4] #トークン文字列
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル

# serverとのやり取り
def interact_with_server(soc):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む
    soc.close()  # 最後にソケットをクローズ

# SIZE要求
def SIZE_req(soc, file_name):
    msg = f'SIZE {file_name}\n' # 要求メッセージ
    soc.send(msg.encode())

# GET要求(ALL)
def GET_req_all(soc, file_name,token_str):
    key = pbl2.genkey(token_str)
    msg = f'GET {file_name} {key} ALL\n' # 要求メッセージ
    soc.send(msg.encode())

# GET要求(PARTIAL)
def GET_req_part(soc,file_name,token_str,sB, eB):
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ
    soc.send(msg.encode())

# REP要求
def REP_req(soc,file_name, token_str):
    key = pbl2.genkey(token_str) # keyの作成
    repkey_out = pbl2.repkey(key, rec_file_name) # repkeyの作成
    msg = f'REP {file_name} {repkey_out}\n' # 要求メッセージ
    soc.send(msg.encode())

# 応答の受け取り
def rec_res(soc):
    rec_str = soc.recv(BUFSIZE).decode()
    print('received response')
    print(rec_str)

if __name__ == '__main__':
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    sever_file_name = 'aaaa' # サーバー側にあるファイル名(書き換える必要あり)

    client_socket.close() # ソケットを閉じる