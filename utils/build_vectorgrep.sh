#!/usr/bin/env bash

# Compile C code into shared libraries usable by Python.
# Recommended way to run is through docker on lowest supported Ubuntu version to maximize dependency compatibility.
# The compiled binaries should be forwards compatible, allowing them to be saved without need to compile per version.

# Set the versions to build so they are consistent throughout the script when updates are performed.
BOOST_BUILD_VERSION=1.75.0
VECTORSCAN_BUILD_VERSION=5.4.11
ZSTD_BUILD_VERSION=1.5.5

# Force execution in docker to ensure reproducibility.
if [ ! -f /.dockerenv ]; then
  echo "Please run inside docker to isolate dependencies, prevent modifications to system, and ensure reproducibility. Aborting."
  echo "Example: docker run --rm -it -v ~/Development/vectorgrep:/mnt/vectorgrep ubuntu:bionic bash -c '/mnt/vectorgrep/utils/build_vectorgrep.sh'"
  exit 1
fi

# Ensure the whole script exits on failures.
set -e
# Turn on command echoing to show all commands as they run.
set -x

# Update the base dependencies.
apt-get update && apt-get install -y \
  build-essential \
  liblzma-dev \
  liblz4-dev \
  libsqlite3-dev \
  pkg-config \
  ragel \
  software-properties-common \
  wget \
  zlib1g-dev

# Install git and gcc/g++ from latest repositories, defaults on U14.04 (Trusty) are too old.
# Newer git is required for multi-threaded submodule clones.
# Newer gcc/g++ required for python detection and SSE4 support.
add-apt-repository -y ppa:git-core/ppa
add-apt-repository -y ppa:ubuntu-toolchain-r/test
apt-get update && apt-get install -y \
  gcc-9 \
  g++-9 \
  git

# Update installs to ensure they are used over defaults from build-essential.
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 50 --slave /usr/bin/g++ g++ /usr/bin/g++-9
update-alternatives --install /usr/bin/c++ c++ /usr/bin/g++-9 50

# Bionic contains cmake that is too old for Vectorscan 5.4.11+ (3.20+ required).
wget https://github.com/Kitware/CMake/releases/download/v3.28.1/cmake-3.28.1-linux-x86_64.tar.gz
tar -xf cmake-3.28.1-linux-x86_64.tar.gz
mv cmake-3.28.1-linux-x86_64/bin/* /usr/bin/
mv cmake-3.28.1-linux-x86_64/share/cmake-3.28 /usr/share/

# Create a new temporary location to allow for isolated compiling.
build_dir=$(mktemp -d -t hsbuild-XXXXXXXX)

# Clone all required projects
cd "${build_dir}"
# Boost and Vectorscan must be pulled from source to support as low as U14.04 (Trusty). Do not use OS packages.
# Use 32 jobs to speed up Boost clone, it has 100+ submodules.
git clone --depth 1 --branch "boost-${BOOST_BUILD_VERSION}" https://github.com/boostorg/boost --recursive --jobs 32
git clone --depth 1 --branch "vectorscan/${VECTORSCAN_BUILD_VERSION}" https://github.com/VectorCamp/vectorscan
git clone --depth 1 --branch "v${ZSTD_BUILD_VERSION}" https://github.com/facebook/zstd.git

# Set up only Boost headers for Vectorscan, full compilation is not required.
cd "${build_dir}"/boost
./bootstrap.sh
./b2 headers

# Compile Vectorscan shared library and objects, so that libvectorgrep can reference in build.
cd "${build_dir}"/vectorscan
mkdir build
cd build
cmake ../ -DCMAKE_BUILD_TYPE=Release \
  -DBOOST_ROOT="${build_dir}"/boost/ \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DBUILD_SHARED_LIBS=On
make -j $(nproc)

# Compile ZSTD shared library and objects, so that libvectorgrep can reference in build.
cd "${build_dir}"/zstd
make -j $(nproc)

# Locate the project root and build from there to ensure the files are always stored in the same location.
project_dir="$(dirname $(dirname "$0"))"

# Compile custom libvectorgrep and libzstd to position independent code, and then into a shared library.
cd "${project_dir}"/vectorgrep/lib/c
# All warnings are failures to enforce clean code.
# Must use "-std=c99" to be compatible down to U14.04 (Trusty).
gcc -std=c99 -c -Wall -Werror -fpic vectorgrep.c \
  "${build_dir}"/zstd/zlibWrapper/gz*.c \
  "${build_dir}"/zstd/zlibWrapper/zstd_zlibwrapper.c \
  -I "${build_dir}"/zstd/lib \
  -I "${build_dir}"/zstd/zlibWrapper/ \
  -I "${build_dir}"/vectorscan/build \
  -I "${build_dir}"/vectorscan/src \
  $(pkg-config --cflags --libs zlib)
gcc -shared -o "${project_dir}"/vectorgrep/lib/libvectorgrep.so \
  vectorgrep.o \
  gz*.o \
  zstd*.o \
  -L"${build_dir}"/vectorscan/build/lib -lhs \
  -L"${build_dir}"/zstd/lib -lzstd \
  $(pkg-config --cflags --libs zlib)

# Copy the external shared libraries that were built back to the source for bundling with libvectorgrep as fallbacks.
cp -v "${build_dir}/vectorscan/build/lib/libhs.so.${VECTORSCAN_BUILD_VERSION}" "${project_dir}/vectorgrep/lib/libhs.so.${VECTORSCAN_BUILD_VERSION}"
cp -v "${build_dir}/zstd/lib/libzstd.so.${ZSTD_BUILD_VERSION}" "${project_dir}/vectorgrep/lib/libzstd.so.${ZSTD_BUILD_VERSION}"
