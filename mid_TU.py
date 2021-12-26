# -*- coding: utf-8 -*-
# mids.py

from socket import *
import threading  # for Thread()
import os
import time

BUFSIZE = 1024 # 受け取る最大のファイルサイズ
rec_file_name = 'midreceived_data.dat' # 受け取ったデータを書き込むファイル

mid_name = os.uname()[1] # 中間サーバのホスト名あるいはIPアドレスを表す文字列

server_name = 0 # サーバのホスト名
server_port = 0 # サーバのポート
packet_sum = 10000
routing_time=10#経路作成する時間
thread = 0

mid_port = 53009
mid_port_UDP =53019

def rec_res(soc):
    # 応答コードの受け取り
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
    with open(rec_file_name, 'wb') as f: # 'wb' は「バイナリファイルを書き込みモードで」という意味
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

def mid_server(server_name, server_port,sentence,com):#中間サーバとサーバの通信
    mid_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    mid_socket.connect((server_name, server_port))#中間、サーバとのコネクト
    print('Sending to server: {0}'.format(sentence))
    print(server_name)
    print(server_port)

    if com =="SET":#サーバのない中間サーバからサーバのある中間サーバへの処理
        sentence=f"DEC {mid_name} \n"#自分の名前を添えてDECコマンドをサーバのある中間サーバへ
        mid_socket.send(sentence.encode())  
        rep = rec_res(mid_socket)
        rep = f"{rep[0:3]} {mid_name} \n"#返ってきたDECコマンドに自分の名前をつけて返信する。
    else:#SIZE,GET,REPのサーバへの通信
        mid_socket.send(sentence.encode())  
        rep = rec_res(mid_socket)
    print(rep)
    print(com)

    if com =="GET" :#GETはデータの受け取りの際に一行目応答、二行目データであるから二回受け取る必要あり
        receive_server_file(mid_socket)
        return rep

    mid_socket.close()
    return rep

def interact_with_client_TCP(soc):
    global server_name
    global server_port
    print("inter")
    sentence = rec_res(soc)
    print('Received: {0}'.format(sentence)) 
    print(sentence[0:3])
    com=sentence[0:3] 
    
    if com=="SET":#このコマンドでサーバ名とサーバポート番号が知れる
        server_name = blank_set(sentence,1)#sentenceの二単語目を使いたい
        server_port = int(blank_set(sentence,2))#sentenceの三単語目を使いたい　str型からint型へ
        print('server_name:',server_name) # サーバ名
        print('server_port:',server_port) # サーバポート番号
        if mid_name == server_name:#SETで送られてきたのがサーバのある中間サーバなら
            print("I am Server")

            rep_sentence=f"DEC {mid_name} \n"#DECコマンドをサーバのホストの名前をつけ返す
            soc.send(rep_sentence.encode())
        else :#SETで送られてきたのがサーバのない中間サーバだったら
            rep_sentence=mid_server(server_name, mid_port,sentence,com)
            #↑サーバのある中間サーバへの通信を始める。
            print('Sending to client: {0}'.format(rep_sentence))
            soc.send(rep_sentence.encode())

    elif com =="DEC":#基本今はサーバのある中間サーバが他の中間サーバから受け取ったDECコマンドへの処理
        rep_sentence=f"DEC {mid_name} \n"#サーバのある中間サーバはここだよって返信。DEC以外消されちゃうけど
        print('Sending to client: {0}'.format(rep_sentence))
        soc.send(rep_sentence.encode())
    elif com =="IAM" :#クライアントのある中間サーバはサーバの情報を格納するだけ
        server_name = blank_set(sentence,1)#sentenceの二単語目を使いたい
        server_port = int(blank_set(sentence,2))#sentenceの三単語目を使いたい
        print('server_name:',server_name,type(server_name)) # サーバ名
        print('server_port:',server_port,type(server_port)) # サーバポート番号
        pass
        
    else: #SIZE,GET,REPを中間サーバが受け取ったとき
        print(server_name,type(server_name))
        print(server_port,type(server_port))
        rep_sentence=mid_server(server_name, server_port,sentence,com)#中間サーバとサーバのやりとり
        print('Sending to client: {0}'.format(rep_sentence))
        soc.send(rep_sentence.encode())

        if com=="GET":
            #"midreceived_data.dat"を送りたい
            #現状ファイルの中身を一度開いて一文字ずつ送ってる
            openfile("midreceived_data.dat",soc)

        print("Finish Sending")
    soc.close()

