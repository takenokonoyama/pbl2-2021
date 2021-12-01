# -*- coding: utf-8 -*-

from socket import *  
import sys
import random
import time

client_name = sys.argv[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
server_name = sys.argv[2] # サーバのホスト名
server_port =  int(sys.argv[3]) # サーバのポート
dataSize = 10000

def dataCreate(data_size):
    for i in range(data_size):
                if i == 0:
                    sentence=str(random.randrange(256))
                else:
                    sentence+=str(random.randrange(256))
    return sentence

def main_TCP():
    print("Useing TCP ")
    client_socket = socket(AF_INET, SOCK_STREAM)  # ソケットを作る
    client_socket.connect((server_name, server_port))  # サーバのソケットに接続する
    sentence=dataCreate(dataSize)
    client_socket.send(sentence.encode())  # 文字列をバイト配列に変換後、送信する。
    start_time = time.time()
    modified_sentence = client_socket.recv(1024)  # 最大1024バイトを受け取る。受け取った内容はバイト配列として格納される。
    end_time = time.time()
    print('From Server: {0}'.format(modified_sentence))  # バイト配列を文字列に変換して表示する
    elapsed_time = end_time - start_time
    print('Start: {0}, End: {1}, Elapsed: {2} seconds'.
        format(start_time, end_time, elapsed_time))
    client_socket.close()  # ソケットを閉じる

def main_UDP():
    print("Useing UDP ")
    client_socket = socket(AF_INET, SOCK_DGRAM) #UDP
    sentence=dataCreate(dataSize)
    client_socket.sendto(sentence.encode(), (server_name, server_port)) #UDP
    start_time = time.time()
    modified_sentence = client_socket.recvfrom(1024) #UDP
    end_time = time.time()
    print('From Server: {0}'.format(modified_sentence))  # バイト配列を文字列に変換して表示する
    elapsed_time = end_time - start_time
    print('Start: {0}, End: {1}, Elapsed: {2} seconds'.
        format(start_time, end_time, elapsed_time))
    client_socket.close()  # ソケットを閉じる

if __name__ == '__main__':
    main_TCP()
    #main_UDP()
    #time.sleep(0.0001)  # wait for 0.0001 seconds