# -*- coding: utf-8 -*-
# client.py

from concurrent import futures
from socket import *
import time
import sys
import pbl2
import pickle
import threading
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
my_name = os.uname()[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
my_port = 53602
my_port_route = 53605 # クライアントのポート
my_port_size = 53602
my_port_get = 53603
my_port_rep = 53604
server_name = sys.argv[1] # サーバのホスト名
server_port =  60623 # サーバのポート
server_file_name = sys.argv[2] # サーバ側にあるファイル名
token_str = sys.argv[3] # トークン文字列
sdata_num = 0
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル
key = ''
mid_name = ''
mid_port = 53601 # 中管理サーバのポート
RouteTable = [] # 調べた経路を保存するリスト
# address = ["pbl1","pbl2","pbl3","pbl4"] # ローカル環境
address = ["pbl1a","pbl2a","pbl3a","pbl4a", "pbl5a","pbl6a","pbl7a"]
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
    # print('received')

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
    # print('request GET ALL')
    return msg

# GET(PARTIAL)
def GET_part(file_name,token_str,sB, eB):
    # 要求
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ

    # print('request GET PARTIAL')
    return msg

# REP
def REP(file_name):
    key = pbl2.genkey(token_str) # keyの作成
    repkey_out = pbl2.repkey(key, rec_file_name) # repkeyの作成
    msg = f'REP {file_name} {repkey_out}\n' # 要求メッセージ
    # print(msg)
    # print('request REP')
    return msg

# serverからのfileの受け取り
def receive_server_file(soc,s_data_num):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    if s_data_num==0: #新規ファイル作成
        com='wb'
    elif s_data_num>=1:#既存ファイルに追記
        com='ab'
    with open(rec_file_name, com) as f:
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む 

# ルーティングパケットの送受信
def exchange_Routepacket(ad1, ad2, ttl):
    global my_port_route
    if ttl == 0:
        mid_name = server_name
    else:
        mid_name = ad1
    
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((mid_name, mid_port)) # 送信するホストとコネクション

    # 送信するデータを配列に格納
    data = b"abcdefghijklmnopqrstuvwxyz" # 任意のデータ
    # 参照する経由番号
    relay_num = 1

    '''
    パケット
    (クライアント名, 1つめの経由するホスト(経由番号1),2つめの経由するホスト(経由番号2),
    サーバ名,任意データ,TTL,参照する経由番号,パケットの種類(Route(ルーティング用パケット) or Com(コマンド用パケット)), 
    送信用(req)or応答用(rep), クライアントのポート番号)
    '''

    info_pack = [my_name, ad1, ad2, server_name , data, ttl, relay_num, 'Route', 'req', my_port_route]
    info_pack = pickle.dumps(info_pack) # 配列全体をバイト列に変換
    start_time = time.time()
    client_socket.send(info_pack) # データ配列の送信
    client_socket.close()

    # info_packet(応答用)の受け取り
    client_socket_recv = socket(AF_INET, SOCK_STREAM)
    client_socket_recv.bind(('', my_port_route))
    my_port_route += 1
    client_socket_recv.listen(10)
    connection_socket, addr = client_socket_recv.accept()
    rep_info_pack = connection_socket.recv(1024)
    rep_info_pack = pickle.loads(rep_info_pack) #バイト列を配列に変換
    connection_socket.close()
    end_time = time.time()

    return rep_info_pack, (end_time-start_time)

# サーバに対して直接通信する経路を調べる
def routing_dir():
    ttl = 0
    # Route用パケットのやり取り
    future = tpe.submit(exchange_Routepacket, 'none', 'none', ttl)
    # my_port += 1
    futures.append(future)
    # rep_info_pack, rtt = future.result(timeout=TO_time) # 応答の受け取り(タイムアウト時間の設定)
    # ルートテーブルへ調べた経路と時間を追加

# ホスト1つを経由する場合の経路を調べる
def routing_1host():
    # global my_port
    # TCPで全てのホストに送信
    ttl = 1
    for ad in address:
        # 自分とサーバと同じ名前を持つ転送管理サーバ以外へ送信
        if my_name != ad and server_name != ad:
            # Route用パケットのやり取り
            future = tpe.submit(exchange_Routepacket, ad, 'none', ttl)
            futures.append(future)

# ホスト2つを経由する場合の経路を調べる
def routing_2host():
    # global my_port
    # TCPで全てのホストに送信
    ttl = 2
    for ad1 in address:
        if my_name != ad1 and server_name != ad1:
            for ad2 in address:
                if my_name != ad2 and server_name != ad2 and ad1 != ad2:
                    # Route用パケットのやり取り
                    future = tpe.submit(exchange_Routepacket, ad1, ad2, ttl)
                    # my_port += 1
                    futures.append(future)

# tpeの実行(Routeパケットの受け取り)
def recv_Route_packet(TO_time):
    for future in futures:
        try:
            rep_info_pack, rtt = future.result(timeout=TO_time)
            if(rtt <= TO_time):
                Route = [rtt, rep_info_pack[0],rep_info_pack[1],\
                        rep_info_pack[2], rep_info_pack[3]]
                RouteTable.append(Route)
        except:
            print('timeout erro or something else')

# SIZE応答からデータサイズを読み取り
def load_data_size(SIZE_msg):
    msg_list = SIZE_msg.split() # 空白で分割
    data_size = int(msg_list[2])
    return data_size

# SIZEパケットのやり取り(サーバ側へ最も速い経路をたどってSIZE要求をする)
def SIZE_cmd(RouteTable):
    if(RouteTable[0][2] == 'none'):
        # 直接SIZE要求
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_name, server_port))
        size_msg = SIZE(server_file_name)
        client_socket.send(size_msg.encode())
        
        # 応答受け取り
        SIZE_sentence = rec_res(client_socket)
        # print('SIZE_sentence', SIZE_sentence)
        data_size = load_data_size(SIZE_sentence)
        client_socket.close()

    else:
        # 転送管理サーバを挟んだサイズ要求
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((RouteTable[0][2], mid_port))
        SIZE_pack = [RouteTable[0][1],RouteTable[0][2],RouteTable[0][3], RouteTable[0][4],\
                        'SIZE', SIZE(server_file_name), 1, 'Com', 'req', my_port_size]
        # print('SIZE_packet', SIZE_pack)
        SIZE_pack = pickle.dumps(SIZE_pack) # 配列全体をバイト列に変換
        client_socket.send(SIZE_pack) # データ配列の送信
        client_socket.close()

        # サーバからの応答の受け取り
        client_socket_recv = socket(AF_INET, SOCK_STREAM)
        client_socket_recv.bind(('', my_port_size))
        client_socket_recv.listen(6)
        connection_socket, addr = client_socket_recv.accept()
        SIZE_sentence = rec_res(connection_socket)
        # print('SIZE_sentence', SIZE_sentence)
        data_size = load_data_size(SIZE_sentence)

        connection_socket.close()
    # パケットのサイズを返す
    return data_size

