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
mid_name = os.uname()[1] # 中間サーバのホスト名
rec_file_name = 'received_data.dat' # 受け取ったデータを書き込むファイル
mids=[] #使える中間サーバを格納する
data_size=0 #GETでデータを分割してDLするためにSIZEでデータ量を格納する
thread=1 #GET PARTIALでファイルに書き込みする時に順番を崩さないため
route_timeout=0 #経路作成時、スレッドのタイムアウトを行なうため
timeout_time=10 #経路作成のタイムアウトする時間。変動できるようにした

mid_port = 53011


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
    global data_size
    size=[]
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

def blank_set(sentence,count_time):#文字列の一部分を取り出すための関数
    #取り出したい文字列とその文字列の何単語めかを引数にしてる。
    #DEC pbl1 pbl3　でpbl1を取り出したいならcount_timeは1
    rep_sentence=[]
    count=0
    i=0
    str=' '
    print(len(sentence)-1)
    while i < len(sentence): #カウントするblanck 数
        if  str == sentence[i]:#空白をカウントしてる。
            count+=1
            i+=1
        if count == count_time:
            rep_sentence.append(sentence[i]) 
        i+=1

    count=0
    for i in rep_sentence:#配列を基に返信の文字列を作成
        if count==0:
            rep=i
        else:
            rep+=i
        count+=1
    return rep #返されるのは取り出したい単語

# GET(ALL)
def GET_all(soc, file_name,token_str):
    # 要求
    key = pbl2.genkey(token_str)
    msg = f'GET {file_name} {key} ALL\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET ALL')
    
    # 応答の受け取り
    rec_res(soc)
    receive_server_file(soc,1)
    soc.close()

# GET(PARTIAL)
def GET_part_send(soc,file_name,token_str,sB, eB):
    # 要求
    key = pbl2.genkey(token_str) # keyの作成
    msg = f'GET {file_name} {key} PARTIAL {sB} {eB}\n' # 要求メッセージ
    soc.send(msg.encode())
    print('request GET PARTIAL')
  
def GET_part_rec(soc,order):
    # 応答の受け取り
    global thread 
    #スレッド内で書き込みの順番を間違えないように管理するため
    #以下自分の順番が来るまでデータの受け取りを待機している
    while(True):
        if order == thread:#順番が自分の番になったら
            rec_res(soc)
            receive_server_file(soc,order)#正直ファイルの書き込みは新規じゃなくて追記で書き込んだ方が良い気がする
            soc.close()
            thread+=1
            break    

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
def receive_server_file(soc,order):
    # 書き込み用ファイルをオープンして処理
    #   ファイル絡みの例外処理とクローズの処理は書く必要がありません
    if order==1: #新規ファイル作成
        com='wb'
    elif order>=2:#既存ファイルに追記
        com='ab'
    with open(rec_file_name, com) as f:
        while True:
            data = soc.recv(BUFSIZE)   # BUFSIZEバイトずつ受信
            if len(data) <= 0:  # 受信したデータがゼロなら、相手からの送信は全て終了
                break
            f.write(data)  # 受け取ったデータをファイルに書き込む

def BCmain(address):#スレッドでコネクトすれば安定してコネクトできる説
    global route_timeout #経路作成時のタイムアウトをスレッドで実行するためのもの　0 :中間サーバの追加可能 1:中間サーバの追加をやめる
    #時間制限で中間サーバを追加する理由は帯域幅が極端に狭い経路を排除したいから
    connect=[]#帯域幅が広めの中間サーバを保存する配列
    for i in range(0,len(address)) :
        print(i,address[i])
        c = threading.Thread(target=BCth, args=(address[i],))
        connect.append(c)
        print(connect[i])
        connect[i].start()#配列に格納次第スレッド開始
    for i in range(0,len(address)) :
        connect[i].join(timeout = 2*timeout_time)#タイムアウト時間を設定　パラメータはよく考えるべき
    route_timeout=1 #経路作成のタイムアウト。スレッドは動いたままだが中間サーバの追加は終了
    


def BCth(address):# thはthreadの略
    global mids
    global timeout_time #タイムアウトの時間をスレッドの中からでも変更できるようにしたいから
    client_socket = socket(AF_INET, SOCK_STREAM) 
    command1 = f'SET {server_name} {server_port}\n'#クライアント以外で働く中間サーバへ送るメッセージ
    command2 = f'IAM {server_name} {server_port}\n'#クライアントで働く中間サーバへ
    if client_name != address :
        try :
            start_time=time.time()
            client_socket.connect((address, mid_port))
            client_socket.send(command1.encode())
            print("sending:","to",address,command1)
            rep=rec_res(client_socket)
            mid_name=blank_set(rep,1)#どこから送られてきたのか
            if route_timeout==0: #タイムアウトでなければ中間サーバ追加
                if len(mids) == 0:#一番最初にconnect出来た時
                    timeout_time=time.time()-start_time
                    #ここで一番最初にconnectした中間サーバを基準にconnectのタイムアウト時間を設定している
                    print(timeout_time)
                mids.append(mid_name)#時間内に通信できた中間サーバを記録
                print(mids)
                print(len(mids))
                print(rep)
        except OSError:
             print("Can't send to",address)
    else :
        try :#クライアントの中間サーバは働かない 
            client_socket.connect((address, mid_port))
            client_socket.send(command2.encode())
            print("sending:","to",address,command2)
        except OSError:
            print("Can't send to",address)

    client_socket.close()


