from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Watcher:
    def __init__(self, dir, app):
        self.dir = dir
        self.app = app

    def start(self):
        file_event_callback = self.send_reload_message

        class MyHandler(FileSystemEventHandler):
            def dispatch(self, evt):
                if not evt.is_directory:
                    # print('%s: %s' % (evt.event_type, evt.src_path))
                    file_event_callback()

        self.observer = Observer()
        self.observer.schedule(MyHandler(), str(self.dir), recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.join()

    def send_reload_message(self):
        self.app.loop.call_soon_threadsafe(self.app._write_debug_sockets, 'reload')
