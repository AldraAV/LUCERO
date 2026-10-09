from .apa_templates import TEMPLATE_CATALOG
from .humanizador import humanizar_documento_completo
from .pptx_surgeon import PptxSurgeon
from .surgeon import DocxSurgeon
from .utils import NS, get_logger

__all__ = ["NS", "TEMPLATE_CATALOG", "DocxSurgeon", "PptxSurgeon", "get_logger", "humanizar_documento_completo"]
__version__ = "1.0.0"
