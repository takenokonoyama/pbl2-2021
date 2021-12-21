# -*- coding: utf-8 -*-
# mids_pack.py
from socket import *
import sys
import threading  # for Thread()
import os
import pickle

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル
# mid_name = sys.argv[1]  # 中間サーバのホスト名あるいはIPアドレスを表す文字列
# mid_port = sys.argv[2] # 中間サーバのポート
# server_name = sys.argv[3] # サーバのホスト名
# server_port =  int(sys.argv[4]) # サーバのポート

cl_name = '' # クライアント名
cl_port = 53602 # クライアントのポート番号
my_name = 'pbl2' # 自身のサーバ名
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

def relay_packet(connect_soc):

    pack = connect_soc.recv(1024)
    pack = pickle.loads(pack) # 配列の受け取り

    print('packet : \n{0}'.format(pack))
    
    # ----Rooting用のパケットだった場合-----
    if(pack[7] == 'Root'):
        server_name = pack[3] # パケットからサーバ名の取得
        # print('server_name: ', server_name)
        if(pack[8] == 'req'):
            # TTL(pack[5])==2ならば、転送管理サーバへ送信
            if(pack[5] == 2):
                # 経由するホストが増えるのでrelay_num(info_pack[6])をインクリメント
                pack[6] += 1 
                pack[5] -= 1 # TTLをデクリメント
                mid_name = pack[pack[6]]
                soc_to_ser = socket(AF_INET, SOCK_STREAM)
                soc_to_ser.connect((mid_name, my_port))
                pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                soc_to_ser.send(pack) # データ配列の送信    
            
            # TTL(info_pack[5])==1ならばTTLを1つ減らして、サーバと同じ名前の転送管理サーバへ送信
            elif(pack[5] == 1):
                # 経由するホストが増えるのでrelay_num(info_pack[6])をインクリメント
                pack[6] += 1
                pack[5] -= 1 # TTLをデクリメント
                soc_to_ser = socket(AF_INET, SOCK_STREAM)
                soc_to_ser.connect((server_name, my_port))
                pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                soc_to_ser.send(pack) # データ配列の送信
                
            # TTL==0ならばその転送管理サーバはサーバと同じ名前をもつ
            elif(pack[5] == 0):
                pack[6] -= 1
                mid_name = pack[pack[6]] # 参照番号1 or 2を見る
                print(mid_name)
                soc_to_mid = socket(AF_INET, SOCK_STREAM)
                soc_to_mid.connect((mid_name, mid_port))
                pack[8] = 'rep' # パケットを応答用に変更
                pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                soc_to_mid.send(pack) # データ配列の送信

        elif(pack[8] == 'rep'):
            if(pack[6] == 1):
                pack[6] -= 1
                cl_name = pack[0] # クライアント名
                cl_port = pack[9] # クライアントのポート
                soc_to_cl = socket(AF_INET, SOCK_STREAM)
                soc_to_cl.connect((cl_name, cl_port))
                print("sending to client :",cl_name, cl_port)
                pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                soc_to_cl.send(pack) # データ配列の送信

            elif(pack[6] == 2):
                pack[6] -= 1
                mid_name = pack[pack[6]]
                print(mid_name)
                soc_to_mid = socket(AF_INET, SOCK_STREAM)
                soc_to_mid.connect((mid_name, mid_port))
                pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                soc_to_mid.send(pack) # データ配列の送信

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
                if(pack[4] == 'GET'):
                    print('received server file')
                    receive_server_file(soc_to_ser)
                print(sentence)

                # ----クライアントとのやり取り----
                cl_name = pack[0]
                cl_port = pack[9]
                soc_to_cl = socket(AF_INET, SOCK_STREAM)
                soc_to_cl.connect((cl_name, cl_port))  
                soc_to_cl.send(sentence.encode())
                if(pack[4] == 'GET'):
                    openfile(rec_file_name, soc_to_cl)
            else:
                # 転送管理サーバへパケットを送信
                if(pack[6] == 1):
                    pack[6] += 1 # 参照番号をインクリメント
                    mid_name = pack[pack[6]]
                    print(mid_name)
                    soc_to_mid = socket(AF_INET, SOCK_STREAM)
                    soc_to_mid.connect((mid_name, mid_port)) 
                    pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                    soc_to_mid.send(pack) # データ配列の送信  
                
                elif(pack[6] == 2):
                    pack[6] -= 1
                    # ----サーバに対するコマンド要求・受け取り--------
                    soc_to_ser = socket(AF_INET, SOCK_STREAM)
                    soc_to_ser.connect((server_name, server_port))
                    soc_to_ser.send(pack[5].encode())
                    sentence = rec_res(soc_to_ser)
                    if(pack[4] == 'GET'):
                        receive_server_file(soc_to_ser)                        

                    # ----転送管理サーバとのやり取り----
                    mid_name = pack[pack[6]]
                    soc_to_mid = socket(AF_INET, SOCK_STREAM)
                    soc_to_mid.connect((mid_name, mid_port))
                    pack[8] = 'rep' # パケットを応答用に変換
                    pack[5] = sentence
                    print(pack)
                    info_pack = pickle.dumps(pack) # 配列全体をバイト列に変換
                    soc_to_mid.send(info_pack) # データ配列の送信
                    if(pack[4] == 'GET'):
                        sentence = rec_res(soc_to_mid)
                        print(sentence)
                        openfile(rec_file_name,soc_to_mid)

        elif(pack[8] == 'rep'): # パケットが応答用
            if(pack[6] == 1):
                if(pack[4] == 'GET'):                        
                    sentence = 'Received packet\n'
                    connect_soc.send(sentence.encode())
                    receive_server_file(connect_soc)
                cl_name = pack[0]
                cl_port = pack[9]
                sentence = pack[5] # 
                soc_to_cl = socket(AF_INET, SOCK_STREAM)
                soc_to_cl.connect((cl_name, cl_port))  
                soc_to_cl.send(sentence.encode())
                if(pack[4] == 'GET'):
                    openfile(rec_file_name, soc_to_cl)
            
def openfile(file_name, soc) :
    path = os.getcwd()
    path +="/"
    path +=file_name
    # print(path)
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
    