from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DocumentFormat(str, Enum):
    DOCX = "docx"
    PDF = "pdf"
    MD = "md"
    TXT = "txt"
    PPTX = "pptx"

class ExtractType(str, Enum):
    FULL_TEXT = "full_text"
    METADATA = "metadata"
    TABLES = "tables"
    IMAGES = "images"
    ALL = "all"

class ReadDocumentRequest(BaseModel):
    file_path: str = Field(..., description="Path to document file")
    format: DocumentFormat | None = Field(None, description="Auto-detect if None")
    extract_type: ExtractType = Field(ExtractType.FULL_TEXT)
    include_metadata: bool = True
    
    @field_validator("file_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        from pathlib import Path
        if not Path(v).exists():
            raise ValueError(f"File not found: {v}")
        return v

class WriteDocumentRequest(BaseModel):
    file_path: str
    content: str
    format: DocumentFormat
    append: bool = False
    encrypt: bool = False
    style_template: str | None = None  # Name of predefined style

class TransformDocumentRequest(BaseModel):
    source_path: str
    target_format: DocumentFormat
    encrypt: bool = False
    compress: bool = False
    options: dict[str, Any] = Field(default_factory=dict)

class ProcessForAgentRequest(BaseModel):
    file_path: str
    chunk_size: int = 2000
    include_embeddings: bool = False
    include_metadata: bool = True
    output_format: Literal["json", "msgpack"] = "json"

class ToolResponse(BaseModel):
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    elapsed_ms: float = 0.0
    
class SchemaResponse(BaseModel):
    platform: str
    tools: list[dict[str, Any]]
    version: str = "1.0.0"
