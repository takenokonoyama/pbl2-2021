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
import subprocess
import re

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
my_name = os.uname()[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
my_port = 53602 # クライアントのポート
my_port_route = 53605 # クライアントのポート
my_port_size = 53604
my_port_get = 53603
my_port_rep = 53602
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
route_count = 0 
# address = ["pbl1","pbl2","pbl3","pbl4"] # ローカル環境のアドレス
address = ["pbl1a","pbl2a","pbl3a","pbl4a", "pbl5a","pbl6a","pbl7a"]
ad_first = [] # 送信する1つめのホストはpingによって絞る

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
def exchange_Routepacket_ping(ad1, ad2, ttl, rtt):
    global my_port_route
    if ttl == 0:
        mid_name = server_name
    else:
        mid_name = ad1
    
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((mid_name, mid_port)) # 送信するホストとコネクション

    # パケットが正当な経路で送られたかを判断
    flg_route = True
    # 参照する経由番号
    relay_num = 1
    '''
    パケット
    (クライアント名, 1つめの経由するホスト(経由番号1),2つめの経由するホスト(経由番号2),
    サーバ名,任意データ,TTL,参照する経由番号,パケットの種類(Route(ルーティング用パケット) or Com(コマンド用パケット)), 
    送信用(req)or応答用(rep), クライアントのポート番号)
    '''

    info_pack = [my_name, ad1, ad2, server_name , flg_route, ttl, relay_num, 'Route', 'req', my_port_route, rtt]
    info_pack = pickle.dumps(info_pack) # 配列全体をバイト列に変換
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

    return rep_info_pack

# ping
def Ping(ad):
    # 正規表現'%'が後ろにつく[0,100]の数字を検索するための正規表現オブジェクトを生成
    regex = re.compile(r'\s[0-100](?=%)') 
    # ping -c 10 -w 1000 adrress
    
    ping = subprocess.run(
            ["ping", "-c", "10","-i", "0.2","-s","65507","-q", ad],
            stdout=subprocess.PIPE,     # 標準出力は判断のため保存
            stderr=subprocess.PIPE # 標準エラーは捨てる
        )
    output = ping.stdout.decode("cp932")
    print(output)
    # outputからpacketlossを抽出する
    packet_loss = regex.search(output)
    # pingコマンドが成功->パケットロス率を返す,失敗->パケットロス率を100％とする
    if packet_loss == None:
        return_p_loss = 100
    else:
        return_p_loss = float(packet_loss.group())
    
    if(return_p_loss != 100):
        # outputからrttの平均を抽出する
        i = output.find('rtt')
        rtt_info = output[i:]
        rtt_info = re.split('[/ ]', rtt_info)
        print(rtt_info)
        rtt = float(rtt_info[7])
    else:
        rtt = 1000000
    print('packetloss:',return_p_loss, 'to', ad)

    return ad, return_p_loss, rtt

    '''
    packet_loss_list.extend(packet_loss)
    succeed = result.find('ttl=') > 0        # pingの実行結果に「ttl=」の文字列があればpingが成功していると判断
    list_result.append(0 if succeed else 1)  # pingが成功ならば 0 ,失敗ならば 1 と入力
    '''

# すべてのホストにPing(並列処理)
def Ping_AllHost():
    with ThreadPoolExecutor(max_workers = 10) as executor:
        # tupleで受けとり
        route_info = list(executor.map(Ping, (ad for ad in address)))
    
    return route_info

# ad_firstを選択
def select_ad_first(route_info, p_loss_lim):
    for ad, p_loss, rtt in route_info:
        if(p_loss <= p_loss_lim):
            if(ad == server_name):
                RouteTable.append([rtt, my_name, 'none', 'none', \
                                server_name])
            ad_first.append((ad, rtt)) # tupleでappendする

# サーバに対して直接通信する経路を調べる
def routing_dir():
    # ad_firstにserver_nameが入っていないならば実行しない
    flg = False
    i = 0
    for ad, t in ad_first:
        if(ad == server_name):
            flg = True
            rtt = t
    if(flg):
        ttl = 0
        # Route用パケットのやり取り
        future = tpe.submit(exchange_Routepacket_ping, 'none', 'none', ttl, int(rtt))

        futures.append(future)
        
        ''' 
        rep_info_pack = future.result() # 応答の受け取り
        # ルートテーブルへ調べた経路と時間を追加
        Route = [rep_info_pack[0],rep_info_pack[1],\
                rep_info_pack[2], rep_info_pack[3]]
        RouteTable.append(Route)
        print('send Route packet')'''

        # print(rep_info_pack)
        # print(RouteTable)
        # print("time : {0}".format(end_time - start_time))

# ホスト1つを経由する場合の経路を調べる
def routing_1host():
    # TCPで全てのホストに送信
    ttl = 1
    for ad, rtt in ad_first:
        # 自分とサーバと同じ名前を持つ転送管理サーバ以外へ送信
        if my_name != ad and server_name != ad:
            # Route用パケットのやり取り
            future = tpe.submit(exchange_Routepacket_ping, ad, 'none', ttl, rtt)
            futures.append(future)

# ホスト2つを経由する場合の経路を調べる
def routing_2host():
    # TCPで全てのホストに送信
    ttl = 2
    for ad1, rtt in ad_first:
        if my_name != ad1 and server_name != ad1:
            for ad2 in address:
                if my_name != ad2 and server_name != ad2 and ad1 != ad2:
                    # Route用パケットのやり取り
                    future = tpe.submit(exchange_Routepacket_ping, ad1, ad2, ttl, rtt)
                    futures.append(future)

# tpeの実行(Routeパケットの受け取り)
def recv_Route_packet(TO_time):
    global route_count
    for future in futures:
        try:
            rep_info_pack = future.result(timeout=TO_time)
            if(rep_info_pack[4] == True):
                route_count += 1

                Route = [rep_info_pack[10],rep_info_pack[0],rep_info_pack[1],\
                        rep_info_pack[2], rep_info_pack[3]]
                RouteTable.append(Route)
            print(rep_info_pack)
        except:
            print('timeout or something else')

# SIZE応答からデータサイズを読み取り
def load_data_size(SIZE_msg):
    msg_list = SIZE_msg.split() # 空白で分割
    data_size = int(msg_list[2])
    return data_size

# SIZEパケットのやり取り(サーバ側へ最も速い経路をたどってSIZE要求をする)
def SIZE_cmd(RouteTable):
    # 直接SIZE要求
    if(RouteTable[0][2] == 'none'):
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_name, server_port))
        size_msg = SIZE(server_file_name)
        client_socket.send(size_msg.encode())

        SIZE_sentence = rec_res(client_socket)
        # print('SIZE_sentence', SIZE_sentence)
        data_size = load_data_size(SIZE_sentence)
        client_socket.close()

    # 転送管理サーバを挟んでサイズ要求
    else:
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
    
    if(RouteTable[i][2] == 'none'):
        get_msg = GET_part(server_file_name, token_str, sep_data_s, sep_data_e)
        client_socket.send(get_msg.encode())
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
    recv_sep_data_s = str_array[4] 
    
    # print(recv_sep_data_s)
    while (True):
        if str(sep_data_s[sdata_num]) == recv_sep_data_s:#順番が自分の番になったら
            # print(sentence)
            receive_server_file(connection_socket, sdata_num)
            connection_socket.close()
            sdata_num += 1
            print(f'Thread {sdata_num} end')
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
    # (合計時間 / 計測時間)のリスト作成
    for i in range(0, len(RouteTable)):
        ratio_list.append(SumTime / RouteTable[i][0])
        SumRatio += (SumTime / RouteTable[i][0])

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
            # 直接GET要求
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect((server_name, server_port))
            # 受信用スレッド(直接GETの応答を受け取る用)
            GETr = threading.Thread(target=GET_part_rec, args=(client_socket,sep_data_s))
            GET_set_r.append(GETr)

        else:
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect((RouteTable[i][2], mid_port))
        # 送信用スレッド
        GETs = threading.Thread(target=GET_part_send, args=(client_socket, RouteTable, token_str, \
            server_file_name, sep_data_s[i], sep_data_e[i], i))
        GET_set_s.append(GETs)
    start_time = time.time()

    for GETs in GET_set_s:# get sendを一斉に行う　
        GETs.start()
    
    client_socket_recv = socket(AF_INET, SOCK_STREAM)
    client_socket_recv.bind(('', my_port_get)) # 自身のポートをソケットに対応づける
    client_socket_recv.listen(5)

    for i in range(0, len(RouteTable)):
        if(RouteTable[i][2] == 'none'):
            continue
        else:
            connection_socket, addr = client_socket_recv.accept()
            # 受信用スレッド
            GETr = threading.Thread(target=GET_part_rec, args=(connection_socket,sep_data_s))
            GET_set_r.append(GETr)
    
    for GETr in GET_set_r:#get recを一斉に行う
        GETr.start()
    print('sending GET PARTIAL Command')

    for GETr in GET_set_r:#get recが全部終わるまで待つ
        GETr.join()
    return start_time

