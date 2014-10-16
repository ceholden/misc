Miscellaneous
=============

## Documentation

Most scripts or programs in this repository are not mature enough or are not used by others to warrant extensive documentation, but the ones that are are listed below organized according to the file location within the repository:

+ landsat
    * [landsat_stack.py](docs/landsat_stack.md)

## Requirements

### Python

Many of the Python programs in this repository use the common suite of scientific Python modules which may already be installed on your machine, including [`numpy`](http://www.numpy.org/), [`scipy`](http://www.scipy.org/), and [`scikit-learn`](http://scikit-learn.org/stable/). Likewise, you probably also already have the Python bindings to [`gdal`](http://www.gdal.org/) installed. 

One very useful module you might not already have installed is [`docopt`](http://docopt.org/) which I use to generate clean [Command Line Interfaces](http://en.wikipedia.org/wiki/Command-line_interface) from the [docstring](http://en.wikipedia.org/wiki/Docstring) of each program. `docopt` is just one Python file and is easily available from [PyPi](https://pypi.python.org/pypi/docopt) through `pip install docopt`. If you do not have write access over the Python library directory, you may simply place a copy of `docopt.py` next to each command line script.

A full listing of requirements includes:

    numpy >= 1.8.1
    scipy >= 0.14.0
    scikit-learn >= 0.15.1
    docopt >= 0.6.1
