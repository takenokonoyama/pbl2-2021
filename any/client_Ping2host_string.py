# -*- coding: utf-8 -*-
# client.py

from concurrent import futures
from socket import *
import time
import sys
import pbl2
import threading
import os
from concurrent.futures import ThreadPoolExecutor
import subprocess
import re

# --------------------------------------------------------------------------------------

# -----クライアント設定------------
my_name = os.uname()[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
my_port = 53602 # クライアントのポート
my_port_route = 53670 # クライアントのポート(念のため)
my_port_size = 53640 # クライアントのポート(size)
my_port_get = 53639 # クライアントのポート(get)
my_port_rep = 53638 # クライアントのポート(rep)

# ---------サーバ(転送管理サーバ)設定-------------
server_name = sys.argv[1] # サーバのホスト名
server_port =  60623 # サーバのポート
server_file_name = sys.argv[2] # サーバ側にあるファイル名
mid_name = '' # 中間管理サーバの名前
mid_port = 53601 # 中管理サーバのポート

# ----- Route用設定-------------
RouteTable = [] # 調べた経路を保存するリスト
route_count = 0 
#address = ["pbl1","pbl2","pbl3","pbl4"] # ローカル環境のアドレス
address = ["pbl1a","pbl2a","pbl3a","pbl4a", "pbl5a","pbl6a","pbl7a"]
ad_first = [] # 送信する1つめのホストはpingによって絞る

# -------コマンド用設定------------
key = '' # トークンキー
token_str = sys.argv[3] # トークン文字列
sdata_num = 0 # ファイル受け取りを正当な順番でするために必要な変数
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル
BUFSIZE = 1024 # 受け取る最大のファイルサイズ
time_table = []
# ---------------------------------------------------------------------------------

# \nまでの文字列の受け取り(\nを含まない)
def rec_res(soc):
    # 応答コードの受け取り
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        if(bytes([b]) == b'\n'):
            rec_str = recv_bytearray.decode()
            print(rec_str)
            break
        recv_bytearray.append(b)
    # print('received')

    return rec_str

# SIZE(文字列生成)
def SIZE(file_name):
    # 要求
    msg = f'SIZE {file_name}' # 要求メッセージ
    # soc.send(msg.encode())
    # print('request SIZE')
    return msg

# GET(ALL)(文字列生成)
def GET_all(file_name, token_str):
    # 要求
    key = pbl2.genkey(token_str)
    msg = f'GET {file_name} {key} ALL' # 要求メッセージ
    # print('request GET ALL')
    return msg

# GET(PARTIAL)
def GET_part(file_name,token_str,sB, eB):
    # 要求
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}' # 要求メッセージ

    # print('request GET PARTIAL')
    return msg

# REP(文字列生成)
def REP(file_name):
    key = pbl2.genkey(token_str) # keyの作成
    repkey_out = pbl2.repkey(key, rec_file_name) # repkeyの作成
    msg = f'REP {file_name} {repkey_out}' # 要求メッセージ
    # print(msg)
    # print('request REP')
    return msg

# serverからのfileの受け取り
def receive_server_file(soc, s_data_num):
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

# routeパケットを適切な型に変換
def fix_route_packet(pack):
    if(pack[4] == 'False'):
        pack[4] = False
    elif(pack[4] == 'True'):
        pack[4] = True

    pack[5] = int(pack[5])
    pack[6] = int(pack[6])
    pack[9] = int(pack[9])
    pack[10] = float(pack[10])

    return pack

