"""
To run:

    muffin app run

"""
import json
import asyncio
import threading
import muffin
from muffin_playground import Application, WebSocketWriter


app = Application()
PAGE_SIZE = 6

@app.register('/')
async def index(request):
    results = await fetch(1)
    return app.render('index.plim', results=results)


@app.register('/websocket/')
async def websocket(request):
    ws = muffin.WebSocketResponse()
    await ws.prepare(request)
    print('Websocket opened')

    writer = WebSocketWriter(ws)

    page = 2
    while not ws.closed:
        results = await fetch(page)
        if results is None:
            break
        writer.write(type='results', value=results)
        page += 1

    await ws.close()
    print('Websocket closed')

    return ws


app.register_static_resource()


async def fetch(page):
    if page >= 11:
        return None
    start = (page - 1) * PAGE_SIZE + 1
    end = start + PAGE_SIZE
    await asyncio.sleep(1)
    return [i for i in range(start, end)]
