import io

import pytest

from peddler.mcp.transport import Transport, TransportError


def test_round_trip_through_shared_stringio():
    buf = io.StringIO()
    Transport(stdin=io.StringIO(), stdout=buf).write_message({"a": 1})
    buf.seek(0)
    result = Transport(stdin=buf, stdout=io.StringIO()).read_message()
    assert result == {"a": 1}


def test_read_message_on_empty_stream_returns_none():
    transport = Transport(stdin=io.StringIO(""), stdout=io.StringIO())
    assert transport.read_message() is None


def test_read_message_skips_blank_line():
    transport = Transport(stdin=io.StringIO('\n{"x": 1}\n'), stdout=io.StringIO())
    assert transport.read_message() == {"x": 1}


def test_read_message_raises_on_invalid_json():
    transport = Transport(stdin=io.StringIO("not json\n"), stdout=io.StringIO())
    with pytest.raises(TransportError):
        transport.read_message()


def test_read_message_raises_on_non_object_json():
    transport = Transport(stdin=io.StringIO("[1, 2]\n"), stdout=io.StringIO())
    with pytest.raises(TransportError):
        transport.read_message()


def test_write_message_ends_with_single_newline_and_escapes_embedded_newlines():
    buf = io.StringIO()
    Transport(stdin=io.StringIO(), stdout=buf).write_message({"text": "line1\nline2"})
    output = buf.getvalue()
    assert output.endswith("\n")
    assert output.count("\n") == 1


def test_read_message_returns_none_after_exhausting_all_lines():
    transport = Transport(stdin=io.StringIO('{"a": 1}\n'), stdout=io.StringIO())
    assert transport.read_message() == {"a": 1}
    assert transport.read_message() is None


def test_write_message_flushes_stdout():
    class _UnflushedStream:
        """A stream whose .write() alone proves nothing was actually sent.

        Real OS pipes (unlike io.StringIO) are block-buffered when not a
        TTY: a write() can sit in the buffer indefinitely without an
        explicit flush(), which is exactly what broke the real MCP
        server -- Claude Code never saw a response until the process
        happened to exit. This fake tracks flush() calls explicitly so
        the test fails if write_message() only writes without flushing.
        """

        def __init__(self):
            self.written = ""
            self.flushed = False

        def write(self, data):
            self.written += data

        def flush(self):
            self.flushed = True

    stream = _UnflushedStream()
    Transport(stdin=io.StringIO(), stdout=stream).write_message({"a": 1})

    assert stream.flushed is True
