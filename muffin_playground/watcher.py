from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Watcher:
    def __init__(self, dir, loop, sockets):
        self.dir = dir
        self.loop = loop
        self.sockets = sockets

    def start(self):
        callback = self.send_reload_message

        class MyHandler(FileSystemEventHandler):
            def dispatch(self, evt):
                if not evt.is_directory:
                    # print('%s: %s' % (evt.event_type, evt.src_path))
                    callback()

        self.observer = Observer()
        self.observer.schedule(MyHandler(), str(self.dir), recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.join()

    def send_reload_message(self):
        self.loop.call_soon_threadsafe(self._send)

    def _send(self):
        for ws in self.sockets:
            ws.send_str('reload')
