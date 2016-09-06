"""
To run:

    muffin app run

"""
import json
import asyncio
import muffin
from muffin_playground import Application, WebSocketHandler, WebSocketWriter


app = Application()
app.register_special_static_route()


@app.register('/websocket/')
class WSHandler(WebSocketHandler):
    async def on_open(self):
        print('Web socket opened')
        self.task = None

    async def on_close(self):
        print('Web socket closed')

    async def on_message(self, msg):
        print(msg)
        if msg.data == 'start' and not self.task:
            coroutine = long_task(WebSocketWriter(self.websocket))
            self.task = asyncio.ensure_future(coroutine)
            self.task.add_done_callback(self.done_callback)
        elif msg.data == 'stop' and self.task:
            self.task.cancel()
            self.task = None

    def done_callback(self, future):
        self.task = None


async def long_task(writer):
    total = 150
    for i in range(1, total+1):
        writer.write(type='progress', value=i, total=total)
        print(i)
        await asyncio.sleep(0.05)
