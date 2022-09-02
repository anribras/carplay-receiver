import tornado.web, tornado.ioloop, tornado.websocket
# from pisource import Pisource, PiVideoFrameType
from string import Template
import io, os, socket

# start configuration
serverPort = 8000

# source = Pisource(sensor_mode=2, resolution='1920x1080', framerate=30)
# source.video_denoise = False

recordingOptions = {
    'format': 'h264',
    'quality': 20,
    'profile': 'high',
    'level': '4.2',
    'intra_period': 15,
    'intra_refresh': 'both',
    'inline_headers': True,
    'sps_timing': True
}

focusPeakingColor = '1.0, 0.0, 0.0, 1.0'
focusPeakingthreshold = 0.055

centerColor = '255, 0, 0, 1.0'
centerThickness = 2

gridColor = '255, 0, 0, 1.0'
gridThickness = 2
# end configuration

# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# s.connect(('8.8.8.8', 0))
# serverIp = s.getsockname()[0]

serverIp = '127.0.0.1'

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


def getFile(filePath):
    file = open(filePath, 'r')
    content = file.read()
    file.close()
    return content


def templatize(content, replacements):
    tmpl = Template(content)
    return tmpl.substitute(replacements)


indexHtml = templatize(getFile('index.html'), {'ip': serverIp, 'port': serverPort, 'fps': 30})
centerHtml = templatize(getFile('center.html'),
                        {'ip': serverIp, 'port': serverPort, 'fps': 30, 'color': centerColor,
                         'thickness': centerThickness})
gridHtml = templatize(getFile('grid.html'),
                      {'ip': serverIp, 'port': serverPort, 'fps': 30, 'color': gridColor,
                       'thickness': gridThickness})
focusHtml = templatize(getFile('focus.html'),
                       {'ip': serverIp, 'port': serverPort, 'fps': 30, 'color': focusPeakingColor,
                        'threshold': focusPeakingthreshold})
jmuxerJs = getFile('jmuxer.min.js')


class StreamBuffer(object):
    def __init__(self, source):
        # self.frameTypes = PiVideoFrameType()
        self.loop = None
        self.buffer = io.BytesIO()
        self.source = source

    def setLoop(self, loop):
        self.loop = loop

    def write(self, buf):
        # if self.source.frame.complete and self.source.frame.frame_type != self.frameTypes.sps_header:
        if 1:
            self.buffer.write(buf)
            if self.loop is not None and wsHandler.hasConnections():
                self.loop.add_callback(callback=wsHandler.broadcast, message=self.buffer.getvalue())
            self.buffer.seek(0)
            self.buffer.truncate()
        else:
            self.buffer.write(buf)


class wsHandler(tornado.websocket.WebSocketHandler):
    connections = []

    def open(self):
        self.connections.append(self)

    def on_close(self):
        self.connections.remove(self)

    def on_message(self, message):
        pass

    @classmethod
    def hasConnections(cl):
        if len(cl.connections) == 0:
            return False
        return True

    @classmethod
    async def broadcast(cl, message):
        for connection in cl.connections:
            try:
                await connection.write_message(message, True)
            except tornado.websocket.WebSocketClosedError:
                pass
            except tornado.iostream.StreamClosedError:
                pass

    def check_origin(self, origin):
        return True


class indexHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(indexHtml)


class centerHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(centerHtml)


class gridHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(gridHtml)


class focusHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(focusHtml)


class jmuxerHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'text/javascript')
        self.write(jmuxerJs)


requestHandlers = [
    (r"/ws/", wsHandler),
    (r"/", indexHandler),
    (r"/center/", centerHandler),
    (r"/grid/", gridHandler),
    (r"/focus/", focusHandler),
    (r"/jmuxer.min.js", jmuxerHandler)
]


def server_loop(source):
    try:
        # streamBuffer = StreamBuffer(source)
        # source.start_recording(streamBuffer, **recordingOptions)
        application = tornado.web.Application(requestHandlers,debug=True)
        application.listen(serverPort)
        loop = tornado.ioloop.IOLoop.current()
        # streamBuffer.setLoop(loop)
        loop.add_callback(callback=wsHandler.broadcast, message=source.data_from_dongle())
        loop.start()
    except KeyboardInterrupt:
        source.stop_recording()
        source.close()
        loop.stop()