# REPコマンド
def REP_cmd(RouteTable, server_file_name):
    # 直接REP要求
    if(RouteTable[0][2] == 'none'):
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_name, server_port))
        rep_msg = REP(server_file_name)
        client_socket.send(rep_msg.encode())

        REP_sentence = rec_res(client_socket)
        end_time = time.time()
        print('REP_sentence', REP_sentence)
        client_socket.close()

        return end_time
    
    else:
        # REP要求用パケットの送信
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((RouteTable[0][2], mid_port)) # 送信するホストとコネクション
        REP_pack = [RouteTable[0][1],RouteTable[0][2],RouteTable[0][3], RouteTable[0][4],\
                        'REP', REP(server_file_name), 1, 'Com', 'req', my_port_rep]
        # print('REP_packet', REP_pack)
        
        REP_pack = pickle.dumps(REP_pack) # 配列全体をバイト列に変換
        client_socket.send(REP_pack) # データ配列の送信
        client_socket.close()

        # サーバからの応答の受け取り
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
    # 全てのホストに対してPingを実行(並列処理)
    packet_info = Ping_AllHost() # tupuleで受け取り(パケロス, rtt)
    print(packet_info)
    # 許容するパケットロスの上限(% 表示)
    packet_loss_limit = 3
    
    # clientからパケットを送るホストを決定する
    select_ad_first(packet_info, packet_loss_limit)

    # ThreadPoolExecutorでタイムアウトを実装している。
    tpe = ThreadPoolExecutor(max_workers=5)
    futures = []
    TO_time = 60 # 保険で5秒でタイムアウトするように設定
    print(ad_first)

    routing_1host() # 1ホスト経由のルーティング(関数をthread化)
    print('routing 1host')
    routing_2host() # 2ホスト経由のルーティング(関数をthread化)
    print('routing 2host')
    recv_Route_packet(TO_time) # threadの実行(パケットの受け取り)

    # ---------ダウンロードしたファイルをルーティングした経路で送信---------    
    print('------download file------')
    print('RouteTable:')
    print(*RouteTable, sep='\n')

    RouteTable = sorted(RouteTable) # timeによってソート
    if(len(RouteTable) >= 2):
        tmp_RouteTable = RouteTable
        RouteTable = []
        for i in range(2):
            RouteTable.append(tmp_RouteTable[i])
    
    print('sorted RouteTable:')
    print(*RouteTable, sep='\n')

    # SIZEコマンド
    print('SIZE Command')
    # print('my_port', my_port)
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
    # print('my_port', my_port)
    end_time = REP_cmd(RouteTable,server_file_name)

    print(f'time {end_time - start_time}')