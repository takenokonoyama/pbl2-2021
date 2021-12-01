#!/usr/bin/env python

from socket import *
import time   # for time.sleep()
import threading  # for Thread()
import sys

client_name = sys.argv[1]  # クライアントのホスト名あるいはIPアドレスを表す文字列
server_name = sys.argv[2] # サーバのホスト名
server_port =  int(sys.argv[3]) # サーバのポート

def interact_with_client_TCP(soc):
    sentence = soc.recv(1024).decode()
    print('Received: {0}'.format(sentence)) 
    capitalized_sentence = sentence
    print('Sending: {0}'.format(capitalized_sentence))

    soc.send(capitalized_sentence.encode())
    soc.close()

def interact_with_client_UDP(soc):
    sentence, client_address = soc.recvfrom(2048)
    print('Received: {0}'.format(sentence)) 
    capitalized_sentence = sentence
    print('Sending: {0}'.format(capitalized_sentence))

    soc.sendto(capitalized_sentence, client_address)
    soc.close()

def main_TCP():
    server_socket = socket(AF_INET, SOCK_STREAM) #TCP
    server_socket.bind(('', server_port))
    server_socket.listen(5) #TCP
    print('The server is ready to receive by TCP')
    connection_socket, addr = server_socket.accept() #TCP    
    client_handler = threading.Thread(target=interact_with_client_TCP, args=(connection_socket,)) #TCP
    client_handler.start()  # スレッドを開始

def main_UDP():
    server_socket = socket(AF_INET, SOCK_DGRAM) #UDP
    server_socket.bind(('', server_port))
    print('The server is ready to receive by UDP')
    interact_with_client_UDP(server_socket)

if __name__ == '__main__':
    main_TCP()
    #main_UDP()

    