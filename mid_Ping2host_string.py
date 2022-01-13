# -*- coding: utf-8 -*-
# mids_pack.py
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
my_port =  53650 # 自身(転送管理サーバ)のポート
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
            ["ping", "-c", "10","-i", "0.2","-s", "65507","-q", ad],
            stdout=subprocess.PIPE,     # 標準出力は判断のため保存
            stderr=subprocess.PIPE
            # stderr=subprocess.DEVNULL # 標準エラーは捨てる
        )
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
    
    # print('packetloss:',return_p_loss, 'to', ad, flg)

    return flg, rtt

    '''
    packet_loss_list.extend(packet_loss)
    succeed = result.find('ttl=') > 0        # pingの実行結果に「ttl=」の文字列があればpingが成功していると判断
    list_result.append(0 if succeed else 1)  # pingが成功ならば 0 ,失敗ならば 1 と入力
    '''

# Routeパケットの送信に使う
def send_packet(name, port, pack):
  soc = socket(AF_INET, SOCK_STREAM)
  soc.connect((name, port))
  # pack_array = pack # 
  pack_str = '/'.join(map(str,pack)) # 配列の要素を/で区切り、文字列にする
  pack_str += '\n'
  # print(pack_str)
  soc.send(pack_str.encode()) # データ配列の送信
  soc.close()

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
def fic_com_packet(pack):
    pack[6] = int(pack[6])
    pack[9] = int(pack[9])

    return pack

# comパケットの送信に使う
def send_com_packet(name, port, pack, file_name):
  soc = socket(AF_INET, SOCK_STREAM)
  soc.connect((name, port))
  pack_array = pack
  pack_str = '/'.join(map(str,pack))
  pack_str += '\n'
  soc.send(pack_str.encode()) # データ配列の送信

  if(pack_array[4] == 'GET'):
      # print('sending file to',name, file_name)
      openfile(file_name, soc)
  soc.close()

