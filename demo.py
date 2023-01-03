import asyncio

import httpx
from tqdm import tqdm

from async_downloader import MultiConnectionDownloader

URL = "https://releases.ubuntu.com/22.04.1/ubuntu-22.04.1-desktop-amd64.iso"

"""
Connection rating
>1 - Normal download
>4 - Quite good
>8 - Good
>16 - Good but probably will be throttled
>32 - Will be throttled
"""


CONNECTIONS = 32


async def __main__():

    session = httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
    )

    progress_bar = tqdm(
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    )

    head_response = await session.head(URL)

    qualified_filename = head_response.url.path.split("/")[-1]
    content_length = int(head_response.headers.get("Content-Length", 0))

    progress_bar.total = content_length
    progress_bar.set_description(f"<= {qualified_filename!r}")

    with open(qualified_filename, "wb") as io:
        downloader = MultiConnectionDownloader(
            session,
            "GET",
            URL,
            progress_bar=progress_bar,
        )

        downloaded_positions = await downloader.allocate_downloads(
            io, content_length, connections=CONNECTIONS
        )

    await session.aclose()


loop = asyncio.new_event_loop()
loop.run_until_complete(__main__())