def commandMain(): 
    global Comp_start
    global Comp_end

    key=len(mids) #使える経路の数で決まる
    #key =0 directでserverと通信 key>=1 serverと通信する際に挟むmidserverの数

    # SIZE 
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key >= 1:
        mid_name=mids[0] #一番早くコネクトした中間サーバを用いて通信
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    SIZE(client_socket, server_file_name) # SIZEコマンド
    
    # GET(ALL)
    # 要求を2つ以上行う場合、ソケットをもう一度作る必要がある
    if key == 0 :
        client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
        GET_all(client_socket, server_file_name, token_str) # GET(ALL)コマンド
        Comp_start=time.time()
        print("Comp_start",Comp_start)
    elif key == 1:
        start=time.time()
        client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
        client_socket.connect((mids[0], mid_port))  #中間サーバ―と通信する場合
        GET_all(client_socket, server_file_name, token_str) # GET(ALL)コマンド
        end=time.time()
        print(end-start)
        Comp_start=time.time()
        print("Comp_start",Comp_start)
    elif key >= 2:
        start=time.time()

        sep_datas_s=[] #分けたデータの始めを入れる　スレッド用
        sep_datas_e=[] #分けたデータの最後を入れる　スレッド用
        for i in range(0,len(mids)):#データ分割
            #使える転送管理サーバの数に応じて同量でデータ分割
            #帯域幅とかでデータの量変えられると神
            if i == 0:#始め0からじゃないと全部DL出来ないのでif
                separate_data_s=0
            else :
                separate_data_s=separate_data_e+1
            separate_data_e=int((i+1)*(data_size/len(mids)))
            sep_datas_s.append(separate_data_s)
            sep_datas_e.append(separate_data_e)

        GET_set_s=[] #get sendをまとめて管理　スレッド用
        GET_set_r=[] #get recをまとめて管理　スレッド用
        for i in range(0,len(mids)):
            order=i+1 #書き込みの分別のため必要.get recで使う
            client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
            client_socket.connect((mids[i], mid_port))
            GETs=threading.Thread(target=GET_part_send, args=(client_socket, server_file_name, token_str,sep_datas_s[i], sep_datas_e[i],))
            GETr=threading.Thread(target=GET_part_rec, args=(client_socket,order,))
            GET_set_s.append(GETs)
            GET_set_r.append(GETr)

        for GETs in GET_set_s:#get sendを一斉に行う　
            GETs.start()
        Comp_start=time.time()
        print("Comp_start",Comp_start)
        for GETr in GET_set_r:#get recを一斉に行う
            GETr.start()
        for GETr in GET_set_r:#get recが全部終わるまで待つ
            GETr.join()
        end=time.time()
        print(end-start)

    # REP
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    if key == 0 :
        client_socket.connect((server_name, server_port)) # サーバのソケットに接続する
    elif key >= 1:
        client_socket.connect((mid_name, mid_port))  #中間サーバ―と通信する場合
    REP(client_socket, server_file_name, token_str) # REPコマンド
    Comp_end=time.time()
    print("Comp_end",Comp_end)

if __name__ == '__main__':
    if server_name == "localhost":#念のためサーバ名がpblXにしか対応してないから置換
        server_name = os.uname()[1]
    start=time.time()
    
    address=["pbl1a","pbl2a","pbl3a","pbl4a","pbl5a","pbl6a","pbl7a"]#AWS環境
    #address=["pbl1","pbl2","pbl3","pbl4"]#local環境

    BCmain(address)

    print('server_name:',server_name) # サーバ名
    print('server_port:',server_port) # サーバポート番号 
    print()
    print('mid_name:',mids) # 使用する中間サーバ名
    print('mid_port:',mid_port) # 中間サーバポート番号 
    print()
    end=time.time()
    rt_time=end-start
    print(mids,len(mids))
    commandMain()#SIZE,GET,REPを行なう関数
    print(mids,len(mids))
    end=time.time()

    print()
    print("転送管理サーバ",mids)
    print()
    print("取得するファイル:",server_file_name)
    print("経路作成にかかった時間:",rt_time)
    print("競技の時間:",Comp_end-Comp_start)