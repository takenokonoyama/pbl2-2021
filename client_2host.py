# -*- coding: utf-8 -*-
# client.py

from socket import *
import time
import sys
import pbl2
import pickle

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
my_name = sys.argv[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
my_port = 53602 # クライアントのポート
server_name = sys.argv[2] # サーバのホスト名
server_port =  int(sys.argv[3]) # サーバのポート
server_file_name = sys.argv[4] # サーバ側にあるファイル名
token_str = sys.argv[5] # トークン文字列

rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル

mid_name = ''
mid_port = 53601 # 中管理サーバのポート

RootTable = [] # 調べた経路を保存するリスト

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

    return rec_str

# SIZE 
def SIZE(file_name):
    # 要求
    msg = f'SIZE {file_name}\n' # 要求メッセージ
    # soc.send(msg.encode())
    # print('request SIZE')
    return msg

# GET(ALL)
def GET_all(file_name, token_str):
    # 要求
    key = pbl2.genkey(token_str)
    msg = f'GET {file_name} {key} ALL\n' # 要求メッセージ
    print('request GET ALL')
    return msg

# GET(PARTIAL)
def GET_part(file_name,token_str,sB, eB):
    # 要求
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ

    print('request GET PARTIAL')
    return msg

# REP
def REP(file_name, token_str):
    key = pbl2.genkey(token_str) # keyの作成
    repkey_out = pbl2.repkey(key, rec_file_name) # repkeyの作成
    msg = f'REP {file_name} {repkey_out}\n' # 要求メッセージ
    # print(msg)
    # print('request REP')
    return msg

# serverからのfileの受け取り(上書き)
def receive_server_file(soc):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む
    print('received server file')

# serverからのfileの受け取り(追記)
def receive_sever_file_add(soc):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'ab') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

# サーバに対して直接通信する経路を調べる
def dir_server():
    start_time = time.time()
    server_socket = socket(AF_INET, SOCK_STREAM) # ソケットを作る    
    server_socket.connect((server_name, server_port)) # 中間、サーバとのコネクト
    
    get_res = GET_all(server_socket, server_file_name, token_str) # GET_ALL
    
    server_socket = socket(AF_INET, SOCK_STREAM) # ソケットを作る    
    server_socket.connect((server_name, server_port)) # 中間、サーバとのコネクト
    
    rep_res = REP(server_socket, server_file_name, token_str) # REP

    end_time = time.time()

    print("dir time: {0}".format(end_time - start_time))

# ホスト1つを経由する場合の経路を調べる
def rooting_1host(my_port, ADDRESS):
    # TCPで全てのホストに送信
    TTL = 1
    for ad in ADDRESS:
        # 自分とサーバと同じ名前を持つ転送管理サーバ以外へ送信
        if my_name != ad and server_name != ad:
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect((ad, mid_port)) # 送信するホストとコネクション
            # mid_port += 1
            # 送信するデータを配列に格納
            data = b"abcdefghijklmnopqrstuvwxyz" # 任意のデータ
            # 参照する経由番号
            relay_num = 1
            '''
            パケット
            (クライアント名, 1つめの経由するホスト(経由番号1),2つめの経由するホスト(経由番号2),
            サーバ名,任意データ,TTL,参照する経由番号,パケットの種類(Root(ルーティング用パケット) or Com(コマンド用パケット)), 
            送信用(req)or応答用(rep), クライアントのポート番号)
            '''
            info_pack = [my_name, ad, 'none',server_name , data, TTL, relay_num,'Root', 'req', my_port]
            info_pack = pickle.dumps(info_pack) # 配列全体をバイト列に変換
            start_time = time.time() # 時間計測開始
            client_socket.send(info_pack) # データ配列の送信
            
            # info_packet(応答用)の受け取り
            client_socket_recv = socket(AF_INET, SOCK_STREAM)
            client_socket_recv.bind(('', my_port))
            my_port += 1
            client_socket_recv.listen(10)
            connection_socket, addr = client_socket_recv.accept()
            rep_info_pack = connection_socket.recv(1024) 
            rep_info_pack = pickle.loads(rep_info_pack) #バイト列を配列に変換
            end_time = time.time() # 時間計測完了

            # ルートテーブルへ調べた経路と時間を追加
            Root = [end_time - start_time,rep_info_pack[0],rep_info_pack[1],\
                    rep_info_pack[2], rep_info_pack[3]]
            RootTable.append(Root)

            # print(rep_info_pack)
            # print(RootTable)
            # print("time : {0}".format(end_time - start_time))
            
            client_socket.close() 

