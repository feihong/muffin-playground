"""
To run:

    muffin app run

"""
import json
import asyncio
import threading
import time
import muffin
from muffin_playground import Application, WebSocketHandler, ThreadSafeWebSocketWriter


app = Application()
app.register_special_static_route()


@app.register('/websocket/')
class WSHandler(WebSocketHandler):
    async def on_open(self):
        self.task = None
        self.stop_event = threading.Event()

    async def on_message(self, msg):
        print(msg)
        if msg.data == 'start' and not self.task:
            self.task = app.start_task_in_executor(
                long_task,
                ThreadSafeWebSocketWriter(self.websocket),
                self.stop_event)
            self.task.add_done_callback(self.done_callback)
        elif msg.data == 'stop' and self.task:
            self.stop_event.set()

    def done_callback(self, future):
        print('done!')
        self.task = None
        self.stop_event.clear()


def long_task(writer, stop_event):
    total = 150
    for i in range(1, total+1):
        if stop_event.is_set():
            return
        writer.write(type='progress', value=i, total=total)
        print(i)
        time.sleep(0.05)
