from museek import driver, messages
from mucipher import sha256Block

import tornado.ioloop
import tornado.web
import tornado.websocket
import json

MUSEEK_HOST = '192.168.1.104:2240'
MUSEEK_PASSWORD = 'slsk'


class MuseekWebSocket(tornado.websocket.WebSocketHandler):

    d = None
    connected = False
    repeat = False

    def prepare(self):
        # TODO: Check Status
        if self.d is None:
            self.d = driver.Driver()
            self.d.connect(MUSEEK_HOST, MUSEEK_PASSWORD)
            message = self.d.fetch()
            if message.__class__ is messages.Challenge:
                chresp = sha256Block(
                    message.challenge + MUSEEK_PASSWORD
                ).hexdigest()
                self.d.send(messages.Login("SHA256", chresp, 0))
                message = self.d.fetch()
                if message.__class__ is messages.Login:
                    print message.result
                    self.connected = message.result

    def open(self):
        print("WebSocket opened")
        if self.d is None and not self.connected:
            self.prepare()

    def on_message(self, message):
        source_message = json.loads(message)
        if source_message['action'] == 'search':
            self.d.send(messages.Search(0, source_message['query']))
            self.repeat = True
            while self.repeat:
                museek_message = self.d.fetch()
                if museek_message.__class__ is messages.SearchReply:
                    json_message = {'type': 'searchReply',
                                    'ticket': museek_message.ticket,
                                    'user': museek_message.user,
                                    'results': museek_message.results}
                    self.write_message(json_message)
                elif museek_message.__class__ is messages.Search:
                    # TODO: maybe it could be better if a search request was associated firstly to a unique token
                    json_message = {'type': 'search',
                                    'search_ticket': museek_message.ticket,
                                    'query': source_message['query']}
                    self.write_message(json_message)

    def on_close(self):
        print("WebSocket closed")


class SearchHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("search.html")

if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/search", SearchHandler),
        (r"/websocket", MuseekWebSocket),
    ], template_path="templates", debug=True)
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()
