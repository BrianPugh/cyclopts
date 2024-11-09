============
AutoRegistry
============

AutoRegistry_ is a python library that automatically creates string-to-functionality mappings, making it trivial to instantiate classes or invoke functions from CLI parameters.

Lets consider the following program that can download a file from either a GCP, AWS, or Azure bucket (without worrying about the implementation):

.. code-block:: python

   import cyclopts
   from pathlib import Path
   from typing import Literal

   def _download_gcp(bucket: str, key: str, dst: Path):
       print("Downloading data from Google.")

   def _download_s3(bucket: str, key: str, dst: Path):
       print("Downloading data from Amazon.")

   def _download_azure(bucket: str, key: str, dst: Path):
       print("Downloading data from Azure.")

   _downloaders = {
       "gcp": _download_gcp,
       "s3": _download_s3,
       "azure": _download_azure,
   }

   app = cyclopts.App()

   @app.command
   def download(bucket: str, key: str, dst: Path, provider: Literal[tuple(_downloaders)] = "gcp"):
       downloader = _downloaders[provider]
       downloader(bucket, key, dst)

   app()

.. code-block:: console

   $ my-script download --help
   ╭─ Parameters ────────────────────────────────────────────────────────────╮
   │ *  BUCKET,--bucket      [required]                                      │
   │ *  KEY,--key            [required]                                      │
   │ *  DST,--dst            [required]                                      │
   │    PROVIDER,--provider  [choices: gcp,s3,azure] [default: gcp]          │
   ╰─────────────────────────────────────────────────────────────────────────╯

   $ my-script my-bucket my-key local.bin --provider=s3
   Downloading data from Amazon.


Not bad, but let's see how this would look with AutoRegistry.

.. code-block:: python

   import cyclopts
   from autoregistry import Registry
   from pathlib import Path
   from typing import Literal

   _downloaders = Registry(prefix="_download_")

   @_downloaders
   def _download_gcp(bucket: str, key: str, dst: Path):
       print("Downloading data from Google.")

   @_downloaders
   def _download_s3(bucket: str, key: str, dst: Path):
       print("Downloading data from Amazon.")

   @_downloaders
   def _download_azure(bucket: str, key: str, dst: Path):
       print("Downloading data from Azure.")

   app = cyclopts.App()

   @app.command
   def download(bucket: str, key: str, dst: Path, provider: Literal[tuple(_downloaders)] = "gcp"):
       downloader = _downloaders[provider]
       downloader(bucket, key, dst)

   app()

.. code-block:: console

   $ my-script download --help
   ╭─ Parameters ────────────────────────────────────────────────────────────╮
   │ *  BUCKET,--bucket      [required]                                      │
   │ *  KEY,--key            [required]                                      │
   │ *  DST,--dst            [required]                                      │
   │    PROVIDER,--provider  [choices: gcp,s3,azure] [default: gcp]          │
   ╰─────────────────────────────────────────────────────────────────────────╯

   $ my-script my-bucket my-key local.bin --provider=s3
   Downloading data from Amazon.

Exactly the same functionality, but more terse and organized.
With Autoregistry, the download providers are much more self-contained, do not require changes in other code locations, and reduce duplication.

.. _AutoRegistry: https://github.com/BrianPugh/autoregistry
