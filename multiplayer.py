import paho.mqtt.client as mqtt
import time
import random
import string
import tkinter
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
        self.client.connect(HOST, PORT, 60)
        self.client.loop_start()

    def post(self, topic, msg_type=None, data=None):
        if not data:
            data = self.name
            msg_type = 'ping'
        msg = json.dumps({'client': self.name, 'topic': topic, 'ts': time.time(), 'type': msg_type, 'data': data})
        self.client.publish(topic, msg)

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def disconnect(self):
        self.client.disconnect()

    def set_on_connect(self, func):
        self.client.on_connect = func

    def set_on_message(self, func):
        self.client.on_message = func

    def create_connection(self, enemy_name):
        self.message_stack = []

        random_string = ''.join(random.choices(string.ascii_lowercase, k=20))
        self.game_topic = GENERAL_TOPIC + '/' + random_string
        self.enemy_name = enemy_name

        data = {'name': self.name, 'enemy_name': self.enemy_name, 'game_topic': self.game_topic}
        self.post(GENERAL_TOPIC, 'start', data)
        self.client.unsubscribe(GENERAL_TOPIC)
        self.subscribe(self.game_topic)

    def receive_connection(self, enemy_name, game_topic):
        self.message_stack = []

        self.enemy_name = enemy_name
        self.game_topic = game_topic

        self.client.unsubscribe(GENERAL_TOPIC)
        self.subscribe(self.game_topic)


class Master:
    def __init__(self):
        self.status = 'started'
        self.last_ping_time = None
        self.buttons = []
        self.hide_button = None
        self.searching_client = None
        self.top_label = None

        self.root = tkinter.Tk()
        self.root.geometry('400x400')
        self.root.resizable(tkinter.FALSE, tkinter.FALSE)
        self.root.title('some title')

        self.left_half = tkinter.Frame(self.root, bg='black')
        self.left_half.place(x=0, y=0, width=200, height=400)
        self.right_half = tkinter.Frame(self.root, bg='black')
        self.right_half.place(x=200, y=0, width=200, height=400)

        self.name_field = tkinter.Entry(self.left_half, justify=tkinter.CENTER)
        self.name_field.place(x=10, y=10, width=180)
        self.name_button = tkinter.Button(self.left_half, text='REVEAL MYSELF\nUSING THIS NAME', command=self.reveal)
        self.name_button.place(x=50, y=40, width=100, height=30)
        self.root.bind('<Return>', lambda event: self.reveal())

        self.output_text = tkinter.Text(self.right_half, bg='black', fg='red')
        self.output_text.insert(tkinter.END, '---START LINE---')
        self.output_text.config(state=tkinter.DISABLED)
        self.output_text.place(x=0, y=0, width=200, height=360)
        self.clear_button = tkinter.Button(self.right_half, text='CLEAR', command=self._clear)
        self.clear_button.place(x=50, y=360, width=100, height=30)

        self.silent_client = Client('')
        self.silent_client.set_on_message(lambda client, data, msg: self._print(
            json.loads(str(msg.payload.decode("utf-8")))['data']))
        self.silent_client.set_on_connect(lambda client, data, flags, rc: self._print(
            "Connected with code " + str(rc)))
        self.silent_client.subscribe(GENERAL_TOPIC)

        self.root.mainloop()

    def reveal(self):
        name = self.name_field.get()
        if len(name) and len(name.split()) == 1:
            self.status = 'searching'
            self.name_field.destroy()
            self.name_button.destroy()
            self.root.unbind('<Return>')
            self.silent_client.disconnect()
            self._clear()

            self.top_label = tkinter.Label(self.left_half, text='AVAILABLE CONNECTIONS :', bg='black', fg='red')
            self.top_label.place(x=0, y=10, width=200, height=30)
            self.hide_button = tkinter.Button(self.left_half, text='HIDE MYSELF', command=self.root.destroy)  # TODO
            self.hide_button.place(x=50, y=360, width=100, height=30)

            self.searching_client = Client(name)
            self.searching_client.subscribe(GENERAL_TOPIC)
            self.searching_client.set_on_message(self.on_searching_message)
            self.searching_client.set_on_connect(lambda client, data, flags, rc: self._print(
                name + " connected with code " + str(rc)))

            self.searching_loop()

    def searching_loop(self):
        if self.status != 'searching':
            return

        self.searching_client.post(GENERAL_TOPIC)
        for but in self.buttons:
            but.destroy()
        self.buttons = []

        cur_time = time.time()
        client_list = []
        for msg in self.searching_client.message_stack:
            if msg['topic'] == GENERAL_TOPIC and cur_time - msg['ts'] < 2:
                client_name = msg['data']
                if client_name not in client_list and self.searching_client.name != client_name:
                    client_list.append(client_name)

        for client_name in client_list:
            self.buttons.append(tkinter.Button(self.left_half, text=client_name, command=lambda: self.connect(client_name)))
            self.buttons[-1].place(x=50, y=50+client_list.index(client_name), width=100, height=30)

        self.root.after(1000, self.searching_loop)

    def waiting_loop(self):
        if self.status != 'waiting':
            return

        self.searching_client.post(self.searching_client.game_topic)
        if time.time() - self.last_ping_time > 10:
            print('lost connection')
            self.root.destroy()

        self.root.after(1000, self.waiting_loop)

    def connect(self, enemy_name, game_topic=None):
        if game_topic:
            self.searching_client.receive_connection(enemy_name, game_topic)
        else:
            self.searching_client.create_connection(enemy_name)

        self.status = 'waiting'
        for but in self.buttons:
            but.destroy()
        self.buttons = []
        self._print('\nStarting game with ' + enemy_name + '\n')
        self.last_ping_time = time.time()

        self.waiting_loop()

    def on_searching_message(self, client, data, message):
        msg = json.loads(str(message.payload.decode("utf-8")))

        if msg['type'] == 'ping' and self.status == 'waiting':
            if msg['client'] == self.searching_client.enemy_name:
                self.last_ping_time = msg['ts']
            return

        self._print(msg['data'])
        self.searching_client.message_stack.append(msg)

        if msg['type'] == 'start' and msg['data']['enemy_name'] == self.searching_client.name:
            self.connect(msg['data']['name'], msg['data']['game_topic'])

    def _print(self, text, sep='\n'):
        if type(text) != str:
            text = json.dumps(text)
        self.output_text.config(state=tkinter.NORMAL)
        self.output_text.insert(tkinter.END, sep + text)
        self.output_text.config(state=tkinter.DISABLED)

    def _clear(self):
        self.output_text.config(state=tkinter.NORMAL)
        self.output_text.delete(1.0, tkinter.END)
        self.output_text.insert(tkinter.END, '---START LINE---')
        self.output_text.config(state=tkinter.DISABLED)


Master()
