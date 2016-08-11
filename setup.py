import sys
from pathlib import Path
from setuptools import setup, find_packages


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()


setup(
    name='muffin-playground',
    version='0.0.1',
    license='Apache 2.0',
    description=Path('README.rst').read_text(),
    platforms=('Any',),
    keywords='asyncio aiohttp muffin'.split(),
    author='Feihong Hsu',
    email='feihong.hsu@gmail.com',
    url='https://github.com/feihong/muffin-playground',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['muffin', 'plim'],
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
