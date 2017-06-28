import sys
from cx_Freeze import setup, Executable

setup(
    name = 'Jackie\'s Map',
    version = '3s',
    description = 'Jackie\'s Map',
    executables = [Executable('jmap3s.py', base = 'Win32GUI')])
