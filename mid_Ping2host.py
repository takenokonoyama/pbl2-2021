# -*- coding: utf-8 -*-
# mids_pack.py
from socket import *
import sys
import threading  # for Thread()
import os
import pickle
import re
import subprocess

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル
rec_count = 0
# mid_name = sys.argv[1]  # 中間サーバのホスト名あるいはIPアドレスを表す文字列
# mid_port = sys.argv[2] # 中間サーバのポート
# server_name = sys.argv[3] # サーバのホスト名
# server_port =  int(sys.argv[4]) # サーバのポート

cl_name = '' # クライアント名
cl_port = 53602 # クライアントのポート番号
my_name = os.uname()[1] # 自身のサーバ名
my_port =  53601 # 自身(転送管理サーバ)のポート
mid_port = my_port # 転送管理サーバのポートは共通
server_name = '' # サーバ名
server_port = 60623 # サーバポート

# 応答コードの受け取り
def rec_res(soc):
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        recv_bytearray.append(b)
        if(bytes([b]) == b'\n'):
            rec_str = recv_bytearray.decode()
            break
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
  regex = re.compile(r'[0-100](?=%)') 
  # ping -c 10 -w 1000 adrress

  ping = subprocess.run(
          ["ping", "-c", "10", "-W", "0.05","-i", "0.2","-s", "1000","-q", ad],
          stdout=subprocess.PIPE,     # 標準出力は判断のため保存
          stderr=subprocess.DEVNULL # 標準エラーは捨てる
      )
  output = ping.stdout.decode("cp932")
  print(output)

  # outputからrttの平均を抽出する
  i = output.find('rtt')
  rtt_info = output[i:]
  rtt_info = re.split('[/ ]', rtt_info)
  print(rtt_info)
  rtt = rtt_info[7]

  # outputからpacketlossを抽出する
  packet_loss = regex.search(output)

  # pingコマンドが成功->パケットロス率を返す,失敗->パケットロス率を100％とする
  if packet_loss == None:
      return_p_loss = 100
  else:
      return_p_loss = float(packet_loss.group())

  if(return_p_loss <= p_loss_lim):
    flg = True
  
  print('packetloss:',return_p_loss, 'to', ad)

  return flg, rtt

  '''
  packet_loss_list.extend(packet_loss)
  succeed = result.find('ttl=') > 0        # pingの実行結果に「ttl=」の文字列があればpingが成功していると判断
  list_result.append(0 if succeed else 1)  # pingが成功ならば 0 ,失敗ならば 1 と入力
  '''

def send_packet(name, port, pack):
  soc = socket(AF_INET, SOCK_STREAM)
  soc.connect((name, port))
  pack = pickle.dumps(pack) # 配列全体をバイト列に変換
  soc.send(pack) # データ配列の送信
  soc.close()

def relay_packet(connect_soc):
    global rec_count
    pack = connect_soc.recv(1024)
    pack = pickle.loads(pack) # 配列の受け取り

    # print('packet : \n{0}'.format(pack))
    
    # ----Routing用のパケットだった場合-----
    if(pack[7] == 'Route'):
        server_name = pack[3] # パケットからサーバ名の取得
        cl_name = pack[0] # パケットからクライアント名を取得
        # print('server_name: ', server_name)
        if(pack[8] == 'req'):
            # TTL(pack[5])==2ならば、転送管理サーバへ送信
            if(pack[5] == 2):
                # 経由するホストが増えるのでrelay_num(info_pack[6])をインクリメント
                pack[6] += 1 
                pack[5] -= 1 # TTLをデクリメント
                mid_name = pack[pack[6]]
                send_packet(mid_name, my_port,pack)
            
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
                
                # 悪い経路だったらクライアントに戻る
                else: 
                  pack[4] = False # パケットが正当な経路で送られなかったのでFalse
                  # pack[6] -= 1
                  # cl_name = pack[pack[6]]
                  cl_port = pack[9]

                  send_packet(cl_name,cl_port, pack)

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
                    send_packet(mid_name, mid_port)

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
        server_name = pack[3] # パケットからサーバ名の取得
        if(pack[8] == 'req'): # パケットが要求用
            # 経路が1ホスト経由だった場合
            if(pack[pack[6]+1] == 'none'): # pack[6](参照番号) == 1である
                pack[6] += 1 # 参照番号をインクリメント
                # ----サーバとのやり取り(コマンド要求・受け取り)--------
                soc_to_ser = socket(AF_INET, SOCK_STREAM)
                soc_to_ser.connect((server_name, server_port))
                soc_to_ser.send(pack[5].encode())
                sentence = rec_res(soc_to_ser)
                print(sentence)
                file_name = str(rec_count)+rec_file_name
                rec_count+=1

                if(pack[4] == 'GET'):
                    print('received server file')
                    receive_server_file(soc_to_ser, file_name)
                soc_to_ser.close()

                # ----クライアントとのやり取り----
                cl_name = pack[0]
                cl_port = pack[9]
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
                    # print(mid_name)
                    soc_to_mid = socket(AF_INET, SOCK_STREAM)
                    soc_to_mid.connect((mid_name, mid_port)) 
                    pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                    soc_to_mid.send(pack) # データ配列の送信  
                    soc_to_mid.close()
                
                elif(pack[6] == 2):
                    pack[6] -= 1
                    # ----サーバに対するコマンド要求・受け取り--------
                    soc_to_ser = socket(AF_INET, SOCK_STREAM)
                    soc_to_ser.connect((server_name, server_port))
                    soc_to_ser.send(pack[5].encode())
                    sentence = rec_res(soc_to_ser)

                    file_name = str(rec_count)+rec_file_name
                    rec_count+=1
                    if(pack[4] == 'GET'):
                        print('received server file')
                        receive_server_file(soc_to_ser, file_name)
                    soc_to_ser.close()
                    print(sentence)

                    # ----転送管理サーバとのやり取り----
                    mid_name = pack[pack[6]]
                    soc_to_mid = socket(AF_INET, SOCK_STREAM)
                    soc_to_mid.connect((mid_name, mid_port))
                    pack[8] = 'rep' # パケットを応答用に変換
                    pack[5] = sentence
                    # print(pack)
                    info_pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                    soc_to_mid.send(info_pack) # データ配列の送信
                    if(pack[4] == 'GET'):
                        sentence = rec_res(soc_to_mid)
                        # print(sentence)
                        print('sending file to',mid_name, file_name)
                        openfile(file_name, soc_to_mid)
                    soc_to_mid.close()

        elif(pack[8] == 'rep'): # パケットが応答用
            if(pack[6] == 1):
                file_name = str(rec_count)+rec_file_name
                rec_count+=1
                if(pack[4] == 'GET'):                        
                    sentence = 'Received packet\n'
                    connect_soc.send(sentence.encode())
                    receive_server_file(connect_soc, file_name)

                cl_name = pack[0]
                cl_port = pack[9]
                sentence = pack[5] # 
                soc_to_cl = socket(AF_INET, SOCK_STREAM)
                soc_to_cl.connect((cl_name, cl_port))  
                soc_to_cl.send(sentence.encode())
                if(pack[4] == 'GET'):
                    print('sending file to',cl_name, file_name)
                    openfile(file_name, soc_to_cl)
                soc_to_cl.close()
    
    connect_soc.close()
def openfile(file_name, soc) :

    # print(path)
    with open(file_name, 'rb') as f:
        s = f.read()
        soc.send(s) # 1文字ずつ送る
        
        # for line in f:
        #    soc.sendall(line) # 1列ずつ送る

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
    