# How Tos

Advanced guides for working with HyperGrep. For basic guides, refer to the [README](../README.md).


## Table Of Contents

  * [Rebuild the libraries](#updaterebuild-the-libraries)


### Update/rebuild the libraries

1. If updating any dependencies, increase the version variables in `utils/build_hyperscanner.sh`.

1. Run the `utils/build_hyperscanner.sh`. Additional guidance is provided on running in an isolated environment.

1. When the build completes, it will save the final libraries in place. Either check in the files if releasing,
or move externally if using in other environments.
