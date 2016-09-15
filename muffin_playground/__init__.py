import sys
import json
import subprocess
import mimetypes
from pathlib import Path

import asyncio
from aiohttp import hdrs
from aiohttp.web import HTTPFound
from aiohttp.web_exceptions import HTTPNotFound, HTTPNotModified
import muffin
from muffin.urls import StaticRoute, StaticResource
from mako.template import Template
from mako.lookup import TemplateLookup
from plim import preprocessor

from . import watcher


__version__ = '0.0.10'


ERROR_JAVASCRIPT = """
document.body.onload = function() {
    document.body.innerHTML = '';
    var pre = document.createElement('pre');
    pre.innerText = %s;
    document.body.appendChild(pre);
}
"""


resources = Path(__file__).parent / 'resources'
lookup = TemplateLookup(
    directories=['.', str(resources)],
    preprocessor=preprocessor)


class Application(muffin.Application):
    def __init__(self, *args, **kwargs):
        if 'DEBUG' not in kwargs:
            kwargs['DEBUG'] = True
        if 'name' not in kwargs:
            kwargs['name'] = 'playground'

        self.client_autoreload = kwargs.pop('client_autoreload', True)
        super().__init__(*args, **kwargs)

        if self.client_autoreload:
            self.reload_sockets = set()
            self.router.add_route('GET', '/__reload.js', reload_js)
            self.router.add_route('GET', '/__reload__/', self._reload_websocket)

            # You must use a start callback, because at this point self.loop
            # does not yet have a valid value.
            # In latest version of aiohttp, you can use on_startup signal instead.
            def start_callback(app):
                self.watcher = watcher.Watcher(
                    dir='.',
                    loop=self.loop,
                    sockets=self.reload_sockets)
                self.watcher.start()
                # Don't use .register_on_finish(), which is deprecated.
                self.on_shutdown.append(lambda app: self.watcher.stop())

            self.register_on_start(start_callback)

    def register_special_static_route(self, prefix='/', directory='.'):
        # Use a start callback because a static route usually needs to be
        # towards the end of the list of routes.
        def start_callback(app):
            route = SpecialFileStaticRoute(
                name=None, prefix=prefix, directory=directory, client_autoreload=True)
            self.router.register_route(route)
            self.router.add_static('/boilerplate/', str(resources))

        self.register_on_start(start_callback)

    def render(self, tmpl_file, **kwargs):
        if not isinstance(tmpl_file, Path):
            tmpl_file = Path(tmpl_file)
        return render(tmpl_file, **kwargs)

    def start_task_in_executor(self, fn, *args):
        return start_task_in_executor(fn, *args)

    async def _reload_websocket(self, request):
        ws = muffin.WebSocketResponse()
        await ws.prepare(request)
        self.reload_sockets.add(ws)
        async for msg in ws:
            pass
        self.reload_sockets.remove(ws)
        return ws


class SpecialFileStaticRoute(StaticRoute):
    def __init__(self, *args, **kwargs):
        self.client_autoreload = kwargs.pop('client_autoreload', True)
        super().__init__(*args, **kwargs)

    async def handle(self, request):
        """
        Based on the code in:

        https://github.com/KeepSafe/aiohttp/blob/v0.22.5/aiohttp/web_urldispatcher.py

        """
        filename = request.match_info['filename']
        try:
            filepath = self._directory.joinpath(filename).resolve()
            filepath.relative_to(self._directory)
        except (ValueError, FileNotFoundError) as error:
            # relatively safe
            raise HTTPNotFound() from error
        except Exception as error:
            # perm error or other kind!
            request.app.logger.exception(error)
            raise HTTPNotFound() from error

        # Try to handle as a special file.
        resp = await self.handle_special_file(request, filepath)
        if resp is not None:
            return resp

        # Make sure that filepath is a file
        if not filepath.is_file():
            raise HTTPNotFound()

        ret = await self._file_sender.send(request, filepath)
        return ret

    async def handle_special_file(self, request, filepath):
        # Handle .plim files.
        if filepath.is_dir():
            filepath2 = filepath / 'index.plim'
            if not filepath2.exists():
                raise HTTPNotFound()
            else:
                return await self.render_plim(filepath2)
        if filepath.suffix == '.plim':
            return await self.render_plim(filepath)

        # Handle RapydScript files.
        if filepath.suffix == '.pyj':
            return await self.render_rapydscript(filepath)

        # Handle Stylus files.
        if filepath.suffix == '.styl':
            return await self.render_stylus(filepath)

        return None

    async def render_plim(self, tmpl_file):
        html = render(tmpl_file)
        if self.client_autoreload:
            html = html.replace('</body>', '<script src="/__reload.js"></script></body>')
        return muffin.Response(content_type='text/html', text=html)

    async def render_rapydscript(self, pyj_file):
        cmd =  [
            'rapydscript', str(pyj_file),
            '--js-version', '6',
            '--import-path', str(resources),
        ]
        success, output = await check_output(cmd)
        if not success:
            output = ERROR_JAVASCRIPT % json.dumps(output)
        return muffin.Response(
            content_type='text/javascript',
            body=output)

    async def render_stylus(self, stylus_file):
        cmd = ['stylus', '-p', str(stylus_file)]
        success, output = await check_output(cmd)
        if not success:
            output = ERROR_JAVASCRIPT % json.dumps(output)
        return muffin.Response(
            content_type='text/javascript',
            body=output)


class WebSocketWriter:
    def __init__(self, wsresponse):
        self.resp = wsresponse

    def write(self, **kwargs):
        # print(kwargs)
        if not self.resp.closed:
            self.resp.send_str(json.dumps(kwargs))


class ThreadSafeWebSocketWriter:
    def __init__(self, wsresponse):
        self.resp = wsresponse
        self.loop = asyncio.get_event_loop()

    def write(self, **kwargs):
        if not self.resp.closed:
            data = json.dumps(kwargs)
            self.loop.call_soon_threadsafe(self.resp.send_str, data)


class WebSocketHandler(muffin.Handler):
    async def get(self, request):
        self.request = request
        ws = muffin.WebSocketResponse()
        self.websocket = ws
        await ws.prepare(request)
        await self.on_open()

        async for msg in ws:
            await self.on_message(msg)

        await self.on_close()
        await ws.close()
        return ws

    async def on_message(self, msg):
        pass

    async def on_open(self):
        pass

    async def on_close(self):
        pass


def render(tmpl_file, **kwargs):
    tmpl = Template(
        text=tmpl_file.read_text(),
        lookup=lookup,
        preprocessor=preprocessor)
    return tmpl.render(**kwargs)


def start_task_in_executor(fn, *args):
    "Execute the given function using the default ThreadPoolExecutor."
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, fn, *args)


async def check_output(cmd):
    "Basically the asynchronous version of subprocess.check_output()."
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.code == 0:
        return False, stderr
    else:
        return True, stdout


async def reload_js(request):
    return muffin.Response(
        content_type='text/javascript',
        body=(resources / 'reload.js').read_bytes())
