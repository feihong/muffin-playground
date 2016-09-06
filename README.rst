Muffin-Playground
#################

A small module containing convenience classes to make it easier to create simple muffin applications.

What it offers:

- An easy-to-use static file handler that automatically compiles certain types of source files (.plim, .styl, .pyj)
- Client autoreload
- Support for plim templating language (.plim)
- Support for Stylus CSS preprocessor (.styl)
- Support for RapydScript Python-to-JS compiler (.pyj)
- Custom muffin.Application subclass with a render() method for plim templates
- WebSocketHandler class with on_open(), on_close(), and on_message() methods

Installation
============

  pip install muffin-playground

If you want RapydScript and Stylus support, you must install their packages via npm:

  npm install -g stylus rapydscript-ng