# ホスト2つを経由する場合の経路を調べる
def rooting_2host(my_port, ADDRESS):
    # TCPで全てのホストに送信
    TTL = 2
    for ad1 in ADDRESS:
        if my_name != ad1 and server_name != ad1:
            for ad2 in ADDRESS:
                if my_name != ad2 and server_name != ad2 and ad1 != ad2:
                    # 自分とサーバと同じ名前を持つ転送管理サーバ以外へ送信
                    client_socket = socket(AF_INET, SOCK_STREAM)
                    client_socket.connect((ad1, mid_port)) # 送信するホストとコネクション
                    # mid_port += 1
                    # 送信するデータを配列に格納
                    data = b"abcdefghijklmnopqrstuvwxyz" # 任意のデータ
                    # 参照する経由番号
                    relay_num = 1
                    '''
                    パケット
                    (クライアント名, 1つめの経由するホスト(経由番号1),2つめの経由するホスト(経由番号2),
                    サーバ名,任意データ,TTL,参照する経由番号,パケットの種類(Root(ルーティング用パケット) or Com(コマンド用パケット)), 
                    送信用(req)or応答用(rep), クライアントのポート番号)
                    '''
                    info_pack = [my_name, ad1, ad2, server_name , data, TTL, \
                                relay_num,'Root','req', my_port]
                    info_pack = pickle.dumps(info_pack) # 配列全体をバイト列に変換
                    start_time = time.time() # 時間計測開始
                    client_socket.send(info_pack) # データ配列の送信
                    
                    # info_packet(応答用)の受け取り
                    client_socket_recv = socket(AF_INET, SOCK_STREAM)
                    client_socket_recv.bind(('', my_port))
                    my_port += 1
                    client_socket_recv.listen(10)
                    connection_socket, addr = client_socket_recv.accept()
                    rep_info_pack = connection_socket.recv(1024) 
                    rep_info_pack = pickle.loads(rep_info_pack) #バイト列を配列に変換
                    end_time = time.time() # 時間計測完了

                    # ルートテーブルへ調べた経路の時間を追加
                    Root = [end_time - start_time,rep_info_pack[0],rep_info_pack[1],\
                            rep_info_pack[2], rep_info_pack[3]]
                    RootTable.append(Root)

                    # print(rep_info_pack)
                    # print(RootTable)
                    # print("time : {0}".format(end_time - start_time))
                    
                    client_socket.close() 

# SIZEパケットのやり取り(サーバ側へ最も速い経路をたどってSIZE要求をする)
def SIZE_cmd(client_socket, my_port, RootTable):
    SIZE_pack = [RootTable[0][1],RootTable[0][2],RootTable[0][3], RootTable[0][4],\
                    'SIZE', SIZE(server_file_name), 1, 'Com', 'req', my_port]
    print('SIZE_packet', SIZE_pack)
    
    SIZE_pack = pickle.dumps(SIZE_pack) # 配列全体をバイト列に変換
    client_socket.send(SIZE_pack) # データ配列の送信

    # サーバからの応答の受け取り
    client_socket_recv = socket(AF_INET, SOCK_STREAM)
    client_socket_recv.bind(('', my_port))
    client_socket_recv.listen(10)
    connection_socket, addr = client_socket_recv.accept()
    SIZE_sentence = rec_res(connection_socket)
    print('SIZE_sentence', SIZE_sentence)
    client_socket.close()
    return SIZE_sentence

# GETコマンド
def GET_cmd(client_socket, my_port, RootTable, token_str, server_file_name):
    
    # GET要求
    GET_pack = [RootTable[0][1],RootTable[0][2],RootTable[0][3],RootTable[0][4],\
                'GET', GET_all(server_file_name, token_str), 1, 'Com', 'req', my_port]
    print('GET_packet', GET_pack)
    GET_pack = pickle.dumps(GET_pack) # 配列全体をバイト列に変換
    client_socket.send(GET_pack) # データ配列の送信
    


    # サーバからの応答(最短経路をたどる)の受け取り
    client_socket_recv = socket(AF_INET, SOCK_STREAM)
    client_socket_recv.bind(('', my_port))
    client_socket_recv.listen(10)
    connection_socket, addr = client_socket_recv.accept()
    GET_sentence = rec_res(connection_socket)    
    print(GET_sentence)
    receive_server_file(connection_socket)
    return GET_sentence

# REPコマンド
def REP_cmd(client_socket, my_port, RootTable, token_str, server_file_name):
    REP_pack = [RootTable[0][1],RootTable[0][2],RootTable[0][3], RootTable[0][4],\
                    'REP', REP(server_file_name, token_str), 1, 'Com', 'req', my_port]
    print('REP_packet', REP_pack)
    
    SIZE_pack = pickle.dumps(REP_pack) # 配列全体をバイト列に変換
    client_socket.send(SIZE_pack) # データ配列の送信

    # サーバからの応答の受け取り
    client_socket_recv = socket(AF_INET, SOCK_STREAM)
    client_socket_recv.bind(('', my_port))
    client_socket_recv.listen(10)
    connection_socket, addr = client_socket_recv.accept()
    REP_sentence = rec_res(connection_socket)
    print('REP_sentence', SIZE_sentence)
    client_socket.close()
    return REP_sentence  

if __name__ == '__main__':

    # 情報の出力
    print('my name', my_name)
    print('my(client) port', my_port)

    print('server name', server_name)
    print('server port', server_port)
    
    print('mid_name', mid_name)
    print('mid_port', mid_port)
    
    print()

    # ---------ネットワークの状態を調べる--------------
    ADDRESS = ["pbl1","pbl2","pbl3","pbl4"]
    my_port += 5
    rooting_1host(my_port, ADDRESS) # 1ホスト経由のルーティング
    my_port += 5
    rooting_2host(my_port, ADDRESS) # 2ホスト経由のルーティング

    print('rooting completed\n')

    # ---------ダウンロードしたファイルをルーティングした経路で送信---------
    RootTable = sorted(RootTable) # timeによってソート
    print(f'sorted RootTable:\n {RootTable}')

    # SIZEコマンド
    print('SIZE Command\n')
    my_port += 10
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((RootTable[0][2], mid_port)) # 送信するホストとコネクション
    SIZE_sentence = SIZE_cmd(client_socket, my_port, RootTable)

    # GETコマンド
    # n = 2 # 経路として採用する数(RootTableをみて速いものからn個)
    my_port+=10
    print('my_port', my_port)
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((RootTable[0][2], mid_port)) # 送信するホストとコネクション
    GET_sentence = GET_cmd(client_socket, my_port, RootTable, token_str, server_file_name)
    
    # REPコマンド
    my_port += 5
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((RootTable[0][2], mid_port)) # 送信するホストとコネクション
    REP_sentence = REP_cmd(client_socket, my_port, RootTable, token_str, server_file_name)
    print(REP_sentence)