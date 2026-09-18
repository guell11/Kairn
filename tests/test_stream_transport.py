"""Validate incremental delivery over real local HTTP, not buffered ASGI transport."""
import asyncio
import contextlib
import socket
import threading
import time
import unittest
from unittest.mock import patch

import httpx
import uvicorn
import kaggle_gateway as gateway
from connection import _stream_works


class StreamTransportTests(unittest.TestCase):
    def test_buffered_sse_does_not_pass_cadence_check(self):
        body = b'data: {"seq":1}\n\ndata: {"seq":2,"done":true}\n\n'
        with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(
                200, content=body, headers={"content-type": "text/event-stream"}))) as client:
            self.assertFalse(_stream_works(client, "http://test/v1"))

    def test_gateway_keeps_one_upstream_request_and_sends_timed_batches(self):
        requests = []
        class Tokens(httpx.AsyncByteStream):
            async def __aiter__(self):
                for i in range(20):
                    yield f'data: {{"token":{i}}}\n\n'.encode()
                    await asyncio.sleep(.3)
                yield b'data: [DONE]\n\n'
        async def upstream(request):
            requests.append(request)
            return httpx.Response(200, stream=Tokens(), headers={"content-type": "text/event-stream"})

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(gateway.app, log_level="critical", lifespan="off"))
        client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        with patch.object(gateway, "client", client), patch.object(gateway, "API_KEY", "local-test"):
            thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not server.started and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(server.started)
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"Authorization": "Bearer local-test"}, timeout=15) as http:
                    self.assertTrue(_stream_works(http, f"http://127.0.0.1:{port}/v1"))
                    start = time.monotonic()
                    with http.stream("POST", "/v1/chat/completions", json={"stream": True, "messages": []}) as response:
                        packets = [(time.monotonic() - start, chunk) for chunk in response.iter_raw()]
                    self.assertEqual(response.status_code, 200)
                    self.assertGreaterEqual(packets[0][0], 3.5)
                    self.assertLess(packets[0][0], 5.8)
                    self.assertGreater(packets[-1][0] - packets[0][0], .5)
                    self.assertIn(b'data: [DONE]', b"".join(chunk for _, chunk in packets))
                self.assertEqual(len(requests), 1)
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                sock.close()
                asyncio.run(client.aclose())
