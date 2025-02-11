from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

import pytest

from src.infra.arq.serializer import deserialize, serialize
from src.models.content_models import Chunk, Document, DocumentMetadata


@pytest.fixture
def sample_uuid() -> UUID:
    """Fixed UUID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    """Sample document metadata for testing."""
    return DocumentMetadata(
        title="Test Document",
        description="Test Description",
        source_url="https://example.com/test",
        og_url="https://example.com/test/og",
    )


@pytest.fixture
def sample_document(sample_uuid, sample_document_metadata) -> Document:
    """Sample document for testing."""
    return Document(
        document_id=sample_uuid,
        source_id=uuid4(),
        content="# Test Content\n\nThis is test content.",
        metadata=sample_document_metadata,
    )


@pytest.fixture
def sample_chunk(sample_uuid, sample_document) -> Chunk:
    """Sample chunk for testing."""
    return Chunk(
        chunk_id=sample_uuid,
        source_id=sample_document.source_id,
        document_id=sample_document.document_id,
        headers={"h1": "Test Header", "h2": "Subheader"},
        text="This is test chunk content",
        token_count=10,
        page_title="Test Page",
        page_url="https://example.com/test",
    )


@pytest.fixture
def complex_test_data(sample_document, sample_chunk) -> dict:
    """Complex nested structure with various types for testing."""
    return {
        "uuid": uuid4(),
        "datetime": datetime.now(UTC),
        "document": sample_document,
        "chunks": [sample_chunk, sample_chunk],
        "metadata": {"ids": [uuid4(), uuid4()], "nested_doc": sample_document},
        "simple_types": [1, "test", True, None],
        "mixed_list": [uuid4(), sample_document, {"key": "value"}, [1, 2, 3]],
    }


def test_pydantic_model_serialization(sample_document):
    """Test serialization/deserialization of a Pydantic model."""
    serialized = serialize({"data": sample_document})
    deserialized = deserialize(serialized)

    assert isinstance(deserialized["data"], Document)
    assert deserialized["data"].document_id == sample_document.document_id
    assert deserialized["data"].content == sample_document.content
    assert isinstance(deserialized["data"].metadata, DocumentMetadata)


def test_nested_pydantic_model_serialization(sample_chunk):
    """Test serialization/deserialization of nested Pydantic models."""
    serialized = serialize({"data": sample_chunk})
    deserialized = deserialize(serialized)

    assert isinstance(deserialized["data"], Chunk)
    assert deserialized["data"].chunk_id == sample_chunk.chunk_id
    assert deserialized["data"].headers == sample_chunk.headers
    assert isinstance(deserialized["data"].headers, dict)


def test_uuid_serialization(sample_uuid):
    """Test UUID serialization/deserialization."""
    serialized = serialize({"uuid": sample_uuid})
    deserialized = deserialize(serialized)

    assert isinstance(deserialized["uuid"], UUID)
    assert deserialized["uuid"] == sample_uuid


def test_complex_structure_serialization(complex_test_data):
    """Test serialization/deserialization of complex nested structure."""
    serialized = serialize({"data": complex_test_data})
    deserialized = deserialize(serialized)["data"]

    # Check types and values
    assert isinstance(deserialized["uuid"], UUID)
    assert isinstance(deserialized["datetime"], datetime)
    assert isinstance(deserialized["document"], Document)
    assert isinstance(deserialized["chunks"][0], Chunk)
    assert isinstance(deserialized["metadata"]["ids"][0], UUID)
    assert isinstance(deserialized["metadata"]["nested_doc"], Document)

    # Check simple types
    assert deserialized["simple_types"] == complex_test_data["simple_types"]

    # Check mixed list
    assert isinstance(deserialized["mixed_list"][0], UUID)
    assert isinstance(deserialized["mixed_list"][1], Document)
    assert isinstance(deserialized["mixed_list"][2], dict)
    assert isinstance(deserialized["mixed_list"][3], list)


def test_error_handling():
    """Test error handling during serialization/deserialization."""

    # Create an object that can't be serialized
    class UnserializableObject:
        def __init__(self):
            self.x = lambda: None

    with pytest.raises(Exception):
        serialize({"data": UnserializableObject()})


def test_serialization_roundtrip(complex_test_data):
    """Test complete serialization roundtrip with equality checks."""
    serialized = serialize({"data": complex_test_data})
    deserialized = deserialize(serialized)["data"]

    # Check document equality
    assert deserialized["document"].document_id == complex_test_data["document"].document_id
    assert deserialized["document"].content == complex_test_data["document"].content

    # Check chunk equality
    assert deserialized["chunks"][0].chunk_id == complex_test_data["chunks"][0].chunk_id
    assert deserialized["chunks"][0].text == complex_test_data["chunks"][0].text


def test_date_serialization():
    """Test serialization of date objects."""
    test_date = date(1969, 7, 20)  # Pre-1970 date (Moon landing)
    serialized = serialize({"date": test_date})
    deserialized = deserialize(serialized)

    assert isinstance(deserialized["date"], date)
    assert deserialized["date"] == test_date
    assert deserialized["date"].year == 1969
    assert deserialized["date"].month == 7
    assert deserialized["date"].day == 20


def test_time_serialization():
    """Test serialization of time objects."""
    test_time = time(23, 59, 59, 999999)  # Edge case with microseconds
    serialized = serialize({"time": test_time})
    deserialized = deserialize(serialized)

    assert isinstance(deserialized["time"], time)
    assert deserialized["time"] == test_time
    assert deserialized["time"].hour == 23
    assert deserialized["time"].minute == 59
    assert deserialized["time"].second == 59
    assert deserialized["time"].microsecond == 999999


def test_datetime_timezone_handling():
    """Test datetime serialization with different timezone scenarios."""
    from datetime import timedelta, timezone

    # UTC datetime
    utc_dt = datetime(2024, 3, 15, 12, 0, tzinfo=UTC)

    # Custom timezone datetime (UTC+2)
    custom_tz = timezone(timedelta(hours=2))
    tz_dt = datetime(2024, 3, 15, 14, 0, tzinfo=custom_tz)

    # Naive datetime
    naive_dt = datetime(2024, 3, 15, 12, 0)

    serialized = serialize({"utc": utc_dt, "custom_tz": tz_dt, "naive": naive_dt})
    deserialized = deserialize(serialized)

    # Check UTC datetime
    assert isinstance(deserialized["utc"], datetime)
    assert deserialized["utc"].tzinfo is not None
    assert deserialized["utc"] == utc_dt

    # Check custom timezone datetime
    assert isinstance(deserialized["custom_tz"], datetime)
    assert deserialized["custom_tz"].tzinfo is not None
    # Note: We don't compare exact timezone objects as they might be normalized to UTC
    assert deserialized["custom_tz"].isoformat() == tz_dt.isoformat()

    # Check naive datetime
    assert isinstance(deserialized["naive"], datetime)
    assert deserialized["naive"].tzinfo is None
    assert deserialized["naive"] == naive_dt