# ルーティングパケットの送受信
def exchange_Routepacket_ping(ad1, ad2, ttl, rtt):
    global my_port_route

    # -------Routeパケットの送信-------------
    # 宛先名の決定
    if ttl == 0:
        mid_name = server_name
    else:
        mid_name = ad1
    
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((mid_name, mid_port)) # 送信するホストとコネクション

    # パケット到達性フラグ
    flg_route = True
    # 経由回数
    relay_num = 1

    """
    Route用パケット
    pack = [クライアント名, 経由する1ホスト目, 経由する2ホスト目, サーバ, パケット到達性フラグ, TTL\
            , 経由回数, パケットの種類(Route), 送信用(req) or 応答用(rep), Route用のクライアントのポート番号\
            , 指定した経路でのrttの累積]
    """
    # パケットは / で区切る    
    info_pack = f"{my_name}/{ad1}/{ad2}/{server_name}/{flg_route}/{ttl}/{relay_num}/Route/req/{my_port_route}/{rtt}"
    info_pack += '\n'
    start_time = time.time()
    client_socket.send(info_pack.encode()) # データ配列の送信
    # 0, 1ホスト経由の場合
    """     
    if(ad2 == 'none'):
    rep_info =  rec_res(client_socket)
    end_time = time.time()
    # /で区切ってリストに格納(各要素は文字列として認識される→適切な型への変換が必要)
    rep_info_pack = rep_info.split('/')
    # 受け取ったパケットを適切な型変換
    rep_info_pack = fix_route_packet(rep_info_pack)
    client_socket.close() 
    """
     # 2ホスト経由の場合
    # else:
    client_socket.close()
    # -------Routeパケットの受け取り-------------
    client_socket_recv = socket(AF_INET, SOCK_STREAM)
    client_socket_recv.bind(('', my_port_route))
    my_port_route += 1
    client_socket_recv.listen(5)
    connection_socket, addr = client_socket_recv.accept()
    rep_info =  rec_res(connection_socket)
    end_time = time.time()
    # /で区切ってリストに格納(各要素は文字列として認識される→適切な型への変換が必要)
    rep_info_pack = rep_info.split('/')
    # 受け取ったパケットを適切な型変換
    rep_info_pack = fix_route_packet(rep_info_pack)
    connection_socket.close()

    return rep_info_pack, (end_time - start_time)
  
# ping
def Ping(ad):
    # 正規表現'%'が後ろにつく[0,100]の数字を検索するための正規表現オブジェクトを生成
    # regex = re.compile(r'\s[0-100](?=%)')
    regex = re.compile(r'\d{1,3}(?=%)')

    """    
    ping = subprocess.run(
          ["ping", "-c", "10","-i", "0.2","-s","65507","-q", ad],
          stdout=subprocess.PIPE,     # 標準出力は判断のため保存
          stderr=subprocess.DEVNULL # 標準エラーは捨てる
    )
    """
   
    # ローカルデバック用
    ping = subprocess.run(
    ["ping", "-c", "10","-i", "0.2","-s","1000","-q", ad],
    stdout=subprocess.PIPE,     # 標準出力は判断のため保存
    stderr=subprocess.PIPE # 標準エラーは捨てる
    ) 
    
    # pingの出力
    output = ping.stdout.decode("cp932")
    # print(output)
    # outputからパケロスの数値を抽出する
    packet_loss = regex.search(output)

    # pingコマンドが成功->パケットロス率を返す,失敗->パケットロス率を100％とする
    if packet_loss == None:
        return_p_loss = 100
    else:
        return_p_loss = float(packet_loss.group())
    
    # outputからrttを抽出する
    if(return_p_loss != 100):
        # outputからrttの平均を抽出する
        i = output.find('rtt')
        rtt_info = output[i:]
        rtt_info = re.split('[/ ]', rtt_info)
        # print(rtt_info)
        rtt = float(rtt_info[7])
    else:
        rtt = 1000000
    
    print()
    print('ping to',ad)
    print('packetloss:',return_p_loss,'rtt',rtt)
    print()

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

# ホスト1つを経由する場合の経路を調べる
def routing_1host():
    ttl = 1
    # 経路はあらかじめクライアント側で決定しておく
    # 自分とserver_nameを持つ転送管理サーバ以外へRoute用パケットを送信
    for ad, rtt in ad_first:
        if my_name != ad and server_name != ad:
            future = tpe.submit(exchange_Routepacket_ping, ad, 'none', ttl, rtt)
            futures.append(future)

# ホスト2つを経由する場合の経路を調べる
def routing_2host():
    # 経路はあらかじめクライアント側で決定しておく
    # 自分とserver_nameを持つ転送管理サーバ以外へRoute用パケットを送信
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
    global tmp
    for future in futures:
        try:
            # Routeの関数を並列実行
            rep_info_pack, time = future.result(timeout=TO_time)
            if(rep_info_pack[4] == True):
                '''
                ルーティング結果
                Route = [指定した経路での累積rtt, クライアント名, 経由する1ホスト目, 経由する2ホスト目, サーバ]
                '''
                time_table.append((time, rep_info_pack[10]))
                Route = [rep_info_pack[10], rep_info_pack[0],rep_info_pack[1],\
                        rep_info_pack[2], rep_info_pack[3]]
                # Routeテーブルに各経路でのルーティング結果を格納
                RouteTable.append(Route)
            # print('time', time,'rtt', rep_info_pack[10])
        except TimeoutError:
            print('Timeout Erro')
        except:
            print(sys.exc_info())

