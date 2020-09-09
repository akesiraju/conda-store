# jupyter-conda-store

This is the JupyterLab Extension for conda-store. The point of this extension is to provide users with the ability to create conda environments and jupyter kernels from within the JupyterLab context.

## Architecture

The current assumption made is that the extension is being installed on a JupyterLab instance being run on a JupyterHub server somewhere. This means that the `conda` binaries and such are exectuted on the server.

A local version will be installed soon where one can use this extension locally, but it will neccesitate a server-side extensions. In other words, this is in the works.


