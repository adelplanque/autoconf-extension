# Autotools-Extension

`autotools-extension` allows you to add a configuration step before building a python extension with distutil or setuptools. It is done with the well-known `autoconf`.
According to the autotools philosophy, only the developer uses `autoconf`. The `configure` script is then embedded in the source distribution.

## Getting Started

### Prerequisites

`autotools-extension` work with python2 (tested with python2.6) or python3.

It requires `setuptools`.

### Installing

* From sources:

  ~~~bash
  python setup.py install
  ~~~

  Please refer to (Alternate Installation)[https://docs.python.org/3/install/index.html#inst-alt-install] for alternative installation schemas.

## Example

Suppose we want to package an extension `my_ext.cpp` using (boost-python)[https://www.boost.org/doc/libs/1_69_0/libs/python/doc/html/index.html].
The name of the library required for link editing depends on the system on which the installation is performed.
boost_python, boost_python37, boost_python36-py36, ... are possible names, depending on the OS, the python version, ...
By adding an autoconf script, the name of the library will be determined at the time of installation.

~~~python
from setuptools import setup, Extension

from autotools_extension.autoconf import Distribution

setup(
    distclass=Distribution,
    name='my_package,
    packages=['my_extension],
    ext_modules=[Extension(
        'my_extension,
        sources=['my_ext.cpp],
        libraries=['@BOOST_PYTHON_LIB@']
    )],
    configure_ac="""
        AC_PREREQ([2.63])
        AC_INIT([waouh], [1.0.0])
        AM_INIT_AUTOMAKE([foreign -Wall -Werror])

        dnl Boost
        AX_BOOST_BASE([1.41], [],
            AC_MSG_ERROR([Needs Boost but it was not found in your system])
        )

        dnl Boost Python
        AX_BOOST_PYTHON
        if test "$ac_cv_boost_python" != "yes"; then
            AC_MSG_ERROR([Boost Python needed])
        fi

        AC_CONFIG_FILES([Makefile])
        AC_OUTPUT
    """,
    configure_options = [
        ('with-boost=', None, "Boost install prefix"),
    ],
)
~~~

A full example is provided at https://github.com/adelplanque/autotools-extension-example

## License

(MIT License)[https://github.com/adelplanque/autotools-extension-example/blob/master/LICENSE]
