# VectorGrep

[![os: linux](https://img.shields.io/badge/os-linux-blue)](https://docs.python.org/3.10/)
[![python: 3.10+](https://img.shields.io/badge/python-3.10_|_3.11-blue)](https://devguide.python.org/versions)
[![python style: google](https://img.shields.io/badge/python%20style-google-blue)](https://google.github.io/styleguide/pyguide.html)
[![imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://github.com/PyCQA/isort)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![code style: pycodestyle](https://img.shields.io/badge/code%20style-pycodestyle-green)](https://github.com/PyCQA/pycodestyle)
[![doc style: pydocstyle](https://img.shields.io/badge/doc%20style-pydocstyle-green)](https://github.com/PyCQA/pydocstyle)
[![static typing: mypy](https://img.shields.io/badge/static_typing-mypy-green)](https://github.com/python/mypy)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
[![testing: pytest](https://img.shields.io/badge/testing-pytest-yellowgreen)](https://github.com/pytest-dev/pytest)
[![security: bandit](https://img.shields.io/badge/security-bandit-black)](https://github.com/PyCQA/bandit)
[![license: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

VectorGrep is a high-performance (Vectorized) Global Regular Expression "Processing" library for Python. It uses
Vectorscan (a portable fork of Intel Hyperscan) to maximize performance, and can be used with multithreaded
or multiprocessed applications. VectorGrep is also home to `vectorgrep` (Vectorized Global Regular Expression Printer),
a multithreaded/multi-file "grep" command to search many files in parallel. It can often be used as a drop in
replacement for `grep/egrep/zgrep` etc.

While a standard "grep" is designed to "print", VectorGrep is designed to allow full control over "processing".
It supports scanning compressed, or uncompressed, text files for regular expressions, and customizing the action
to take when a match is found. For full information about the performance of Vectorscan (and Hyperscan), refer to:  
[VectorCamp: Vectorscan](https://github.com/VectorCamp/vectorscan)  
[Intel: Hyperscan](https://github.com/intel/hyperscan)

VectorGrep also is the successor to [HyperGrep](https://github.com/pyranha-labs/hypergrep). It is designed to be
a drop in replacement for the original during initial releases. Refer to the [FAQ](#faq) for more information
about this change.


## Table Of Contents

  * [Key Features](#key-features)
  * [Compatibility](#compatibility)
  * [Getting Started](#getting-started)
    * [Installation](#installation)
    * [Examples](#examples)
    * [Contribute](#contribute)
    * [Advanced Guides](#advanced-guides)
  * [FAQ](#faq)


## Key Features

- **Simplicity**
  - No experience with Vectorscan/Hyperscan required. Provides "grep" styled interfaces.
  - No external dependencies, and no building required (on natively supported platforms).
  - Built in support for compressed and uncompressed files.
- **Speed**
  - Uses Vectorscan/Hyperscan, a high-performance multiple regex matching library.
  - Performs read and regex operations outside Python.
  - Batches results for Python, reducing overhead (customizable).
- **Parallelism**
  - Bypasses GIL (Global Interpreter Lock) during read and regex operations to allow proper multithreading.
  - Python consumer threads (callbacks) are able to handle many producer threads (readers).


## Compatibility

- Supports Python 3.10+
- Supports Linux systems with x86_64 architecture
  - Ubuntu Focal (20.04), Debian Bullseye (11), and above out of the box
  - Ubuntu Trusty (14.04) and above with gcc-9/g++-9 installed
  - Other Operating System configurations may work, but are not tested/guaranteed
    - Linux distros other than Debian/Ubuntu should work, assuming GLIBC is high enough
    - May be able to be built on Windows/OSX manually
    - More platforms are planned to be supported (natively) in the future
- Some regex constructs are not supported by Vectorscan/Hyperscan in order to guarantee stable performance
  - For more information refer to: [Unsupported Constructs](https://intel.github.io/hyperscan/dev-reference/compilation.html#unsupported-constructs)


## Getting Started

### Installation

- Install VectorGrep via pip:
    ```shell
    pip install vectorgrep
    ```

- Or via git clone:
    ```shell
    git clone <path to fork>
    cd vectorgrep
    pip install .
    ```

- Or build and install from wheel:
    ```shell
    # Build locally.
    git clone <path to fork>
    cd vectorgrep
    make wheel
    
    # Push dist/vectorgrep*.tar.gz to environment where it will be installed.
    pip install dist/vectorgrep*.tar.gz
    ```

### Examples

- Read one file with the example single threaded command:
    ```shell
    # vectorgrep/scanner.py <regex> <file>
    vectorgrep/scanner.py pattern ./vectorgrep/scanner.py
    ```

- Read multiple files with the multithreaded command (drop in replacement for `grep` where patterns are compatible):
    ```shell
    # From install:
    # vectorgrep <regex> <file(s)>
    vectorgrep pattern ./vectorgrep/scanner.py

    # From package:
    # vectorgrep/multiscanner.py <regex> <file>
    vectorgrep/multiscanner.py pattern ./vectorgrep/scanner.py
    ```

- Collect all matches from a file, similar to grep, and perform a custom operation on results:
    ```python
    import vectorgrep
    
    file = "./vectorgrep/scanner.py"
    pattern = 'pattern'
    
    results, return_code = vectorgrep.grep(file, [pattern])
    for index, line in results:
        print(f'{index}: {line}')
    ```

- Manually scan a file and perform a custom operation on match:
    ```python
    import vectorgrep
    
    file = "./vectorgrep/scanner.py"
    pattern = 'pattern'

    def on_match(matches: list, count: int) -> None:
        for index in range(count):
            match = matches[index]
            line = match.line.decode(errors='ignore')
            print(f'Custom print: {line.rstrip()}')
    
    vectorgrep.scan(file, [pattern], on_match)
    ```

- Override the `libhs` and/or `libzstd` libraries to use files outside the package.
Must be called before any other usage of `vectorgrep`:
    ```python
    import vectorgrep

    vectorgrep.configure_libraries(
        libhs='/home/myuser/libhs.so.mybuild',
        libzstd='/home/myuser/libzstd.so.mybuild',
    )
    ```

### Contributing

Refer to the [Contributing Guide](CONTRIBUTING.md) for information on how to contribute to this project.

### Advanced Guides

Refer to [How Tos](docs/HOW_TO.md) for more advanced topics, such as building the shared library objects.


## FAQ

#### Q: How does VectorGrep compare to other Vectorscan/Hyperscan python libraries?

**A:** VectorGrep has a specific goal: provide a high performance "grep" like interface in python,
but with more control. It is not intended to be a full set of bindings to Vectorscan/Hyperscan. If you need
full control over the low level backend, there are other python libraries intended for that use case. Here are
a few of the reasons for the focused goal of this library:

- Simplify developer integration.
  - No experience with Vectorscan/Hyperscan required.
  - Familiarity with `grep` variants beneficial, but not required.
- Avoid messy subprocess chains common in "parallel grep" implementations.
  - Commands like `zgrep` are actually a `zcat` + `grep`. This can lead to 3+ processes per file read.
  - Subprocessing is messy in general, best to minimize its use as much as possible.
- Optimize performance.
  - Reduce callbacks to/from python to reduce overhead.
  - Allow true multithreading during read and regex matching.
  - Provide the pattern matched in multi-regex searches, without having to repeat the search in Python.

When it comes to performance, here is an example of the benefit of this design. Due to the performance of
Vectorscan/Hyperscan, it is also often faster than native `grep` variants, even while using python. Scenario setup:
- 2.10GHz Intel x86_64 Processor
- ~17M line file (~300M gzip compressed, ~3G uncompressed).
- ~800 PCRE patterns.
- Counting only, no extra processing of lines.
- Each job run 5 times and averaged (lower is better).

|   | Scenario (Uncompressed timings in parenthesis) | VectorGrep    | Full bindings     | zgrep (grep)  |
|---|------------------------------------------------|---------------|-------------------|---------------|
| 1 | ~90K matches, 1 pattern                        | 8.2s (2.5s)   | 22.8s (15.5s)     | 12.5s (5.2s)  |
| 2 | ~900K matches, 10 patterns                     | 9.7s (3.8s)   | 25.7s (16.8s)     | 19.8s (17.3s) |
| 3 | ~15M matches, ~800 patterns                    | 44.2s (38.1s) | 73.5s (57.7s)     | *             |
| 4 | Scenario #3 (x4 files), 1 process (4 threads)  | 49.6s (46.8s) | 1432.6s (1302.2s) | *             |

* GNU grep does not allow multiple PCRE patterns natively, and concatenation via "or" failed.

#### Q: How do I make a custom build for a system other than Linux x86_64?

**A**: Refer to [How To: Build the libraries for different architectures](docs/HOW_TO.md#build-the-libraries-for-different-architectures)

#### Q: I only have an ARM CPU, can I build/run the x86_64 libraries?

**A**: Depends. The current production build supports native x86_64 CPUs, as well as virtualized (in most scenarios).
For example, if you are on a Mac M1/M2/etc., you can use Docker and a supported image in x64 mode with
`--platform linux/amd64`. Performance may vary however, as the code is running through virtual machine emulation.
This process can also be used to build new libraries if your system is set up properly for emulation.
Refer to [How To: Build the libraries for different architectures](docs/HOW_TO.md#build-the-libraries-for-different-architectures)
for more information about supporting additional environments (natively or through emulation) besides Linux x86_64.

#### Q: Why was Vectorscan forked from Hyperscan?

**A:** Vectorscan was originally created to provide a portable fork of Hyperscan, and allow running on other
architectures such as ARM. Intel changed the license of Hyperscan from BSD to IPL (Intel Proprietary License)
starting in 5.5, while Vectorscan continues to provide updates and remain fully open source. For more information:  
[Vectorscan: Why was there a need for a fork?](https://github.com/VectorCamp/vectorscan#why-was-there-a-need-for-a-fork)  
[Vectorscan: Hyperscan license change](https://github.com/VectorCamp/vectorscan#hyperscan-license-change-after-54)

#### Q: Why is VectorGrep not a fork of HyperGrep?

**A:** HyperGrep receives maintenance updates, but over time it will become a different solution from
VectorGrep, and eventually become no longer updated, due to the licensing changes made by Intel to Hyperscan. In order
to keep the responsibilities of each clearly separated, and avoid any confusion about backports or feature requests,
it was decided to make a "clean cut" of HyperGrep, instead of using a "fork". There are no plans to backport any
features from VectorGrep to HyperGrep. VectorGrep starts from HyperGrep commit 9c6f2b2. The original commit
history can be found in [HyperGrep History](docs/HYPERGREP_HISTORY)