def openfile(file_name,soc) :#fileを開き一文字ずつ送るための関数
    path=os.getcwd()
    print(path)
    path +="/"
    path +=file_name
    with open(path,'rb') as f:
        s = f.read()
        soc.send(s)

def blank_set(sentence,count_time):#文字列の一部分を取り出すための関数
    #取り出したい文字列とその文字列の何単語めかを引数にしてる。
    #DEC pbl1 pbl3　でpbl1を取り出したいならcount_timeは1
    rep_sentence=[]
    count=0
    i=0
    str=' '
    print(len(sentence)-1)
    #1,配列に文字を格納してから、2,配列を基に返信の文字列を作成
    #1,配列に文字を格納
    while i < len(sentence): #カウントするblanck 数
        if  str == sentence[i]:#空白をカウントしてる。
            count+=1
            i+=1
        if count == count_time:
            rep_sentence.append(sentence[i]) 
        i+=1

    #2,配列を基に返信の文字列を作成
    count=0
    for i in rep_sentence:#配列を基に返信の文字列を作成
        if count==0:
            rep=i
        else:
            rep+=i
        count+=1
    return rep #返されるのは取り出したい単語

def main_TCP(): #クライアントと中間サーバの通信
    mid_socket = socket(AF_INET, SOCK_STREAM) # ソケットを作る
    mid_socket.bind(('', mid_port))
    mid_socket.listen(6) #並列で6台まで処理できる
    print('The server is ready to receive by TCP')
    while True:
        # クライアントからの接続があったら、それを受け付け、
        # そのクライアントとの通信のためのソケットを作る
        connection_socket, addr = mid_socket.accept()  
        client_handler = threading.Thread(target=interact_with_client_TCP, args=(connection_socket,))
        client_handler.start()  # スレッドを開始

def main_UDP():
    mid_socket = socket(AF_INET, SOCK_DGRAM)
    print('The server is ready to receive by UDP')
    mid_socket.bind(('', mid_port_UDP))
    interact_with_client_UDP(mid_socket)
    mid_socket.close()

def interact_with_client_UDP(soc):
    # ソケットを用意
    global server_name
    global server_port

    count=0
    while True:
        # 受信
        rec, addr = soc.recvfrom(8192)
        rec_sentence=rec.decode()
        if count ==0 :
            s_time=time.time()
            server_name = blank_set(rec_sentence,1)#rec_sentenceの二単語目を使いたい
            server_port = int(blank_set(rec_sentence,2))#rec_sentenceの三単語目を使いたい
            packet_sum  = int(blank_set(rec_sentence,3))
            print(server_name,server_port, packet_sum)
        count+=1
        el_time=time.time()-s_time
        if count >= int(packet_sum/2)  or el_time > 5:
            break


    if server_name!=mid_name:
        sentence = f'UDP {server_name} {server_port} {packet_sum} \n'
        try:
            for i in range (packet_sum):#packet_sumの数だけ同じ文字を送ることでパケロス調べる
                soc.sendto(sentence.encode(),(server_name,mid_port_UDP))
        except OSError:
            pass
        
        print("lts server ")

        rec, addr = soc.recvfrom(8192)
        rec_sentence=rec.decode()
        mid=blank_set(rec_sentence,1)
        siz=int(blank_set(rec_sentence,2))
        print(count,siz)
        count=int((count+siz)/2)
    else:    
        print("im server")
    
    sentence = f"reply {mid_name} {count} \n"
    print("sentence:",sentence)
    print("st sendto",addr[0],addr[1])

    soc.sendto(sentence.encode(),(addr[0],addr[1]))
    print("fi sendto")
    print(mid_name)


if __name__ == '__main__':
    #print("mid_name:",mid_name)
    #print("mid_port:",mid_port)
    main_UDP()
    if mid_name == server_name:
        while True :
            main_UDP()
    print(server_name,server_port)
    main_TCP()