import paho.mqtt.client as mqtt
import time
import random
import string
import tkinter
import math
import json

HOST = 'broker.hivemq.com'
PORT = 1883
GENERAL_TOPIC = 'uoplnwcxejughlufizpedofrzbnvkzwnsntdpuad'


class Client:
    def __init__(self, name):
        self.status = 'searching'
        self.game_topic = None
        self.enemy_name = None
        self.message_stack = []
        self.name = name

        self.client = mqtt.Client()
        self.client.username_pw_set(self.name)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.connect(HOST, PORT, 60)
        self.client.loop_start()

        self.subscribe(GENERAL_TOPIC)

        self.root = tkinter.Tk()
        tkinter.Button(self.root, text="Quit", command=self.root.destroy).pack(side=tkinter.BOTTOM)
        self.buttons = []
        self.mainloop_searching()

        self.root.mainloop()

    def mainloop_searching(self):
        if self.status != 'searching':
            return

        self.post(GENERAL_TOPIC)
        for but in self.buttons:
            but.destroy()
        self.buttons = []

        cur_time = time.time()
        client_list = []
        for msg in self.message_stack:
            if msg['topic'] == GENERAL_TOPIC and cur_time - msg['ts'] < 2:
                client = msg['msg']
                if client not in client_list and self.name != client:
                    client_list.append(client)

        for client in client_list:
            self.buttons.append(tkinter.Button(self.root, text=client, command=lambda: self.connect(client)))
            self.buttons[-1].pack(side=tkinter.TOP)

        self.root.after(1000, self.mainloop_searching)

    def mainloop_waiting(self):
        if self.status != 'starting game':
            return

        self.post(self.game_topic)
        for msg in self.message_stack:
            if msg['topic'] == self.game_topic and msg['msg'] == self.enemy_name:
                self.status = 'in game'
                self.destroy()

        self.root.after(1000, self.mainloop_waiting)

    def connect(self, enemy_name):
        self.status = 'starting game'
        for but in self.buttons:
            but.destroy()
        self.buttons = []
        tkinter.Label(self.root, text='Starting game with ' + enemy_name).pack(side=tkinter.TOP)

        random_string = ''.join(random.choices(string.ascii_lowercase, k=20))
        self.game_topic = GENERAL_TOPIC + '/' + random_string
        self.enemy_name = enemy_name

        start_string = 'start ' + self.name + ' ' + self.enemy_name + ' ' + self.game_topic
        self.post(GENERAL_TOPIC, start_string)
        self.client.unsubscribe(GENERAL_TOPIC)
        self.subscribe(self.game_topic)

        self.mainloop_waiting()

    def post(self, topic, data=None):
        if not data:
            data = self.name

        self.client.publish(topic, data)
        return data

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def destroy(self):
        self.client.loop_stop()
        self.client.disconnect()
        try:
            self.root.destroy()
        except:
            pass

    def on_connect(self, client, userdata, flags, rc):
        print(self.name, "connected with code " + str(rc))

    def on_message(self, client, userdata, message):
        msg = str(message.payload.decode("utf-8"))
        topic = message.topic
        cur_time = time.time()
        element = {'msg': msg, 'topic': topic, 'ts': cur_time}
        self.message_stack.append(element)
        print(element)

        if len(msg.split()) == 4 and msg.split()[0] == 'start' and msg.split()[2] == self.name:
            self.enemy_name = msg.split()[1]
            self.game_topic = msg.split()[3]
            self.status = 'starting game'

            for but in self.buttons:
                but.destroy()
            self.buttons = []
            tkinter.Label(self.root, text='Starting game with ' + self.enemy_name).pack(side=tkinter.TOP)

            self.client.unsubscribe(GENERAL_TOPIC)
            self.subscribe(self.game_topic)

            self.mainloop_waiting()


def main():
    Client('Client_1')


main()
