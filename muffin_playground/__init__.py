import sys
import json
import subprocess
import mimetypes
from pathlib import Path

import asyncio
from aiohttp import hdrs
from aiohttp.web_exceptions import HTTPNotFound, HTTPNotModified
import muffin
from muffin.urls import StaticRoute, StaticResource
from mako.template import Template
from mako.lookup import TemplateLookup
from plim import preprocessor


here = Path(__file__).parent
lookup = TemplateLookup(
    directories=['.', str(here)],
    preprocessor=preprocessor)


class Application(muffin.Application):
    def __init__(self, *args, **kwargs):
        if 'DEBUG' not in kwargs:
            kwargs['DEBUG'] = True
        if 'name' not in kwargs:
            kwargs['name'] = 'playground'
        super().__init__(*args, **kwargs)

    def register_static_resource(self):
        route = CustomStaticRoute(None, '/', '.')
        resource = StaticResource(route)
        self.router._reg_resource(resource)

    def render(self, tmpl_file, **kwargs):
        if not isinstance(tmpl_file, Path):
            tmpl_file = Path(tmpl_file)
        return render(tmpl_file, **kwargs)


class CustomStaticRoute(StaticRoute):
    @asyncio.coroutine
    def handle(self, request):
        filename = request.match_info['filename']
        try:
            filepath = self._directory.joinpath(filename).resolve()
            filepath.relative_to(self._directory)
        except (ValueError, FileNotFoundError) as error:
            # relatively safe
            raise HTTPNotFound() from error
        except Exception as error:
            # perm error or other kind!
            request.logger.exception(error)
            raise HTTPNotFound() from error

        # Handle .plim files.
        if filepath.is_dir():
            filepath = filepath / 'index.plim'
            if not filepath.exists():
                raise HTTPNotFound()
            else:
                return (yield from self.render_plim(request, filepath))
        if filepath.suffix == '.plim':
            return (yield from self.render_plim(request, filepath))

        # Handle RapydScript files.
        if filepath.suffix == '.pyj':
            return (yield from self.compile_rapydscript(request, filepath))

        # Handle RapydScript files.
        if filepath.suffix == '.styl':
            return (yield from self.compile_stylus(request, filepath))

        st = filepath.stat()

        modsince = request.if_modified_since
        if modsince is not None and st.st_mtime <= modsince.timestamp():
            raise HTTPNotModified()

        ct, encoding = mimetypes.guess_type(str(filepath))
        if not ct:
            ct = 'application/octet-stream'

        resp = self._response_factory()
        resp.content_type = ct
        if encoding:
            resp.headers[hdrs.CONTENT_ENCODING] = encoding
        resp.last_modified = st.st_mtime

        file_size = st.st_size

        resp.content_length = file_size
        resp.set_tcp_cork(True)
        try:
            yield from resp.prepare(request)

            with filepath.open('rb') as f:
                yield from self._sendfile(request, resp, f, file_size)

        finally:
            resp.set_tcp_nodelay(True)

        return resp

    async def render_plim(self, request, tmpl_file):
        resp = self._response_factory()
        resp.content_type = 'text/html'
        await resp.prepare(request)
        output = render(tmpl_file).encode('utf-8')
        resp.content_length = len(output)
        resp.write(output)
        return resp

    async def compile_rapydscript(self, request, pyj_file):
        resp = self._response_factory()
        resp.content_type = 'text/javascript'
        await resp.prepare(request)

        cmd =  [
            'rapydscript', str(pyj_file),
            '-j', '6',
            '-p', str(here),
        ]
        output = subprocess.check_output(cmd)
        resp.content_length = len(output)
        resp.write(output)
        return resp

    async def compile_stylus(self, request, stylus_file):
        resp = self._response_factory()
        resp.content_type = 'text/css'
        await resp.prepare(request)

        cmd =  ['stylus', '-p', str(stylus_file)]
        output = subprocess.check_output(cmd)
        resp.content_length = len(output)
        resp.write(output)
        return resp


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