# SIZE応答からデータサイズを読み取り
def load_data_size(SIZE_msg):
    msg_list = SIZE_msg.split() # 空白で分割
    data_size = int(msg_list[2]) # size部分を取り出す
    return data_size

# SIZEパケットのやり取り(サーバ側へ最も速い経路をたどってSIZE要求をする)
def SIZE_cmd(RouteTable):

    # サーバ側に対して直接SIZEコマンドを実行
    if(RouteTable[0][2] == 'none'):
        # -------SIZEコマンド要求の送信---------
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_name, server_port))
        size_msg = SIZE(server_file_name)
        size_msg += '\n'
        client_socket.send(size_msg.encode())

        # -------SIZEコマンド応答の受け取り---------
        SIZE_sentence = rec_res(client_socket)
        # print('SIZE_sentence', SIZE_sentence)
        if SIZE_sentence[0:2] == "NG":
            print("check your filename and try again")
            sys.exit( )
        data_size = load_data_size(SIZE_sentence)
        client_socket.close()

    # 転送管理サーバを挟んだ経路でのサイズ要求
    else:        
        # -------SIZEパケットの送信---------
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((RouteTable[0][2], mid_port))
        relay_num = 1
        """
        SIZE用パケット
        SIZE_pack = [クライアント名, 経由する1ホスト目, 経由する2ホスト目, サーバ, コマンドの種類(SIZE), コマンド要求文字列, \
                        経由回数, パケットの種類(Com), 要求(req) or 応答(rep), size用のクライアントのポート番号]
        """
        SIZE_pack = f"{RouteTable[0][1]}/{RouteTable[0][2]}/{RouteTable[0][3]}/{RouteTable[0][4]}/SIZE/{SIZE(server_file_name)}/{relay_num}/Com/req/{my_port_size}"
        SIZE_pack += '\n'
        # print('SIZE_packet', SIZE_pack)
        client_socket.send(SIZE_pack.encode()) # データ配列の送信
        client_socket.close()

        # -------SIZEsentenceの受け取り---------
        # クライアント側にはSIZEコマンドの応答(string)が送られてくる
        client_socket_recv = socket(AF_INET, SOCK_STREAM)
        client_socket_recv.bind(('', my_port_size))
        client_socket_recv.listen(6)
        connection_socket, addr = client_socket_recv.accept()
        SIZE_sentence = rec_res(connection_socket)
        if SIZE_sentence[0:2] == "NG":
            print("check your filename and try again")
            sys.exit( )
        # print('SIZE_sentence', SIZE_sentence)
        data_size = load_data_size(SIZE_sentence) # データサイズの読み取り
        connection_socket.close()
    # パケットのサイズを返す
    return data_size

# GET_partialコマンド(送信)
def GET_part_send(client_socket, RouteTable, token_str, server_file_name, sep_data_s, sep_data_e, i):
    
    if(RouteTable[i][2] == 'none'):
        # -------GETコマンド要求の送信---------
        get_msg = GET_part(server_file_name, token_str, sep_data_s, sep_data_e)
        get_msg += '\n'
        client_socket.send(get_msg.encode())
    else:
        # -------GETパケット要求の送信---------
        """
        GET用パケット
        GET_pack = [クライアント名, 経由する1ホスト目, 経由する2ホスト目, サーバ, コマンドの種類(GET), コマンド要求文字列, \
                        経由回数, パケットの種類(Com), 要求(req) or 応答(rep), GET用のクライアントのポート番号]
        """
        GET_pack = f"{RouteTable[i][1]}/{RouteTable[i][2]}/{RouteTable[i][3]}/{RouteTable[i][4]}/GET/{GET_part(server_file_name, token_str, sep_data_s, sep_data_e)}/{1}/Com/req/{my_port_get}"
        GET_pack += '\n'
        client_socket.send(GET_pack.encode()) # データ配列の送信
        client_socket.close()

# GETpartialコマンド(受け取り)
def GET_part_rec(connection_socket, sep_data_s):
    # -------GET応答の受け取り---------
    global sdata_num
    sentence = rec_res(connection_socket)
    str_array = sentence.split()
    recv_sep_data_s = str_array[4]
    # スレッド内で書き込みの順番を間違えないように管理するため
    # ファイル分割の先頭番目で自身が何番目のファイルかを判断している
    while (True):
        if str(sep_data_s[sdata_num]) == recv_sep_data_s:# 順番が自分の番になったらファイル受け取り
            receive_server_file(connection_socket, sdata_num)
            connection_socket.close()
            sdata_num += 1
            print(f'Thread {sdata_num} end')
            break

