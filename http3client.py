import asyncio
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import HeadersReceived, DataReceived
from aioquic.quic.configuration import QuicConfiguration

class Http3ClientProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.h3_connection = None
        self.done = asyncio.Event()
        self.stream_counter = 0  # Counter to manage stream IDs manually

    def quic_event_received(self, event):
        if self.h3_connection is None:
            self.h3_connection = H3Connection(self._quic)

        for http_event in self.h3_connection.handle_event(event):
            if isinstance(http_event, HeadersReceived):
                headers = [(key.decode(), value.decode()) for key, value in http_event.headers]
                print("Headers:", headers)
            elif isinstance(http_event, DataReceived):
                print("Data:", http_event.data.decode())
                self.done.set()

    async def fetch(self, method, path, headers=None):
        if headers is None:
            headers = []

        # Required HTTP/3 headers
        http_headers = [
            (b":method", method.encode()),
            (b":path", path.encode()),
            (b":scheme", b"https"),
            (b":authority", b"quic.aiortc.org"),
        ] + headers

        # Use a simple counter to assign stream IDs (even numbers for client-initiated streams)
        stream_id = self.stream_counter
        self.stream_counter += 4  # Increment by 4 to follow QUIC's stream ID rules

        # Send headers and data
        self.h3_connection.send_headers(stream_id, headers=http_headers)
        self.h3_connection.send_data(stream_id, b"", end_stream=True)

async def run():
    target = "quic.aiortc.org"
    port = 443

    # QUIC configuration
    configuration = QuicConfiguration(is_client=True, alpn_protocols=["h3"])

    async with connect(
        target, port, configuration=configuration, create_protocol=Http3ClientProtocol
    ) as protocol:
        client = protocol
        await client.fetch("GET", "/")
        await client.done.wait()

if __name__ == "__main__":
    asyncio.run(run())