# GET_partialコマンド(送信)
def GET_part_send(client_socket, RouteTable, token_str, server_file_name, sep_data_s, sep_data_e, i):
    # GETコマンドをサーバ側へ直接
    if(RouteTable[i][2] == 'none'):
        get_msg = GET_part(server_file_name, token_str, sep_data_s, sep_data_e)
        client_socket.send(get_msg.encode())
        # client_socket.close()
    else:
        # print('GET sending to',RouteTable[i][2])
        # GET要求
        GET_pack = [RouteTable[i][1], RouteTable[i][2], RouteTable[i][3], RouteTable[i][4],\
                    'GET', GET_part(server_file_name, token_str, sep_data_s, sep_data_e), 1, 'Com', 'req', my_port_get]
        # print('GET_packet', GET_pack)
        GET_pack = pickle.dumps(GET_pack) # 配列全体をバイト列に変換
        client_socket.send(GET_pack) # データ配列の送信
        client_socket.close()

# GETpartialコマンド(受け取り)
def GET_part_rec(connection_socket, sep_data_s):
    # 応答の受け取り
    global sdata_num
    # スレッド内で書き込みの順番を間違えないように管理するため
    # 以下自分の順番が来るまでデータの受け取りを待機している
    # ファイル分割の先頭番目で自身が何番目のファイルかを判断している
    sentence = rec_res(connection_socket)
    str_array = sentence.split()
    # print('recv_sentence', str_array)
    recv_sep_data_s = str_array[4] 
    print('recv_sep_data_s', recv_sep_data_s)
    while (True):
        if str(sep_data_s[sdata_num]) == recv_sep_data_s:#順番が自分の番になったら
            # print(sentence)
            receive_server_file(connection_socket, sdata_num)
            connection_socket.close()
            sdata_num += 1
            break

