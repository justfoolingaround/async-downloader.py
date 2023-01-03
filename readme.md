# `async_downloader.py`

Finally, a reliable multi-connection downloader.

> **Note**: This project is written for [justfoolingaround](https://www.github.com/justfoolingaround)'s project.

## Features

> **Warning**: This project **only** supports `httpx.AsyncClient` as its session class. However, migrating into `aiohttp` is not that difficult. You may just inherit two coroutine methods of the class (`is_resumable` and `download_part`).


- Can be used as a single connection downloader for *those* cases.
- Implements a highly reliable `is_resumable` method for validating resumable content.<a href="#when-resumable"><sup>When to use this?</sup></a>
- Supports pause event that immediately stops the download progress.
- Supports `tqdm.tqdm` to be used as its progress bar.
- Supports progress bar for **individual connections**.
- Supports `asyncio.Future` usage in the `download_part` function.<a href="#when-future"><sup>When to use this?</sup></a>
- Supports immediately allocating the file to the disk.

<h2 id="when-future">When to use <code>asyncio.Future</code> in the <code>download_part</code> function?</h2>

TL;DR: For pausing / resuming effectively.

This tool is a bare-bone downloader. The downloader cannot *just* guess when the previous download completed. This is majorly because it uses a single file during its IO operations. It opens a file, downloads content and puts those content in the expected positions **while** downloading.

So, when a pause occurs, this future is expected to get the completed position of the download progress so that the developer make implementations for resuming content that did not make it.

<h2 id="when-resumable">When to use the <code>is_resumable</code> method?</h2>

TL;DR: Recommended to use **every time**.

There are servers in the wild that are notorious for breaking standards.

The standard method is to use a `HEAD` request, see if `Accept-Ranges` and/or `Content-Length` are present and operate accordingly. However sometimes,
- The server may block the `HEAD` requests.
- The server may not oblige by the `Accept-Ranges` and/or `Content-Length` headers.

The method within the project simply sends a `GET` request with `range: 0-0` and checks if the server sends in a standard `206 Partial Content` response.