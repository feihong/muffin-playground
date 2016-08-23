import os
import sys
import re
from pathlib import Path
from setuptools import setup, find_packages


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()


code = Path('muffin_playground/__init__.py').read_text()
version = re.search(r"^__version__\s*=\s*'(.*)'", code, re.M).group(1)


setup(
    name='muffin-playground',
    version=version,
    license='Apache 2.0',
    description='Convenience classes for simple muffin apps',
    long_description=Path('README.rst').read_text(),
    platforms='Any',
    keywords='asyncio aiohttp muffin'.split(),
    author='Feihong Hsu',
    author_email='feihong.hsu@gmail.com',
    url='https://github.com/feihong/muffin-playground',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['muffin>=0.9.0', 'plim'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
