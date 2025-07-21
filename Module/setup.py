from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("quote_split_chunked.pyx", language_level=3)
)
