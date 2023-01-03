import asyncio


async def maybe_coro(coro, *args, **kwargs):
    loop = asyncio.get_running_loop()

    if asyncio.iscoroutinefunction(coro):
        return await coro(*args, **kwargs)
    else:
        return await loop.run_in_executor(None, coro, *args, **kwargs)


class MultiConnectionDownloader:

    MINIMUM_PART_SIZE = 1024**2

    def __init__(
        self,
        session,
        *args,
        loop=None,
        progress_bar=None,
        **kwargs,
    ):
        self.session = session

        self.args = args
        self.kwargs = kwargs

        self.loop = loop or asyncio.new_event_loop()
        self.io_lock = asyncio.Lock()

        self.progress_bar = progress_bar

    async def download_part(
        self,
        io,
        start: int,
        end: int,
        progress_bar=None,
        future=None,
        pause_event=None,
    ):

        headers = self.kwargs.pop("headers", {})

        if end is None:
            if start is not None:
                headers["Range"] = f"bytes={start}-"
        else:
            headers["Range"] = f"bytes={start}-{end}"

        position = start or 0

        async with self.session.stream(
            *self.args, **self.kwargs, headers=headers
        ) as response:
            if progress_bar is not None:

                content_length = int(response.headers.get("Content-Length", 0))

                if content_length > 0:
                    progress_bar.total = content_length

            async for chunk in response.aiter_bytes(8192):

                chunk_size = len(chunk)

                if self.progress_bar is not None:
                    self.progress_bar.update(chunk_size)

                if progress_bar is not None:
                    progress_bar.update(chunk_size)

                await self.write_to_file(
                    self.io_lock,
                    io,
                    position,
                    chunk,
                )
                position += chunk_size

                if pause_event is not None and pause_event.is_set():
                    break

        if future is not None:
            future.set_result((start, position))

        return (start, position)

    @staticmethod
    async def write_to_file(
        lock: asyncio.Lock,
        io,
        position: int,
        data: bytes,
    ):

        async with lock:
            await maybe_coro(io.seek, position)
            await maybe_coro(io.write, data)
            await maybe_coro(io.flush)

    async def allocate_downloads(
        self,
        io,
        content_length: int = None,
        connections: int = 8,
        allocate_content_on_disk=False,
        pause_event=None,
    ):
        def iter_allocations():
            if content_length is None or content_length < self.MINIMUM_PART_SIZE:
                yield None, None
            else:
                chunk_size = content_length // connections
                for i in range(connections - 1):
                    yield i * chunk_size, (i + 1) * chunk_size - 1

                yield (connections - 1) * chunk_size, None

        if allocate_content_on_disk:
            async with self.io_lock:
                await maybe_coro(io.truncate, content_length)

        return await asyncio.gather(
            *(
                self.download_part(io, start, end, pause_event=pause_event)
                for start, end in iter_allocations()
            )
        )

    @staticmethod
    async def is_resumable(
        session,
        method,
        *args,
        **kwargs,
    ):
        headers = kwargs.pop("headers", {})

        headers["Range"] = "bytes=0-0"

        async with session.stream(method, *args, **kwargs) as response:
            return response.status_code == 206
