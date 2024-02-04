# How Tos

Advanced guides for working with VectorGrep. For basic guides, refer to the [README](../README.md).


## Table Of Contents

  * [Update/rebuild the libraries](#updaterebuild-the-libraries)
  * [Build the libraries for different architectures](#build-the-libraries-for-different-architectures)
  * [Check GLIBC supported versions](#check-glibc-supported-versions)
  * [Build Python 3.10+](#build-and-install-python310)


### Update/rebuild the libraries

1. If updating dependencies for production, increase the default version variables in `utils/build_vectorgrep.sh`.

1. Run `utils/build_vectorgrep.sh`, with or without arguments to control the versions and platform.
Guidance is automatically provided on running in an isolated environment via docker for best results.
   - Boost, CMake, Vectorscan, and ZStandard library versions can be controlled with arguments.
   - Platform, such as `linux-x86_64` vs `linux-aarch64`, can be controlled with arguments.
   - See [Build the libraries for different architectures](#build-the-libraries-for-different-architectures) for more
     complex builds, such as cross-compiling

1. When the build completes, it will save the final libraries in place under `vectorgrep/lib`. Either check in the
files if releasing, or save for distribution and use in custom environments.


### Build the libraries for different architectures

The current production build supports native x86_64 CPUs, as well as virtualized (in most scenarios). If running
one of the natively supported environments, a custom build is not needed. If you wish to build for other
architectures, the simplest way is to follow [Update/Rebuild the libraries](#updaterebuild-the-libraries)
on a system matching the desired hardware configuration. If hardware for the desired configuration is not available
at build time, then the docker `--platform` option may be able to fill in the gap (support varies based on environment).

For example, if you are on a Mac M1/M2/etc., you can use Docker and a supported image in x64 mode with
`--platform linux/amd64`, and then run the build for x86_64 devices from ARM devices. Support for other ARM
devices should be similar, assuming they support virtualized backends, such as `qemu`.

When the libraries have been built, they can then be stored anywhere, and the configuration updated to point to
the custom build with the following before running any VectorGrep operations:
 ```python
 import vectorgrep

 vectorgrep.configure_libraries(
     libhs='/home/myuser/libhs.so.mybuild',
     libvectorgrep='/home/myuser/libvectorgrep.so.mybuild',
     libzstd='/home/myuser/libzstd.so.mybuild',
 )
 ```


### Check GLIBC supported versions

If you are seeing messages similar to `version 'GLIBCXX_3.4.26' not found` when attempting to import VectorGrep,
your system may not have high enough support for GLIBC. You may be able to install a newer version depending on
the operating system, but the first steps is to check support. On x86_64 systems, the following (or similar variations)
can be used to dump the supported list:

```bash
strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBC
```

The output will look similar to:
```
GLIBCXX_3.4
...
GLIBCXX_3.4.25
```

If the version mentioned in the error is not found in the list, then the system does not currently support VectorGrep.
Look into updating the version of GLIBC on the system, such as installing a newer gcc/g++, etc. Example of how to do
this on Ubuntu (down to Trusty):
```bash
add-apt-repository -y ppa:ubuntu-toolchain-r/test
apt-get update
apt-get install -y gcc-9 g++-9
```


### Build and install python3.10+

If running Ubuntu Focal (20.04+), or Debian Bookworm (12+), they include python3.10+ as the default python3.
If looking to build a newer python version than available by default, or for systems where 3.10+ is not available,
the following steps can be used. This is not an in depth guide for building python, there are plenty of great guides
online for more complex setups, however this should work for the most common installations. These steps are also
used to test VectorGrep on various distros.

1. Install dependencies to build python from source. This builds a fairly minimal python. If you wish to expand
python support for additional libraries, install them after these base packages, but before configuring in step 3:  
    ```bash
    sudo apt install -y \
        build-essential \
        libncurses5-dev \
        libgdbm-dev \
        libssl-dev \
        libreadline-dev \
        libffi-dev \
        libsqlite3-dev \
        libbz2-dev \
        zlib1g-dev \
        wget
    sudo ldconfig
    ```

1. Pull down the tarball and extract the source:
    ```bash
    wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz
    tar -xf Python-3.10.13.tgz
    ```

1. Configure the source and build:
    ```bash
    cd Python-3.10.13/
    ./configure
    make -j $(nproc)
    ```

1. Install:
    ```bash
    sudo make altinstall
    ```

1. Cleanup source:
    ```bash
    cd ..
    rm -r Python-3.10.13/
    rm Python-Python-3.10.13.tgz
    ```