# GETコマンド
def GET_part_cmd(RouteTable, token_str, server_file_name, data_size):
    print()
    print('separate data')
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

    # データ分割(ルーティングパケットの往復時間依存)
    ratio_list = []
    SumRatio = 0
    # (1 / 計測時間)のリスト作成
    for i in range(0, len(RouteTable)):
        ratio_list.append(1 / RouteTable[i][0]**2)
        SumRatio += (1 / RouteTable[i][0]**2)

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

        print(f'sep{i} data_size: {separate_data_e - separate_data_s}')

        sep_data_s.append(separate_data_s)
        sep_data_e.append(separate_data_e)
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
        rep_msg += '\n'

        client_socket.send(rep_msg.encode())
        REP_sentence = rec_res(client_socket)
        end_time = time.time()
        # print('REP_sentence', REP_sentence)
        client_socket.close()

        return end_time
    
    else:
        # REP要求用パケットの送信
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((RouteTable[0][2], mid_port)) # 送信するホストとコネクション
        """
        REP用パケット
        REP_pack = [クライアント名, 経由する1ホスト目, 経由する2ホスト目, サーバ, コマンドの種類(GET), コマンド要求文字列, \
                        経由回数, パケットの種類(Com), 要求(req) or 応答(rep), GET用のクライアントのポート番号]
        """
        REP_pack = f"{RouteTable[0][1]}/{RouteTable[0][2]}/{RouteTable[0][3]}/{RouteTable[0][4]}/REP/{REP(server_file_name)}/{1}/Com/req/{my_port_rep}"
        REP_pack += '\n'

        # print('REP_packet', REP_pack)
        client_socket.send(REP_pack.encode()) # データ配列の送信
        client_socket.close()

        # サーバからの応答の受け取り
        client_socket_recv = socket(AF_INET, SOCK_STREAM)
        client_socket_recv.bind(('', my_port_rep))
        client_socket_recv.listen(5)
        connection_socket, addr = client_socket_recv.accept()
        REP_sentence = rec_res(connection_socket)
        end_time = time.time()
        # print(f'REP_sentence {REP_sentence}')
        connection_socket.close()

    return end_time  

if __name__ == '__main__':
    # ---------ネットワークの状態を調べる--------------
    print('-----routing-----')
    # 全てのホストに対してPingを実行(並列処理)
    packet_info = Ping_AllHost() # tupuleで受け取り(パケロス, rtt)
    # 許容するパケットロスの上限(% 表示)
    packet_loss_limit = 3
    
    # clientからパケットを送るホストを決定する
    select_ad_first(packet_info, packet_loss_limit)

    # ThreadPoolExecutorでタイムアウトを実装している。
    tpe = ThreadPoolExecutor(max_workers=5)
    futures = []
    TO_time = 60 # 保険で60秒でタイムアウトするように設定

    # routing_dir()
    routing_1host() # 1ホスト経由のルーティング(関数をthread化)
    # routing_2host() # 2ホスト経由のルーティング(関数をthread化)
    recv_Route_packet(TO_time) # threadの実行(パケットの受け取り)
    print(time_table)
    # ---------ダウンロードしたファイルをルーティングした経路で送信---------    
    print('------download file------')
    
    RouteTable = sorted(RouteTable) # timeによってソート

    if(len(RouteTable) >= 2):
        tmp_RouteTable = RouteTable
        RouteTable = []
        for i in range(2):
            RouteTable.append(tmp_RouteTable[i])
    print()
    print('sorted RouteTable:')
    print(*RouteTable, sep='\n')
    print()

    # SIZEコマンド
    print()
    print('SIZE Command')
    # print('my_port', my_port)
    data_size = SIZE_cmd(RouteTable)
    print('data_size:',data_size)
    print()

    print()
    print('GET Command')
    # print('my_port', my_port)
    # GETpartialコマンド
    start_time = GET_part_cmd(RouteTable, token_str, server_file_name, data_size)
    print()
    
    print()
    # REPコマンド
    print('REP Command')
    end_time = REP_cmd(RouteTable,server_file_name)
    print(f'time {end_time - start_time}')