# GETコマンド
def GET_part_cmd(RouteTable, token_str, server_file_name, data_size):
    sep_data_s=[] # 分けたデータの最初を入れる 
    sep_data_e=[] # 分けたデータの最後を入れる
    '''
    # データ分割(等分)
    for i in range(0,len(RouteTable)):
        # 使える転送管理サーバの数に応じて同量でデータ分割(帯域幅等で分割できるとより良い)
        if i == 0: 
            separate_data_s=0
        else:
            separate_data_s=separate_data_e+1
        separate_data_e=int((i+1)*(data_size/len(RouteTable)))
        print(f'sep{i} {separate_data_s} {separate_data_e}')
        sep_data_s.append(separate_data_s)
        sep_data_e.append(separate_data_e)
    '''

    # '''
    # データ分割(ルーティングパケットの往復時間依存)
    SumTime = 0
    ratio_list = []
    for i in range(0, len(RouteTable)):
        SumTime += RouteTable[i][0]
    
    print('routing Time:', SumTime)
    
    SumRatio = 0
    # 計測時間の逆数の比のリスト作成
    for i in range(0, len(RouteTable)):
        ratio_list.append(1. / RouteTable[i][0])
        SumRatio += (1. / RouteTable[i][0])

    for i in range(0,len(RouteTable)):
        if i == 0: 
            separate_data_s=0
        else:
            separate_data_s=separate_data_e+1
        separate_data_size = int(float(data_size)*((ratio_list[i]/ SumRatio)))
        if(i == len(RouteTable)-1):
            separate_data_e = data_size
        else:
            separate_data_e = separate_data_size + separate_data_s
        
        print(f'sep{i} {separate_data_s} {separate_data_e}')

        sep_data_s.append(separate_data_s)
        sep_data_e.append(separate_data_e)
    # '''
    print()
    
    # GETpartialコマンド
    GET_set_s=[] #get sendをまとめて管理　スレッド用
    GET_set_r=[] #get recをまとめて管理　スレッド用
    for i in range(0,len(RouteTable)):
        if(RouteTable[i][2] == 'none'):
            # 直接GET要求用ソケット
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect((server_name, server_port))
            # 受信用スレッド(サーバの直接GETの応答を受け取る用)
            GETr = threading.Thread(target=GET_part_rec, args=(client_socket,sep_data_s))
            GET_set_r.append(GETr)

        else:
            # midへのGET送信用ソケット
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect((RouteTable[i][2], mid_port))
        # 送信用スレッドをたてる
        GETs = threading.Thread(target=GET_part_send, args=(client_socket, RouteTable, token_str, \
            server_file_name, sep_data_s[i], sep_data_e[i], i))
        GET_set_s.append(GETs)
    start_time = time.time()
    for GETs in GET_set_s:# get sendを一斉に行う　
        GETs.start()
    
    print()
    client_socket_recv = socket(AF_INET, SOCK_STREAM)
    client_socket_recv.bind(('', my_port_get)) # 自身のポートをソケットに対応づける
    client_socket_recv.listen(7)

    for i in range(0, len(RouteTable)):
        if(RouteTable[i][2] == 'none'):
            # サーバから直接のGET受け取りスレッドはもう立ててある
            continue
        else:
            connection_socket, addr = client_socket_recv.accept()
            # 受信用スレッド
            GETr = threading.Thread(target=GET_part_rec, args=(connection_socket,sep_data_s))
            GET_set_r.append(GETr)
    
    print('sending GET PARTIAL Command')
    for GETr in GET_set_r:#get recを一斉に行う
        GETr.start()

    for GETr in GET_set_r:#get recが全部終わるまで待つ
        GETr.join()

    # my_port += 1
    return start_time