def relay_packet(connect_soc):
    global rec_count # ファイル名の衝突を避けるためのカウント変数

    pack_string = rec_res(connect_soc) #　パケット(文字列区切り)受け取り
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
        
        server_name = pack[3] # パケットからサーバ名の取得
        cl_name = pack[0] # パケットからクライアント名を取得

        if(pack[8] == 'req'):
            # TTL(pack[5])==2ならば、転送管理サーバへ送信
            if(pack[5] == 2):
              mid_name = pack[pack[6]+1]
              flg_ping, rtt = Ping_mid(mid_name, 3)
              if(flg_ping):
                pack[6] += 1 # relay_numをインクリメント
                pack[5] -= 1 # TTLをデクリメント
                # 経由するホストが増えるのでrelay_num(info_pack[6])をインクリメント
                pack[10] += rtt
                send_packet(mid_name, my_port, pack)

              else:
                pack[6] -= 1
                pack[4] = False
                pack[8] = 'rep'
                cl_port = pack[9]
                send_packet(cl_name, cl_port, pack)

            # TTL(info_pack[5])==1ならばTTLを1つ減らして、サーバと同じ名前の転送管理サーバへping
            # その後pingがタイムアウトorパケットロスしなければrouteパケットを転送管理サーバへ送信
            elif(pack[5] == 1):
                flg_ping, rtt = Ping_mid(server_name, 3)
                # pingで良い経路であると分かったらrttを加えてパケットを送信
                if(flg_ping):
                  # 経由するホストが増えるのでrelay_num(info_pack[6])をインクリメント
                  pack[6] += 1
                  pack[5] -= 1 # TTLをデクリメント
                  pack[10] += rtt # rttを加算
                  send_packet(server_name, my_port, pack)
                
                # 悪い経路だったら1コ前に戻る
                else: 
                  pack[6] -= 1
                  pack[4] = False # パケットが正当な経路で送られなかったのでFalse
                  pack[8] = 'rep'
                  pack[5] -= 1 # TTLをデクリメント

                  if(pack[pack[6]] == cl_name):
                    cl_port = pack[9]
                    send_packet(cl_name, cl_port, pack)
                    
                  else:
                    mid_name = pack[pack[6]]
                    send_packet(mid_name, my_port, pack)

            # TTL==0ならばその転送管理サーバはサーバと同じ名前をもつ
            elif(pack[5] == 0):
                pack[6] -= 1
                # relay_num == 0 ならばサーバと直接通信のルーティング
                if(pack[6] == 0):
                    cl_name = pack[pack[6]]
                    cl_port = pack[9]
                    pack[8] = 'rep' # パケットを応答用に変更
                    send_packet(cl_name, cl_port, pack)
                else:
                    mid_name = pack[pack[6]]
                    # print(mid_name)
                    pack[8] = 'rep' # パケットを応答用に変更
                    send_packet(mid_name, mid_port, pack)

        elif(pack[8] == 'rep'):
            # 応答のとき、relay_num(pack[6])はhostの番号を指している
            pack[6] -= 1
            if(pack[6] == 0):
                cl_name = pack[0] # クライアント名
                cl_port = pack[9] # クライアントのポート
                send_packet(cl_name, cl_port, pack)
            
            elif(pack[6] == 1):
                mid_name = pack[pack[6]]
                # print(mid_name)
                send_packet(mid_name, mid_port, pack)

    # ----コマンド用のパケットだった場合
    elif(pack[7] == 'Com'):

        pack = fic_com_packet(pack)
        
        server_name = pack[3] # パケットからサーバ名の取得

        if(pack[8] == 'req'): # パケットが要求用
            # 経路が1ホスト経由だった場合
            if(pack[pack[6]+1] == 'none'): # pack[6](参照番号) == 1である
                pack[6] += 1 # 参照番号をインクリメント
                # ----サーバとのやり取り(コマンド要求・受け取り)--------
                soc_to_ser = socket(AF_INET, SOCK_STREAM)
                soc_to_ser.connect((server_name, server_port))
                req_sentence = pack[5]
                req_sentence += '\n'
                soc_to_ser.send(req_sentence.encode())
                sentence = rec_res(soc_to_ser)
                print(sentence)
                file_name = str(rec_count)+rec_file_name
                rec_count+=1
                if(pack[4] == 'GET'):
                    # print('received server file')
                    receive_server_file(soc_to_ser, file_name)
                soc_to_ser.close()

                # ----クライアントとのやり取り----
                cl_name = pack[0]
                cl_port = pack[9]
                sentence += '\n'
                soc_to_cl = socket(AF_INET, SOCK_STREAM)
                soc_to_cl.connect((cl_name, cl_port))  
                soc_to_cl.send(sentence.encode())
                
                if(pack[4] == 'GET'):
                   #  print('sending file to',cl_name, file_name)
                    openfile(file_name, soc_to_cl)
                soc_to_cl.close()
            else:
                # 転送管理サーバへパケットを送信
                if(pack[6] == 1):
                    pack[6] += 1 # 参照番号をインクリメント
                    mid_name = pack[pack[6]] 
                    send_packet(mid_name, my_port, pack)
                
                elif(pack[6] == 2):
                    pack[6] -= 1
                    # ----サーバに対するコマンド要求・受け取り--------
                    soc_to_ser = socket(AF_INET, SOCK_STREAM)
                    soc_to_ser.connect((server_name, server_port))
                    req_sentence = pack[5]
                    req_sentence += '\n'
                    soc_to_ser.send(req_sentence.encode())
                    sentence = rec_res(soc_to_ser)

                    file_name = str(rec_count)+rec_file_name
                    rec_count+=1
                    if(pack[4] == 'GET'):
                        # print('received server file')
                        receive_server_file(soc_to_ser, file_name)
                    soc_to_ser.close()

                    # ----転送管理サーバとのやり取り----
                    mid_name = pack[pack[6]]
                    pack[8] = 'rep' # パケットを応答用に変換
                    pack[5] = sentence
                    print('pack5',pack[5])
                    send_com_packet(mid_name, my_port, pack, file_name)

        elif(pack[8] == 'rep'): # パケットが応答用
            if(pack[6] == 1):
                file_name = str(rec_count)+rec_file_name
                rec_count+=1
                if(pack[4] == 'GET'):
                    receive_server_file(connect_soc, file_name)

                cl_name = pack[0]
                cl_port = pack[9]
                sentence = pack[5]
                sentence += '\n'

                soc_to_cl = socket(AF_INET, SOCK_STREAM)
                soc_to_cl.connect((cl_name, cl_port))  
                soc_to_cl.send(sentence.encode())
                if(pack[4] == 'GET'):
                    # ('sending file to',cl_name, file_name)
                    openfile(file_name, soc_to_cl)
                soc_to_cl.close()
    connect_soc.close()

def openfile(file_name, soc) :
    with open(file_name, 'rb') as f:
        s = f.read()
        soc.send(s)

def main():
    # -----転送管理サーバを経由してサーバとクライアントの通信をする----  
    my_socket = socket(AF_INET, SOCK_STREAM) 
    my_socket.bind(('', my_port)) # 自身のポートをソケットに対応づける
    my_socket.listen(10)

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
    