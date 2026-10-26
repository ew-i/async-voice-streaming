"""Play ElevenLabs text-to-speech audio while it is still being received.

A background thread receives audio chunks into a bounded buffer while the main
thread plays them back, so playback starts with the first chunk.
"""

import logging
import os
import sys
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from queue import Empty, Full, Queue

from elevenlabs import stream as play_audio_stream
from elevenlabs.client import ElevenLabs
from elevenlabs.core import RequestOptions

logger = logging.getLogger(__name__)

API_KEY_ENV_VAR = "ELEVENLABS_API_KEY"
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MODEL_ID = "eleven_multilingual_v2"

MAX_BUFFERED_CHUNKS = 50
CONSUMER_WAIT_SECONDS = 5
PRODUCER_WAIT_SECONDS = 0.5
STALL_TIMEOUT_SECONDS = 15

DEMO_TEXT = (
    "This is a simple python script showcasing asynchronous real-time voice streaming "
    "with the ElevenLabs API."
)


class _EndOfStream(Enum):
    TOKEN = "end of stream"


_END_OF_STREAM = _EndOfStream.TOKEN


class AudioBuffer:
    """Hands audio chunks from one producer thread to one consumer thread.

    The producer calls `put` and finally `close`; the consumer iterates over the
    buffer and calls `cancel` if it stops early, so a blocked producer can exit.
    """

    def __init__(self, max_chunks: int = MAX_BUFFERED_CHUNKS) -> None:
        self._items: Queue[bytes | _EndOfStream] = Queue(maxsize=max_chunks)
        self._cancelled = threading.Event()

    def put(self, chunk: bytes) -> bool:
        return self._offer(chunk)

    def close(self) -> None:
        self._offer(_END_OF_STREAM)

    def cancel(self) -> None:
        self._cancelled.set()

    def __iter__(self) -> Iterator[bytes]:
        while True:
            item = self._wait_for_item()
            if item is _END_OF_STREAM:
                return
            yield item

    def _offer(self, item: bytes | _EndOfStream) -> bool:
        while not self._cancelled.is_set():
            try:
                self._items.put(item, timeout=PRODUCER_WAIT_SECONDS)
                return True
            except Full:
                continue
        return False

    def _wait_for_item(self) -> bytes | _EndOfStream:
        while True:
            try:
                return self._items.get(timeout=CONSUMER_WAIT_SECONDS)
            except Empty:
                logger.warning(
                    "No audio received for %ss (network bottleneck?). Still waiting...",
                    CONSUMER_WAIT_SECONDS,
                )


def receive_audio_stream(
        client: ElevenLabs, text: str, voice_id: str, buffer: AudioBuffer
) -> None:
    logger.info("Receiving audio stream...")
    try:
        chunks = client.text_to_speech.stream(
            voice_id=voice_id,
            text=text,
            model_id=MODEL_ID,
            request_options=RequestOptions(timeout_in_seconds=STALL_TIMEOUT_SECONDS),
        )
        for chunk in chunks:
            if not chunk:
                continue
            if not buffer.put(chunk):
                logger.info("Playback stopped, closing audio stream.")
                return
            logger.debug("Buffered audio chunk (%d bytes).", len(chunk))
    finally:
        buffer.close()
        logger.info("Audio stream finished.")


def play_audio(buffer: AudioBuffer) -> None:
    logger.info("Starting audio playback...")
    try:
        play_audio_stream(iter(buffer))
    finally:
        buffer.cancel()


def stream_speech(client: ElevenLabs, text: str, voice_id: str = DEFAULT_VOICE_ID) -> None:
    if not text.strip():
        raise ValueError("Text to speak must not be empty.")

    buffer = AudioBuffer()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="ElevenLabs-Receiver") as pool:
        reception = pool.submit(receive_audio_stream, client, text, voice_id, buffer)
        play_audio(buffer)
        reception.result()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(threadName)s - %(message)s",
    )

    api_key = os.environ.get(API_KEY_ENV_VAR)
    if not api_key:
        logger.error("%s is missing from the environment variables.", API_KEY_ENV_VAR)
        return 1

    try:
        stream_speech(ElevenLabs(api_key=api_key), DEMO_TEXT)
    except Exception:
        logger.exception("Voice streaming failed.")
        return 1

    logger.info("Voice streaming completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
