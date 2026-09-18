import unittest
import asyncio

from kaggle_gateway import batched_stream


class StreamBatchingTests(unittest.IsolatedAsyncioTestCase):
    async def test_groups_chunks_and_flushes_at_end(self):
        async def source():
            yield b"data: one\n\n"
            yield b"data: two\n\n"

        batches = [item async for item in batched_stream(source(), interval=4, max_bytes=1024)]
        self.assertEqual(batches, [b"data: one\n\ndata: two\n\n"])

    async def test_flushes_on_byte_bound_without_losing_framing(self):
        async def source():
            yield b"data: one\n\n"
            yield b"data: two\n\n"

        batches = [item async for item in batched_stream(source(), interval=4, max_bytes=11)]
        self.assertEqual(b"".join(batches), b"data: one\n\ndata: two\n\n")
        self.assertEqual(batches[0], b"data: one\n\n")

    async def test_cancellation_does_not_emit_partial_fake_frame(self):
        async def source():
            yield b"data: partial"
            await __import__("asyncio").sleep(10)

        iterator = batched_stream(source(), interval=0.01)
        await iterator.__anext__()
        await iterator.aclose()

    async def test_token_after_window_is_kept_for_next_batch(self):
        async def source():
            yield b"data: one\n\n"
            await asyncio.sleep(0.03)
            yield b"data: two\n\n"

        batches = [item async for item in batched_stream(source(), interval=0.01)]
        self.assertEqual(b"".join(batches), b"data: one\n\ndata: two\n\n")
        self.assertEqual(len(batches), 2)

    async def test_continuous_tokens_flush_before_generation_finishes(self):
        finished = False
        async def source():
            nonlocal finished
            for _ in range(15):
                yield b"token"
                await asyncio.sleep(0.01)
            finished = True
        stream = batched_stream(source(), interval=0.035)
        first = await anext(stream)
        self.assertFalse(finished)
        rest = [item async for item in stream]
        self.assertEqual(b"".join([first, *rest]), b"token" * 15)
        self.assertGreater(len(rest), 1)

    async def test_large_chunk_is_split_at_memory_bound(self):
        async def source():
            yield b"x" * 103
        batches = [item async for item in batched_stream(source(), max_bytes=10)]
        self.assertTrue(all(len(item) <= 10 for item in batches))
        self.assertEqual(b"".join(batches), b"x" * 103)

    async def test_flushes_pending_output_before_propagating_upstream_failure(self):
        async def source():
            yield b"data: content\n\n"
            raise RuntimeError("upstream failed")
        stream = batched_stream(source())
        self.assertEqual(await anext(stream), b"data: content\n\n")
        with self.assertRaisesRegex(RuntimeError, "upstream failed"):
            await anext(stream)


if __name__ == "__main__":
    unittest.main()
