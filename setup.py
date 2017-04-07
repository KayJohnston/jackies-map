import sys
from cx_Freeze import setup, Executable

setup(
    name = 'Jackie\'s Map',
    version = '3',
    description = 'Jackie\'s Map',
    executables = [Executable('jmap3q2.py', base = 'Win32GUI')])
