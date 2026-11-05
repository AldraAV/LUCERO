"""
xlsx_surgeon.py — Motor quirurgico para hojas de calculo Excel (.xlsx, .xlsm).
Opera con precision atomica sobre celdas, formulas, estilos, tablas y rangos
preservando al 100% el formato existente y permitiendo inyecciones con la
estetica sobria del Aldraverso.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils.cell import (
        coordinate_to_tuple,
        get_column_letter,
        range_boundaries,
    )
    from openpyxl.worksheet.table import Table, TableStyleInfo
except ImportError:
    openpyxl = None
    Alignment = Border = Font = PatternFill = Side = None
    coordinate_to_tuple = get_column_letter = range_boundaries = None
    Table = TableStyleInfo = None

from .utils import get_logger, validate_xlsx

registro = get_logger("lucero.xlsx_surgeon")


class ErrorXlsxSurgeon(Exception):
    """Excepcion base para errores del cirujano Excel."""
    pass


class ErrorHojaNoEncontrada(ErrorXlsxSurgeon):
    """Se lanza cuando una hoja solicitada no existe en el libro."""
    pass


class ErrorCeldaInvalida(ErrorXlsxSurgeon):
    """Se lanza cuando una coordenada o rango de celdas es invalido."""
    pass


class XlsxSurgeon:
    """
    Motor quirurgico soberano para hojas de calculo Excel.
    Permite inspeccionar la estructura tabular, alterar celdas atomicamente
    con preservacion total de fuentes/bordes/rellenos, inyectar tablas completas
    y buscar/reemplazar contenido sin corromper metadatos ni macros.
    """

    def __init__(
        self,
        ruta_excel: str | Path | None = None,
        solo_lectura: bool = False,
        mantener_vba: bool = True,
    ) -> None:
        if openpyxl is None:
            raise RuntimeError(
                "La libreria openpyxl no esta instalada en el entorno virtual."
            )

        self.ruta: Path | None = Path(ruta_excel) if ruta_excel else None
        self.solo_lectura: bool = solo_lectura
        self.mantener_vba: bool = mantener_vba
        self._libro: Any | None = None
        self._modificado: bool = False

        if self.ruta:
            validate_xlsx(self.ruta)
            registro.info("Cargando libro Excel: %s", self.ruta.name)
            self._libro = openpyxl.load_workbook(
                filename=str(self.ruta),
                read_only=self.solo_lectura,
                keep_vba=self.mantener_vba,
                data_only=False,
            )
            registro.debug(
                "Libro cargado con exito. Total hojas: %d",
                len(self._libro.sheetnames),
            )

    @property
    def libro(self) -> Any:
        """Instancia activa de openpyxl.Workbook."""
        if self._libro is None:
            registro.info("Creando nuevo libro Excel en memoria...")
            self._libro = openpyxl.Workbook()
        return self._libro

    @property
    def modificado(self) -> bool:
        """Indica si el libro ha sufrido modificaciones quirurgicas."""
        return self._modificado

    def _obtener_hoja(self, nombre_hoja: str | None = None) -> Any:
        """Resuelve y retorna la hoja solicitada o la activa por defecto."""
        if nombre_hoja:
            if nombre_hoja not in self.libro.sheetnames:
                raise ErrorHojaNoEncontrada(
                    f"La hoja '{nombre_hoja}' no existe en el libro. "
                    f"Hojas disponibles: {self.libro.sheetnames}"
                )
            return self.libro[nombre_hoja]
        return self.libro.active

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: INSPECCION DE ESTRUCTURA Y CELDAS
    # ─────────────────────────────────────────────────────────────────────────

    def inspeccionar_hojas(self) -> list[dict[str, Any]]:
        """
        Inspecciona los metadatos de todas las hojas del libro:
        nombre, visibilidad, dimensiones, conteo de filas/columnas, tablas y
        rangos de celdas combinadas.
        """
        registro.info("Inspeccionando hojas del libro...")
        informe_hojas: list[dict[str, Any]] = []

        for hoja in self.libro.worksheets:
            tablas_info: list[str] = (
                list(hoja.tables.keys())
                if hasattr(hoja, "tables") and hoja.tables
                else []
            )
            combinadas_info: list[str] = (
                [str(rango) for rango in hoja.merged_cells.ranges]
                if hasattr(hoja, "merged_cells") and hoja.merged_cells
                else []
            )

            informe_hojas.append({
                "nombre": hoja.title,
                "estado_visibilidad": getattr(hoja, "sheet_state", "visible"),
                "dimensiones": getattr(hoja, "dimensions", "A1"),
                "max_filas": hoja.max_row,
                "max_columnas": hoja.max_column,
                "total_tablas": len(tablas_info),
                "nombres_tablas": tablas_info,
                "celdas_combinadas": combinadas_info,
            })

        return informe_hojas

    def inspeccionar_celdas(
        self,
        nombre_hoja: str | None = None,
        rango_celdas: str | None = None,
        max_filas: int = 100,
    ) -> dict[str, Any]:
        """
        Extrae datos detallados y estilos de un rango de celdas o de las filas
        activas de una hoja, permitiendo al agente auditar valores, tipos y formato.
        """
        hoja = self._obtener_hoja(nombre_hoja)
        registro.info(
            "Inspeccionando celdas en hoja '%s' (rango: %s, max_filas: %d)...",
            hoja.title,
            rango_celdas or "automatico",
            max_filas,
        )

        celdas_resultado: list[dict[str, Any]] = []

        if rango_celdas:
            if ":" in rango_celdas:
                try:
                    min_col, min_row, max_col, max_row = range_boundaries(rango_celdas)
                except Exception as error_rango:
                    raise ErrorCeldaInvalida(
                        f"Rango de celdas invalido '{rango_celdas}': {error_rango}"
                    )
                limite_fila = min(max_row, min_row + max_filas - 1)
                iterador_filas = hoja.iter_rows(
                    min_row=min_row,
                    max_row=limite_fila,
                    min_col=min_col,
                    max_col=max_col,
                )
            else:
                celda_unica = hoja[rango_celdas]
                return {
                    "hoja": hoja.title,
                    "rango_inspeccionado": rango_celdas,
                    "total_celdas": 1,
                    "celdas": [self._extraer_info_celda(celda_unica)],
                }
        else:
            fila_final = min(hoja.max_row or 1, max_filas)
            col_final = hoja.max_column or 1
            iterador_filas = hoja.iter_rows(
                min_row=1,
                max_row=fila_final,
                min_col=1,
                max_col=col_final,
            )

        for fila in iterador_filas:
            for celda in fila:
                if celda.value is not None or celda.has_style:
                    celdas_resultado.append(self._extraer_info_celda(celda))

        return {
            "hoja": hoja.title,
            "rango_inspeccionado": rango_celdas or f"A1:{get_column_letter(hoja.max_column or 1)}{min(hoja.max_row or 1, max_filas)}",
            "total_celdas": len(celdas_resultado),
            "celdas": celdas_resultado,
        }

    def _extraer_info_celda(self, celda: Any) -> dict[str, Any]:
        """Extrae de forma limpia el valor, formula y estilo completo de una celda."""
        es_formula = False
        valor_str = None

        if celda.value is not None:
            valor_crudo = str(celda.value)
            es_formula = valor_crudo.startswith("=")
            valor_str = valor_crudo

        estilo_info: dict[str, Any] = {}
        if celda.has_style:
            fuente = celda.font
            if fuente:
                estilo_info["fuente"] = {
                    "nombre": fuente.name,
                    "tamano": fuente.size,
                    "negrita": bool(fuente.bold),
                    "cursiva": bool(fuente.italic),
                    "color": str(fuente.color.rgb) if fuente.color and fuente.color.rgb else None,
                }
            alineacion = celda.alignment
            if alineacion:
                estilo_info["alineacion"] = {
                    "horizontal": alineacion.horizontal,
                    "vertical": alineacion.vertical,
                    "ajuste_texto": bool(alineacion.wrap_text),
                }
            if celda.number_format:
                estilo_info["formato_numero"] = celda.number_format

            relleno = celda.fill
            if relleno and relleno.fill_type:
                estilo_info["relleno"] = {
                    "tipo": relleno.fill_type,
                    "color": str(relleno.start_color.rgb) if relleno.start_color and relleno.start_color.rgb else None,
                }

        letra_columna = getattr(celda, "column_letter", None)
        if not letra_columna and hasattr(celda, "column") and celda.column:
            letra_columna = get_column_letter(celda.column)

        return {
            "coordenada": getattr(celda, "coordinate", ""),
            "fila": getattr(celda, "row", 0),
            "columna": getattr(celda, "column", 0),
            "columna_letra": letra_columna or "",
            "valor": valor_str,
            "tipo_dato": getattr(celda, "data_type", "s"),
            "es_formula": es_formula,
            "estilo": estilo_info,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 2: CIRUGIA ATOMICA DE CELDAS Y TABLAS
    # ─────────────────────────────────────────────────────────────────────────

    def reemplazar_celda_quirurgica(
        self,
        nombre_hoja: str,
        coordenada: str,
        nuevo_valor: Any,
        es_formula: bool = False,
    ) -> dict[str, Any]:
        """
        Reemplaza el valor o formula de una celda garantizando la preservacion
        al 100% de sus estilos originales (fuente, borde, alineacion, formato numerico).
        """
        hoja = self._obtener_hoja(nombre_hoja)
        coordenada_limpia = coordenada.strip().upper()

        try:
            celda = hoja[coordenada_limpia]
        except Exception as error_coord:
            raise ErrorCeldaInvalida(
                f"Coordenada invalida '{coordenada}': {error_coord}"
            )

        valor_anterior = celda.value
        tipo_anterior = celda.data_type

        # Tratamiento inteligente del tipo de dato
        valor_a_asignar = nuevo_valor
        if es_formula or (isinstance(nuevo_valor, str) and nuevo_valor.strip().startswith("=")):
            valor_a_asignar = str(nuevo_valor).strip()
        elif isinstance(nuevo_valor, str):
            val_limpio = nuevo_valor.strip()
            # Intentar conversion a entero o decimal si representa un numero puro
            if re.fullmatch(r"^-?\d+$", val_limpio):
                try:
                    valor_a_asignar = int(val_limpio)
                except ValueError:
                    valor_a_asignar = val_limpio
            elif re.fullmatch(r"^-?\d+\.\d+$", val_limpio):
                try:
                    valor_a_asignar = float(val_limpio)
                except ValueError:
                    valor_a_asignar = val_limpio

        celda.value = valor_a_asignar
        self._modificado = True

        registro.info(
            "Cirugia celda [%s!%s]: '%s' -> '%s' (Estilos intactos)",
            nombre_hoja,
            coordenada_limpia,
            valor_anterior,
            valor_a_asignar,
        )

        return {
            "hoja": nombre_hoja,
            "coordenada": coordenada_limpia,
            "valor_anterior": str(valor_anterior),
            "valor_nuevo": str(valor_a_asignar),
            "tipo_anterior": tipo_anterior,
            "tipo_nuevo": celda.data_type,
            "estilo_preservado": True,
        }

    def inyectar_tabla_quirurgica(
        self,
        nombre_hoja: str,
        celda_inicio: str,
        encabezados: list[str],
        filas: list[list[Any]],
        nombre_tabla: str | None = None,
        aplicar_estilo_aurora: bool = False,
    ) -> dict[str, Any]:
        """
        Inserta una matriz estructurada de encabezados y filas a partir de una celda,
        con opcion de aplicar el sistema de estilo sobrio del Aldraverso y registrar
        la tabla formalmente en el libro.
        """
        hoja = self._obtener_hoja(nombre_hoja)
        coord_limpia = celda_inicio.strip().upper()

        try:
            fila_inicio, col_inicio = coordinate_to_tuple(coord_limpia)
        except Exception as error_coord:
            raise ErrorCeldaInvalida(
                f"Celda de inicio invalida '{celda_inicio}': {error_coord}"
            )

        total_columnas = len(encabezados)
        total_filas = len(filas)

        registro.info(
            "Inyectando tabla en [%s!%s]: %d columnas, %d filas",
            nombre_hoja,
            coord_limpia,
            total_columnas,
            total_filas,
        )

        # Paleta Aurora para cabecera sobria
        fuente_encabezado = Font(name="Space Grotesk", size=11, bold=True, color="FFFFFF")
        relleno_encabezado = PatternFill(
            start_color="1E293B", end_color="1E293B", fill_type="solid"
        )
        alineacion_encabezado = Alignment(horizontal="center", vertical="center", wrap_text=True)

        borde_sutil = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )
        fuente_datos = Font(name="Inter", size=10)
        alineacion_datos = Alignment(vertical="center")

        # 1. Escribir Encabezados
        for idx_col, texto_encabezado in enumerate(encabezados):
            col_actual = col_inicio + idx_col
            celda = hoja.cell(row=fila_inicio, column=col_actual, value=texto_encabezado)
            if aplicar_estilo_aurora:
                celda.font = fuente_encabezado
                celda.fill = relleno_encabezado
                celda.alignment = alineacion_encabezado
                celda.border = borde_sutil

        # 2. Escribir Filas de Datos
        for idx_fila, datos_fila in enumerate(filas):
            fila_actual = fila_inicio + 1 + idx_fila
            for idx_col in range(total_columnas):
                valor_celda = datos_fila[idx_col] if idx_col < len(datos_fila) else ""
                col_actual = col_inicio + idx_col
                celda = hoja.cell(row=fila_actual, column=col_actual, value=valor_celda)
                if aplicar_estilo_aurora:
                    celda.font = fuente_datos
                    celda.alignment = alineacion_datos
                    celda.border = borde_sutil

        # Autoajuste de anchos de columna
        for idx_col in range(total_columnas):
            letra_col = get_column_letter(col_inicio + idx_col)
            longitud_maxima = len(str(encabezados[idx_col]))
            for datos_fila in filas:
                if idx_col < len(datos_fila):
                    longitud_maxima = max(longitud_maxima, len(str(datos_fila[idx_col])))
            ancho_sugerido = max(longitud_maxima + 4, 12)
            hoja.column_dimensions[letra_col].width = min(ancho_sugerido, 50)

        col_fin_letra = get_column_letter(col_inicio + total_columnas - 1)
        fila_fin = fila_inicio + total_filas
        rango_total = f"{coord_limpia}:{col_fin_letra}{fila_fin}"

        # Registrar tabla estructurada si se solicita
        if nombre_tabla:
            nombre_tabla_sanitizado = re.sub(r"[^A-Za-z0-9_]", "_", nombre_tabla)
            tabla_excel = Table(displayName=nombre_tabla_sanitizado, ref=rango_total)
            if not aplicar_estilo_aurora:
                estilo_tabla = TableStyleInfo(
                    name="TableStyleLight1",
                    showFirstColumn=False,
                    showLastColumn=False,
                    showRowStripes=True,
                    showColumnStripes=False,
                )
                tabla_excel.tableStyleInfo = estilo_tabla
            hoja.add_table(tabla_excel)
            registro.info("Tabla estructurada '%s' registrada.", nombre_tabla_sanitizado)

        self._modificado = True

        return {
            "hoja": nombre_hoja,
            "rango_inyectado": rango_total,
            "total_filas_datos": total_filas,
            "total_columnas": total_columnas,
            "nombre_tabla": nombre_tabla,
            "estilo_aurora_aplicado": aplicar_estilo_aurora,
        }

    def buscar_y_reemplazar(
        self,
        texto_buscar: str,
        texto_reemplazo: str,
        nombre_hoja: str | None = None,
        coincidencia_exacta: bool = False,
    ) -> dict[str, Any]:
        """
        Busca y reemplaza cadenas de texto en celdas de una hoja (o todas las hojas),
        conservando intactas todas las fuentes, rellenos, formulas y alineaciones.
        """
        hojas_a_procesar = [self._obtener_hoja(nombre_hoja)] if nombre_hoja else self.libro.worksheets
        reemplazos_efectuados: list[dict[str, str]] = []

        registro.info(
            "Buscando '%s' para reemplazar por '%s' (coincidencia_exacta=%s)...",
            texto_buscar,
            texto_reemplazo,
            coincidencia_exacta,
        )

        for hoja in hojas_a_procesar:
            for fila in hoja.iter_rows():
                for celda in fila:
                    if celda.value is not None and isinstance(celda.value, str):
                        valor_actual = celda.value
                        hubo_cambio = False
                        nuevo_valor = valor_actual

                        if coincidencia_exacta:
                            if valor_actual == texto_buscar:
                                nuevo_valor = texto_reemplazo
                                hubo_cambio = True
                        else:
                            if texto_buscar in valor_actual:
                                nuevo_valor = valor_actual.replace(texto_buscar, texto_reemplazo)
                                hubo_cambio = True

                        if hubo_cambio:
                            celda.value = nuevo_valor
                            reemplazos_efectuados.append({
                                "hoja": hoja.title,
                                "coordenada": celda.coordinate,
                                "valor_previo": valor_actual,
                                "valor_nuevo": nuevo_valor,
                            })

        if reemplazos_efectuados:
            self._modificado = True

        registro.info("Reemplazos concluidos: %d celdas modificadas.", len(reemplazos_efectuados))

        return {
            "texto_buscado": texto_buscar,
            "texto_reemplazo": texto_reemplazo,
            "total_reemplazos": len(reemplazos_efectuados),
            "detalles": reemplazos_efectuados,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # GUARDADO Y CONSOLIDACION
    # ─────────────────────────────────────────────────────────────────────────

    def guardar(self, ruta_destino: str | Path | None = None) -> Path:
        """
        Guarda el libro en disco. Si no se indica ruta de destino,
        sobreescribe el archivo de origen preservando la integridad.
        """
        destino = Path(ruta_destino) if ruta_destino else self.ruta
        if not destino:
            raise ErrorXlsxSurgeon(
                "No se especifico ninguna ruta de destino para guardar el archivo Excel."
            )

        destino.parent.mkdir(parents=True, exist_ok=True)
        registro.info("Guardando libro en: %s", destino.resolve())
        self.libro.save(str(destino))
        self._modificado = False
        registro.info("Libro guardado exitosamente.")
        return destino.resolve()


# Alias soberano en espanol
CirujanoXlsx = XlsxSurgeon
