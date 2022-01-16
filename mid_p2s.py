# -*- coding: utf-8 -*-
# mids_pack.py
from multiprocessing import connection
from socket import *
import sys
import threading  # for Thread()
import os
import pickle
import re
import subprocess
# --------------------------------------------------------------------------------------
# -------クライアント設定--------
cl_name = '' # クライアント名
cl_port = 53602 # クライアントのポート番号

# -------サーバ(転送管理サーバ)設定---------
my_name = os.uname()[1] # 自身のサーバ名
my_port =  53606 # 自身(転送管理サーバ)のポート
mid_port = my_port # 転送管理サーバのポートは共通
server_name = '' # サーバ名
server_port = 60623 # サーバポート

# -------コマンド用設定--------------------
BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル
rec_count = 0

# --------------------------------------------------------------------------------------

# 応答コードの受け取り
def rec_res(soc):
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        if(bytes([b]) == b'\n'):
            rec_str = recv_bytearray.decode()
            break
        recv_bytearray.append(b)
    # print('received response')
    return rec_str

def receive_server_file(soc, file_name):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(file_name,'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

# ping
def Ping_mid(ad, p_loss_lim):
    flg = False
    # 正規表現'%'が後ろにつく[0,100]の数字を検索するための正規表現オブジェクトを生成
    regex = re.compile(r'\d{1,3}(?=%)') 
    # ping -c 10 -w 1000 adrress
    
    ping = subprocess.run(
          ["ping", "-c", "20","-i", "0.2","-s","65507","-q", ad],
          stdout=subprocess.PIPE,     # 標準出力は判断のため保存
          stderr=subprocess.DEVNULL # 標準エラーは捨てる
    ) 
   
    """ 
    # ローカルデバック用
    ping = subprocess.run(
    ["ping", "-c", "10","-i", "0.2","-s","1000","-q", ad],
    stdout=subprocess.PIPE,     # 標準出力は判断のため保存
    stderr=subprocess.PIPE # 標準エラーは捨てる
    )  """
   
    output = ping.stdout.decode("cp932")
    # print(output)

    # outputからpacketlossを取り出すする
    packet_loss = regex.search(output)
    # pingコマンドが成功->パケットロス率を返す,失敗->パケットロス率を100％とする
    if packet_loss == None:
        return_p_loss = 100
    else:
        return_p_loss = float(packet_loss.group())

    if(return_p_loss <= p_loss_lim):
        # outputからrttの平均を取り出す
        i = output.find('rtt')
        rtt_info = output[i:]
        rtt_info = re.split('[/ ]', rtt_info)
        # print(rtt_info)
        rtt = float(rtt_info[7])
        flg = True
    else:
        rtt = 100000000
    
    print()
    print('ping to',ad)
    print('packetloss:',return_p_loss,'rtt',rtt, flg)
    print()

    return flg, rtt

# Routeパケットの送信に使う
def send_packet(soc, pack):
  # pack_array = pack # 
  pack_str = '/'.join(map(str,pack)) # 配列の要素を/で区切り、文字列にする
  pack_str += '\n'
  
  print()
  print('send_packet')
  print(pack_str)
  print()
  
  soc.send(pack_str.encode()) # データ配列の送信
  # soc.close()

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

# comパケットを適切な型に変換
def fix_com_packet(pack):
    pack[6] = int(pack[6])
    pack[9] = int(pack[9])

    return pack

# comパケットの送信に使う
def send_com_packet(soc, pack, file_name):
    pack_array = pack
    pack_str = '/'.join(map(str,pack))
    pack_str += '\n'
    soc.send(pack_str.encode()) # データ配列の送信
    
    print()
    print('send_com_packet')
    print(pack_str)
    print()

    if(pack_array[4] == 'GET'):
        # print('sending file to',name, file_name)
        openfile(file_name, soc)
    # soc.close()

def relay_packet(connect_soc):
    global rec_count # ファイル名の衝突を避けるためのカウント変数
    pack_string = rec_res(connect_soc) #　パケット(文字列区切り)受け取り
    print()
    print('recv_packet')
    print(pack_string)
    print()

    pack = pack_string.split('/') # /で区切ってリストに格納(各要素は文字列として認識される→intやboolに変換が必要)
    
    # -----Routing用のパケットだった場合-----
    if(pack[7] == 'Route'):
        """
        Route用パケット
        pack = [クライアント名, 経由する1ホスト目, 経由する2ホスト目, サーバ, パケット到達性フラグ, TTL\
                , 経由回数, パケットの種類(Route), 送信用(req) or 応答用(rep), クライアントのポート番号\
                , 指定した経路でのrttの累積]
        """
        # パケットの要素を適切な型に変換
        pack = fix_route_packet(pack)
        send_pack = pack # 送信用パケット
        
        server_name = pack[3] # パケットからサーバ名の取得
        cl_name = pack[0] # パケットからクライアント名を取得

        if(pack[8] == 'req'):
            # TTL(pack[5])==2ならば、転送管理サーバへ送信
            if(pack[5] == 2):
                mid_name = pack[pack[6]+1]
                flg_ping, rtt = Ping_mid(mid_name, 0)
                if(flg_ping):
                    send_pack[6] += 1 # relay_numをインクリメント
                    send_pack[5] -= 1 # TTLをデクリメント
                    # 経由するホストが増えるのでrelay_num(info_pack[6])をインクリメント
                    send_pack[10] += rtt
                    soc_to_mid = socket(AF_INET, SOCK_STREAM)
                    soc_to_mid.connect((mid_name, mid_port))
                    send_packet(soc_to_mid, send_pack)

                    # 転送管理サーバからの受け取り
                    pack_string = rec_res(soc_to_mid) #　パケット(文字列)受け取り
                    print()
                    print('recv_packet from mid')
                    print(pack_string)
                    print()
                    pack = pack_string.split('/') # /で区切ってリストに格納(各要素は文字列として認識される→intやboolに変換が必要)
                    pack = fix_route_packet(pack)
                    # connection_socketへ送信
                    send_pack = pack
                    send_pack[6] -= 1
                    send_packet(connect_soc, send_pack)
                    soc_to_mid.close()
                else:
                    send_pack[6] -= 1
                    send_pack[4] = False
                    send_pack[8] = 'rep'
                    cl_port = send_pack[9]
                    # soc_to_cl = socket(AF_INET, SOCK_STREAM)
                    # soc_to_cl.connect((cl_name, cl_port))
                    send_packet(connect_soc, send_pack)

            # TTL(info_pack[5])==1ならばTTLを1つ減らして、サーバと同じ名前の転送管理サーバへping
            # その後pingがタイムアウトorパケットロスしなければrouteパケットを転送管理サーバへ送信
            elif(pack[5] == 1):
                flg_ping, rtt = Ping_mid(server_name, 0)
                # pingで良い経路であると分かったらrttを加えて1コ前に戻る
                if(flg_ping):
                    send_pack[6] -= 1
                    send_pack[8] = 'rep'
                    send_pack[5] -= 1 # TTLをデクリメント
                    send_pack[10] += rtt
                    if(send_pack[send_pack[6]] == cl_name):
                        cl_port = send_pack[9]
                        # soc_to_cl = socket(AF_INET, SOCK_STREAM)
                        # soc_to_cl.connect((cl_name, cl_port))
                        send_packet(connect_soc, send_pack)
                    else:
                        mid_name = send_pack[send_pack[6]]
                        # soc_to_mid = socket(AF_INET, SOCK_STREAM)
                        # soc_to_mid.connect((mid_name, my_port))
                        send_packet(connect_soc, send_pack)
                # 悪い経路だったら到達性をFalseにして1コ前に戻る
                else: 
                    send_pack[6] -= 1
                    send_pack[4] = False # パケットが正当な経路で送られなかったのでFalse
                    send_pack[8] = 'rep'
                    send_pack[5] -= 1 # TTLをデクリメント

                    if(send_pack[send_pack[6]] == cl_name):
                        cl_port = send_pack[9]
                        # soc_to_cl = socket(AF_INET, SOCK_STREAM)
                        # soc_to_cl.connect((cl_name, cl_port))
                        send_packet(connect_soc, send_pack)
                    
                    else:
                        mid_name = send_pack[send_pack[6]]
                        # soc_to_mid = socket(AF_INET, SOCK_STREAM)
                        # soc_to_mid.connect((mid_name, my_port))
                        send_packet(connect_soc, send_pack)
    
    # ----コマンド用のパケットだった場合
    elif(pack[7] == 'Com'):

        pack = fix_com_packet(pack)
        send_pack = pack
        server_name = pack[3] # パケットからサーバ名の取得
        if(pack[8] == 'req'): # パケットが要求用
            # 経路が1ホスト経由だった場合
            if(pack[pack[6]+1] == 'none'): # pack[6](経由数) == 1である
                send_pack[6] += 1 # 経由数をインクリメント
                # ----サーバとのやり取り(コマンド要求・受け取り)--------
                soc_to_ser = socket(AF_INET, SOCK_STREAM)
                soc_to_ser.connect((server_name, server_port))
                req_sentence = pack[5]
                req_sentence += '\n'
                soc_to_ser.send(req_sentence.encode())
                sentence = rec_res(soc_to_ser) # コマンド応答
                print(sentence)
                sentence += '\n'                
                connect_soc.send(sentence.encode()) # クライアント側へ応答を返す
                
                if(pack[4] == 'GET'):
                    # print('received server file')
                    while True:
                        b = soc_to_ser.recv(1024)
                        connect_soc.send(b)
                        if(len(b) <= 0):
                            break
                soc_to_ser.close()
            
            else:
                # 転送管理サーバへパケットを送信
                if(pack[6] == 1):
                    send_pack[6] += 1 # 参照番号をインクリメント
                    mid_name = send_pack[send_pack[6]]                     
                    soc_to_mid = socket(AF_INET, SOCK_STREAM)
                    soc_to_mid.connect((mid_name, mid_port))
                    send_packet(soc_to_mid, send_pack)

                    # 転送管理サーバからの受け取り
                    pack_string = rec_res(soc_to_mid) #　パケット(文字列)受け取り
                    print()
                    print('recv_packet from mid')
                    print(pack_string)
                    print()
                    pack = pack_string.split('/') # /で区切ってリストに格納(各要素は文字列として認識される→intやboolに変換が必要)
                    pack = fix_com_packet(pack)
                    send_pack = pack
                    # クライアント側へファイルを送信
                    sentence = pack[5]
                    sentence += '\n'
                    connect_soc.send(sentence.encode())
                    if(pack[4] == 'GET'):
                        # print('received server file')
                        while True:
                            b = soc_to_mid.recv(1024)
                            connect_soc.send(b)
                            if(len(b) <= 0):
                                break
                
                elif(pack[6] == 2):
                    send_pack[6] -= 1
                    # ----サーバに対するコマンド要求・受け取り--------
                    soc_to_ser = socket(AF_INET, SOCK_STREAM)
                    soc_to_ser.connect((server_name, server_port))
                    req_sentence = pack[5]
                    req_sentence += '\n'
                    soc_to_ser.send(req_sentence.encode())
                    sentence = rec_res(soc_to_ser)

                    send_pack[5] = sentence
                    send_packet(connect_soc, send_pack)

                    if(pack[4] == 'GET'):
                        # print('received server file')
                        while True:
                            b = soc_to_ser.recv(1024)
                            connect_soc.send(b)
                            if(len(b) <= 0):
                                break
                    soc_to_ser.close()
    connect_soc.close()

def openfile(file_name, soc) :
    with open(file_name, 'rb') as f:
        s = f.read()
        soc.send(s)

def main():
    # -----転送管理サーバを経由してサーバとクライアントの通信をする----  
    my_socket = socket(AF_INET, SOCK_STREAM) 
    my_socket.bind(('', my_port)) # 自身のポートをソケットに対応づける
    my_socket.listen(5)

    print('The server is ready to receive info packet')

    while True:
        # クライアントからの接続があったら、それを受け付け、
        # そのクライアントとの通信のためのソケットを作る
        connection_socket, addr = my_socket.accept() # 送信元ホストとのコネクション  
        client_handler = threading.Thread(target=relay_packet, args=(connection_socket,))
        client_handler.start()  # スレッドを開始

if __name__ == '__main__':

    print("mid_name:", my_name)
    print("mid_port:", my_port)    
    
    main()
    