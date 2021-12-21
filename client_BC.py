# -*- coding: utf-8 -*-
# client.py

from socket import *
import time
import sys
import pbl2
import os
import threading

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
client_name = os.uname()[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
server_name = sys.argv[1] # サーバのホスト名
server_port =  int(sys.argv[2]) # サーバのポート
server_file_name = sys.argv[3] # ファイル名
token_str = sys.argv[4] # トークン文字列
mid_name = "localhost" # 中間サーバのホスト名
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル
mids=[]
size=[]
data_size=0

mid_port = 53010


# 応答の受け取り
def rec_res(soc):
    # 応答コードの受け取り
    recv_bytearray = bytearray() # 応答コードのバイト列を受け取る配列
    while True:
        b = soc.recv(1)[0]
        if(bytes([b]) == b'\n'):
            recv_bytearray.append(b)
            rec_str = recv_bytearray.decode()
            break
        recv_bytearray.append(b)
    print('received response')
    print(rec_str)
    return rec_str

# SIZE 
def SIZE(soc, file_name):
    # 要求
    msg = f'SIZE {file_name}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request SIZE')
    
    # 応答の受け取り
    size_sentence=rec_res(soc)
    print(size_sentence[0:2])
    if size_sentence[0:2]=="OK": #SIZE要求がOKだった場合
        data_size_clt(size_sentence)
    soc.close()

def data_size_clt(size_sentence):#SIZE要求がOKだった場合にデータ量を計算する
    global size
    global data_size
    count=0
    i=0
    str=' '
    while count < 3: #データのサイズ欄を参照したい
        if  str==size_sentence[i]:#空白をカウントしてる。
            count+=1
            i+=1
        if count == 2:
            size.append(int (size_sentence[i])) #一回配列にいれてデータ量を把握
        i+=1
    
    count=1
    for i in size:#配列を基にデータ量の計算をする
        if count!=len(size) :
            data_size+=10**(len(size)-count)*i
            count+=1
        else:
            data_size+=i

# GET(ALL)
def GET_all(soc, file_name,token_str):
    # 要求
    key = pbl2.genkey(token_str)
    msg = f'GET {file_name} {key} ALL\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET ALL')
    
    # 応答の受け取り
    rec_res(soc)
    receive_server_file(soc)
    soc.close()

# GET(PARTIAL)
def GET_part(soc,file_name,token_str,sB, eB):
    # 要求
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET PARTIAL')

    # 応答の受け取り
    rec_res(soc)
    receive_server_file_a(soc)#正直ファイルの書き込みは新規じゃなくて追記で書き込んだ方が良い気がする
    soc.close()    

# REP
def REP(soc, file_name, token_str):
    key = pbl2.genkey(token_str) # keyの作成
    repkey_out = pbl2.repkey(key, rec_file_name) # repkeyの作成
    msg = f'REP {file_name} {repkey_out}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request REP')
    
    # 応答の受け取り
    rec_res(soc)
    soc.close()

# serverからのfileの受け取り
def receive_server_file(soc):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

# serverからのfileの受け取り GETPARTIAL用の追記
def receive_server_file_a(soc):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    with open(rec_file_name, 'ab') as f: # 'ab' は「バイナリファイルを上書き書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

def BC():#TCPでブロードキャストしようとした力技。ほんとはUDPでしたい。
    #しかしUDPでするなら全部書き換え必要。TCＰでタイムアウト処理を入れる方が簡単そう。
    global mid_name
    global mids
    ADDRESS = {"pbl1","pbl2","pbl3","pbl4"}#,"pbl5","pbl6","pbl7"}
    print("BC")
    command1 = f'SET {server_name} {server_port}\n'#クライアント以外に送るメッセージ
    command2 = f'IAM {server_name} {server_port}\n'#クライアントで働く中間サーバへ
    for address in ADDRESS:#絶対タイムアウトいれよう。コネクトを確率それぞれさせてる
        if client_name != address :
            try :
                client_socket = socket(AF_INET, SOCK_STREAM) 
                client_socket.connect((address, mid_port))
                client_socket.send(command1.encode())
                print("sending:","to",address,command1)
                rep=rec_res(client_socket)
                mid_name=rep[3:7] #どこから送られてきたのか
                mids.append(mid_name)#通信できた中間サーバを記録
                print(mids)
                print(len(mids))
                print(rep)
            except OSError:
                print("Can't send to",address)
        else :
            try :#クライアントの中間サーバは働かない
                client_socket = socket(AF_INET, SOCK_STREAM) 
                client_socket.connect((address, mid_port))
                client_socket.send(command2.encode())
                print("sending:","to",address,command2)
            except OSError:
                print("Can't send to",address)

    client_socket.close()

def BCmain():#スレッドでコネクトすれば安定してコネクトできる説
    client_socket = socket(AF_INET, SOCK_STREAM) 
    client_handler = threading.Thread(target=BC, args=(client_socket,))
    client_handler.start()

def commandMain(key):#key =0 direct server key=1 midserver 
    # SIZE 
    mid_name=mids[0] #一番早くコネクトした
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key == 1:
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    SIZE(client_socket, server_file_name) # SIZEコマンド

    """
    # GET(ALL)
    # 要求を2つ以上行う場合、ソケットをもう一度作る必要がある
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key == 1:
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    
    GET_all(client_socket, server_file_name, token_str) # GET(ALL)コマンド

    """
    # GET(PARTIAL)
    os.remove(rec_file_name)#ファイルの削除　追記のためまっさらなファイルがいい。テスト用
    half_size=int(data_size/2)
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((mids[0], mid_port))  # サーバのソケットに接続する
    GET_part(client_socket, server_file_name, token_str, 0, half_size) # GET(PARTIAL)コマンド
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((mids[1], mid_port))  # サーバのソケットに接続する
    GET_part(client_socket, server_file_name, token_str,half_size+1, data_size) # GET(PARTIAL)コマンド


    # REP
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key == 1:
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    REP(client_socket, server_file_name, token_str) # REPコマンド

if __name__ == '__main__':
    BC()

    print('server_name:',server_name) # サーバ名
    print('server_port:',server_port) # サーバポート番号 
    
    print()
    
    print('mid_name:',mid_name) # 中間サーバ名
    print('mid_port:',mid_port) # 中間サーバポート番号 
    
    print()
    
    commandMain(1)

    