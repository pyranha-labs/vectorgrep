#!/usr/bin/env bash

# Compile C code into shared libraries usable by Python.
# Recommended way to run is through docker on lowest supported Ubuntu version to maximize dependency compatibility.
# The compiled binaries should be forwards compatible, allowing them to be saved without need to compile per version.

# Set the versions to build so they are consistent throughout the script when updates are performed.
BOOST_BUILD_VERSION=1.75.0
HYPERSCAN_BUILD_VERSION=5.4.2
ZSTD_BUILD_VERSION=1.5.5

# Force execution in docker to ensure reproducibility.
if [ ! -f /.dockerenv ]; then
  echo "Please run inside docker to isolate dependencies, prevent modifications to system, and ensure reproducibility. Aborting."
  echo "Example: docker run --rm -it -v ~/Development/hypergrep:/mnt/hypergrep ubuntu:trusty bash -c '/mnt/hypergrep/utils/build_hyperscanner.sh'"
  exit 1
fi

# Ensure the whole script exits on failures.
set -e
# Turn on command echoing to show all commands as they run.
set -x

# Update the base dependencies.
apt-get update && apt-get install -y \
  build-essential \
  cmake \
  liblzma-dev \
  liblz4-dev \
  python \
  pkg-config \
  ragel \
  software-properties-common \
  wget \
  zlib1g-dev

# Install git from latest PPA, default on U14.04 (Trusty) is too old for multi-threaded submodule clones.
add-apt-repository -y ppa:git-core/ppa
apt-get update && apt-get install -y git

# Create a new temporary location to allow for isolated compiling.
build_dir=$(mktemp -d -t hsbuild-XXXXXXXX)

# Clone all required projects
cd "${build_dir}"
# Boost and Hyperscan must be pulled from source to support as low as U14.04 (Trusty). Do not use OS packages.
# Use 32 jobs to speed up Boost clone, it has 100+ submodules.
git clone --depth 1 --branch "boost-${BOOST_BUILD_VERSION}" https://github.com/boostorg/boost --recursive --jobs 32
git clone --depth 1 --branch "v${HYPERSCAN_BUILD_VERSION}" https://github.com/intel/hyperscan
git clone --depth 1 --branch "v${ZSTD_BUILD_VERSION}" https://github.com/facebook/zstd.git

# Set up only Boost headers for Hyperscan, full compilation is not required.
cd "${build_dir}"/boost
./bootstrap.sh
./b2 headers

# Compile Hyperscan shared library and objects, so that hyperscanner can reference in build.
cd "${build_dir}"/hyperscan
cmake -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=On \
  -DBOOST_ROOT="${build_dir}"/boost/
make -j $(nproc)

# Compile ZSTD shared library and objects, so that hyperscanner can reference in build.
cd "${build_dir}"/zstd
make -j $(nproc)

# Locate the project root and build from there to ensure the files are always stored in the same location.
project_dir="$(cd "$(dirname "$0")" && git rev-parse --show-toplevel)"

# Compile custom libhyperscanner and libzstd to position independent code, and then into a shared library.
cd "${project_dir}"/hypergrep/lib/c
# All warnings are failures to enforce clean code.
# Must use "-std=c99" to be compatible down to U14.04 (Trusty).
gcc -std=c99 -c -Wall -Werror -fpic hyperscanner.c \
  "${build_dir}"/zstd/zlibWrapper/gz*.c \
  "${build_dir}"/zstd/zlibWrapper/zstd_zlibwrapper.c \
  -I "${build_dir}"/zstd/lib \
  -I "${build_dir}"/zstd/zlibWrapper/ \
  -I "${build_dir}"/hyperscan/lib \
  -I "${build_dir}"/hyperscan/src \
  $(pkg-config --cflags --libs zlib)
gcc -shared -o "${project_dir}"/hypergrep/lib/libhyperscanner.so \
  hyperscanner.o \
  gz*.o \
  zstd*.o \
  -L"${build_dir}"/hyperscan/lib -lhs \
  -L"${build_dir}"/zstd/lib -lzstd \
  $(pkg-config --cflags --libs zlib)

# Copy the external shared libraries that were built back to the source for bundling with the hyperscanner as fallbacks.
cp -v "${build_dir}/hyperscan/lib/libhs.so.${HYPERSCAN_BUILD_VERSION}" "${project_dir}/hypergrep/lib/libhs.so.${HYPERSCAN_BUILD_VERSION}"
cp -v "${build_dir}/zstd/lib/libzstd.so.${ZSTD_BUILD_VERSION}" "${project_dir}/hypergrep/lib/libzstd.so.${ZSTD_BUILD_VERSION}"
