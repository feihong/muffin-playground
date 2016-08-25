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


__version__ = '0.0.6'


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

    def register_static_route(self, prefix='/', directory='.'):
        route = CustomStaticRoute(name=None, prefix=prefix, directory=directory)
        self.router.register_route(route)

    def render(self, tmpl_file, **kwargs):
        if not isinstance(tmpl_file, Path):
            tmpl_file = Path(tmpl_file)
        return render(tmpl_file, **kwargs)

    def start_task_in_executor(self, fn, *args):
        return start_task_in_executor(fn, *args)


class CustomStaticRoute(StaticRoute):
    async def handle(self, request):
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
                return await self.render_plim(request, filepath2)
        if filepath.suffix == '.plim':
            return await self.render_plim(request, filepath)

        # Handle RapydScript files.
        if filepath.suffix == '.pyj':
            return await self.render_rapydscript(request, filepath)

        # Handle Stylus files.
        if filepath.suffix == '.styl':
            return await self.render_stylus(request, filepath)

        # # Handle Transcrypt files.
        # if filepath.suffix == '.py':
        #     return await self.compile_transcrypt(request, filepath, filename)

        return None

    async def create_response(self, request, content_type, output):
        resp = muffin.StreamResponse()
        resp.content_type = content_type
        await resp.prepare(request)
        resp.content_length = len(output)
        resp.write(output)
        return resp

    async def render_plim(self, request, tmpl_file):
        return await self.create_response(
            request,
            content_type='text/html',
            output=render(tmpl_file).encode('utf-8'))

    async def render_rapydscript(self, request, pyj_file):
        cmd =  [
            'rapydscript', str(pyj_file),
            '--js-version', '6',
            '--import-path', str(here),
        ]
        return await self.create_response(
            request,
            content_type='text/javascript',
            output=await check_output(cmd))

    async def render_stylus(self, request, stylus_file):
        cmd = ['stylus', '-p', str(stylus_file)]
        return await self.create_response(
            request,
            content_type='text/css',
            output=await check_output(cmd))

    # async def compile_transcrypt(self, request, py_file, filename):
    #     import transcrypt.__main__ as ts
    #
    #     redirect_url = filename.parent / '__javascript__' / (filename.stem + '.js')
    #     output_file = py_file.parent / '__javascript__' / (py_file.stem + '.js')
    #     if output_file.exists() and output_file.stat().st_mtime > py_file.stat().st_mtime:
    #         return HTTPFound(str(redirect_url))
    #
    #     filename = Path(filename)
    #
    #     def compile():
    #         sys.argv = [
    #             'transcrypt',
    #             '-b',           # build
    #             '-m',           # generate source map
    #             '-e', '6',      # generate ES 6 code
    #             str(py_file)]
    #         print(sys.argv)
    #         ts.main()
    #
    #     await start_task_in_executor(compile)
    #     return HTTPFound(str(redirect_url))
    #
    # async def get_response_for_file(self, request, filepath, content_type):
    #     resp = await self.get_response(request, content_type)
    #     output = filepath.read_bytes()
    #     resp.content_length = len(output)
    #     resp.write(output)
    #     return resp


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
    loop = asyncio.get_event_loop()
    coroutine = loop.run_in_executor(None, fn, *args)
    return asyncio.ensure_future(coroutine)


async def check_output(cmd):
    "Like the asynchronous version of subprocess.check_output()."
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return stdout