# REPコマンド
def REP_cmd(RouteTable, server_file_name):
    if(RouteTable[0][2] == 'none'):
        # 直接REP要求
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_name, server_port))
        rep_msg = REP(server_file_name)
        client_socket.send(rep_msg.encode())

        # REP応答受け取り
        REP_sentence = rec_res(client_socket)
        client_socket.close()
        end_time = time.time()
        print('REP_sentence', REP_sentence)
        return end_time
    
    else:
        # 中間サーバをはさんだREP要求
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((RouteTable[0][2], mid_port)) # 送信するホストとコネクション
        REP_pack = [RouteTable[0][1],RouteTable[0][2],RouteTable[0][3], RouteTable[0][4],\
                        'REP', REP(server_file_name), 1, 'Com', 'req', my_port_rep]
        # print('REP_packet', REP_pack)
        REP_pack = pickle.dumps(REP_pack) # 配列全体をバイト列に変換
        client_socket.send(REP_pack) # データ配列の送信
        client_socket.close()

        # REP応答の受け取り
        client_socket_recv = socket(AF_INET, SOCK_STREAM)
        client_socket_recv.bind(('', my_port_rep))
        client_socket_recv.listen(10)
        connection_socket, addr = client_socket_recv.accept()
        REP_sentence = rec_res(connection_socket)
        end_time = time.time()
        print(f'REP_sentence {REP_sentence}')
        connection_socket.close()

    return end_time  

if __name__ == '__main__':

    print('----sending infomation----')
    # 情報の出力
    print('my name(初期値)', my_name)
    print('my(client) port', my_port)

    print('server name', server_name)
    print('server port', server_port)
    
    print('mid_name', mid_name)
    print('mid_port', mid_port)
    
    print()

    # ---------ネットワークの状態を調べる--------------
    print('-----routing-----')
    # ThreadPoolExecutorでタイムアウトを実装している。(result()が同期処理らしいので実際にはスレッド化できていないかも)
    tpe = ThreadPoolExecutor(max_workers=26)
    futures = []
    # print('my_port', my_port)
    TO_time = 0.5 # タイムアウト時間
    routing_dir() # 0ホスト経由のルーティング
    print('routing dir completed')

    # print('my_port', my_port)
    routing_1host() # 1ホスト経由のルーティング
    # print('my_port', my_port)
    print('routing 1host completed')
    routing_2host() # 2ホスト経由のルーティング
    print('routing 2host completed')
    recv_Route_packet(TO_time)

    # タイムアウト内で送信できる経路がなかった場合
    while True:
        if(len(RouteTable) != 0):
            break
        TO_time += 0.5
        routing_dir() # 0ホスト経由のルーティング
        print('routing dir(again)')
        # print('my_port', my_port)
        routing_1host() # 1ホスト経由のルーティング
        # print('my_port', my_port)
        print('routing 1host(again)')
        routing_2host() # 2ホスト経由のルーティング
        print('routing 2host(again)')
        recv_Route_packet(TO_time)

    # ---------ダウンロードしたファイルをルーティングした経路で送信---------
    print('------download file------')
    print()

    RouteTable = sorted(RouteTable) # timeによってソート
    print('sorted RouteTable:')
    print(*RouteTable, sep='\n')

    # SIZEコマンド
    print('SIZE Command')

    data_size = SIZE_cmd(RouteTable)
    print('data_size:',data_size)
    print()
    print('GET Command')
    # print('my_port', my_port)
    
    # GETpartialコマンド
    start_time = GET_part_cmd(RouteTable, token_str, server_file_name, data_size)

    print()
    # REPコマンド
    print('REP Command')

    end_time = REP_cmd(RouteTable,server_file_name)

    print(f'time {end_time - start_time}')