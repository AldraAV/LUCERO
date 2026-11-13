"""
excel_surgeon.py - Motor de Cirugia Quirurgica y Curacion de Datos para Libros Excel (.xlsx).
Preservacion de formulas, formato OOXML y arquitectura clave:valor.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter, coordinate_to_tuple

from .utils import get_logger

log = get_logger("excel_surgeon")


class ExcelSurgeon:
    """Operaciones quirurgicas sobre hojas de calculo Excel (.xlsx)."""

    @staticmethod
    def inspect_sheets(excel_path: str) -> dict[str, Any]:
        """
        Inspecciona la totalidad de hojas de un libro Excel:
        nombre, visibilidad, dimensiones, total de filas y columnas, tablas y celdas combinadas.
        """
        p = Path(excel_path)
        if not p.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {excel_path}")

        wb = openpyxl.load_workbook(p, read_only=False, data_only=False)
        resultado: dict[str, Any] = {
            "archivo": str(p),
            "total_hojas": len(wb.sheetnames),
            "hojas": []
        }

        for nombre in wb.sheetnames:
            ws = wb[nombre]
            info_hoja = {
                "nombre": nombre,
                "estado_visibilidad": ws.sheet_state,
                "dimensiones": ws.dimensions,
                "max_filas": ws.max_row,
                "max_columnas": ws.max_column,
                "celdas_combinadas": [str(r) for r in ws.merged_cells.ranges],
                "tablas": list(ws.tables.keys()) if hasattr(ws, "tables") else []
            }
            resultado["hojas"].append(info_hoja)

        wb.close()
        return resultado

    @staticmethod
    def inspect_cells(
        excel_path: str,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        max_rows: int = 100
    ) -> dict[str, Any]:
        """
        Inspecciona en profundidad un rango de celdas o filas de una hoja de calculo:
        extrae valores, formulas, tipos de datos y metadatos de estilo.
        """
        p = Path(excel_path)
        if not p.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {excel_path}")

        wb = openpyxl.load_workbook(p, data_only=False)
        wb_data = openpyxl.load_workbook(p, data_only=True)
        nombre_hoja = sheet_name if sheet_name and sheet_name in wb.sheetnames else wb.active.title
        ws = wb[nombre_hoja]
        ws_data = wb_data[nombre_hoja]

        celdas_resultado: dict[str, Any] = {}

        if cell_range:
            rango = ws[cell_range]
            if isinstance(rango, openpyxl.cell.cell.Cell):
                rango_filas = ((rango,),)
            elif isinstance(rango, tuple) and len(rango) > 0 and isinstance(rango[0], openpyxl.cell.cell.Cell):
                rango_filas = (rango,)
            else:
                rango_filas = rango
        else:
            rango_filas = ws.iter_rows(max_row=max_rows)

        filas_procesadas = 0
        for fila in rango_filas:
            filas_procesadas += 1
            if filas_procesadas > max_rows:
                break
            for celda in fila:
                if celda is None or (celda.value is None and not celda.comment):
                    continue

                coord = celda.coordinate
                val = celda.value
                val_calc = ws_data[coord].value if ws_data is not None else None
                es_formula = str(val).startswith("=") if val is not None else False

                estilo_info = {
                    "fuente": celda.font.name if celda.font else None,
                    "tamano": celda.font.size if celda.font else None,
                    "negrita": celda.font.bold if celda.font else False,
                    "cursiva": celda.font.italic if celda.font else False,
                    "color_fuente": str(celda.font.color.rgb) if (celda.font and celda.font.color and hasattr(celda.font.color, "rgb")) else None,
                    "formato_numero": celda.number_format,
                    "alineacion": celda.alignment.horizontal if celda.alignment else None
                }

                celdas_resultado[coord] = {
                    "valor": str(val) if val is not None else "",
                    "valor_calculado": val_calc,
                    "tipo_dato": celda.data_type,
                    "es_formula": es_formula,
                    "estilo": estilo_info
                }

        wb.close()
        wb_data.close()

        wb.close()
        return {
            "archivo": str(p),
            "hoja": ws.title,
            "rango_inspeccionado": cell_range or f"A1:{get_column_letter(ws.max_column)}{min(ws.max_row, max_rows)}",
            "total_celdas_con_dato": len(celdas_resultado),
            "celdas": celdas_resultado
        }

    @staticmethod
    def surgical_replace_cell(
        excel_path: str,
        coordinate: str,
        new_value: str,
        sheet_name: str | None = None,
        is_formula: bool = False,
        output_path: str | None = None
    ) -> dict[str, Any]:
        """
        Modifica atomicamente una celda en una hoja de Excel preservando estilos originales.
        """
        p = Path(excel_path)
        if not p.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {excel_path}")

        destino = Path(output_path) if output_path else p
        wb = openpyxl.load_workbook(p)
        ws = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

        celda = ws[coordinate]
        valor_anterior = str(celda.value) if celda.value is not None else ""

        if is_formula or (isinstance(new_value, str) and new_value.startswith("=")):
            celda.value = new_value
        else:
            try:
                if "." in new_value:
                    celda.value = float(new_value)
                else:
                    celda.value = int(new_value)
            except ValueError:
                celda.value = new_value

        wb.save(destino)
        wb.close()

        log.info("[EXCEL CIRUGIA] Reemplazo atómico en %s:%s ('%s' -> '%s')", ws.title, coordinate, valor_anterior, new_value)
        return {
            "exito": True,
            "archivo_salida": str(destino),
            "hoja": ws.title,
            "coordenada": coordinate,
            "valor_anterior": valor_anterior,
            "nuevo_valor": str(celda.value)
        }

    @staticmethod
    def surgical_inject_table(
        excel_path: str,
        start_cell: str,
        headers: list[str],
        rows: list[list[Any]],
        sheet_name: str | None = None,
        table_name: str | None = None,
        apply_aurora_style: bool = False,
        output_path: str | None = None
    ) -> dict[str, Any]:
        """
        Inyecta una tabla completa o matriz estructurada clave:valor con ajuste de columnas y estilos opcionales.
        """
        p = Path(excel_path)
        if not p.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {excel_path}")

        destino = Path(output_path) if output_path else p
        wb = openpyxl.load_workbook(p)
        ws = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

        fila_ini, col_ini = coordinate_to_tuple(start_cell)

        # Inyectar encabezados
        for j, cabecera in enumerate(headers):
            col_actual = col_ini + j
            celda = ws.cell(row=fila_ini, column=col_actual, value=cabecera)
            if apply_aurora_style:
                # Estilo Aurora Obsidiana/Ambar
                celda.font = Font(name="Roboto", size=11, bold=True, color="F1F5F9")
                celda.fill = PatternFill(start_color="090D16", end_color="090D16", fill_type="solid")
                celda.alignment = Alignment(horizontal="center", vertical="center")

        # Inyectar filas
        borde_fino = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1")
        )

        for i, fila in enumerate(rows):
            fila_actual = fila_ini + 1 + i
            for j, val in enumerate(fila):
                col_actual = col_ini + j
                celda = ws.cell(row=fila_actual, column=col_actual)
                if isinstance(val, str) and val.startswith("="):
                    celda.value = val
                else:
                    try:
                        if isinstance(val, (int, float)):
                            celda.value = val
                        elif "." in str(val) and str(val).replace(".", "", 1).isdigit():
                            celda.value = float(val)
                        elif str(val).isdigit():
                            celda.value = int(val)
                        else:
                            celda.value = val
                    except Exception:
                        celda.value = val

                if apply_aurora_style:
                    celda.font = Font(name="Roboto", size=10)
                    celda.border = borde_fino
                    if i % 2 == 1:
                        celda.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        # Autoajuste de anchos de columna
        for j in range(len(headers)):
            col_letra = get_column_letter(col_ini + j)
            max_len = max(
                len(str(headers[j])),
                max((len(str(r[j])) for r in rows if j < len(r)), default=0)
            )
            ws.column_dimensions[col_letra].width = max(max_len + 4, 12)

        wb.save(destino)
        wb.close()

        log.info("[EXCEL INYECCION] Tabla inyectada en %s:%s (%d filas x %d columnas)", ws.title, start_cell, len(rows), len(headers))
        return {
            "exito": True,
            "archivo_salida": str(destino),
            "hoja": ws.title,
            "celda_inicio": start_cell,
            "total_encabezados": len(headers),
            "total_filas_inyectadas": len(rows)
        }

    @staticmethod
    def surgical_search_replace(
        excel_path: str,
        search_text: str,
        replace_text: str,
        sheet_name: str | None = None,
        exact_match: bool = False,
        output_path: str | None = None
    ) -> dict[str, Any]:
        """
        Busca y reemplaza cadenas en celdas de una o todas las hojas conservando formato.
        """
        p = Path(excel_path)
        if not p.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {excel_path}")

        destino = Path(output_path) if output_path else p
        wb = openpyxl.load_workbook(p)
        hojas = [wb[sheet_name]] if sheet_name and sheet_name in wb.sheetnames else wb.worksheets

        total_reemplazos = 0
        detalles_reemplazos: list[dict[str, str]] = []

        for ws in hojas:
            for fila in ws.iter_rows():
                for celda in fila:
                    if celda.value is None:
                        continue
                    # Si es fórmula, no tocamos
                    if str(celda.value).startswith("="):
                        continue

                    val_str = str(celda.value)
                    ocurre = False
                    nuevo_val = val_str

                    if exact_match and val_str == search_text:
                        ocurre = True
                        nuevo_val = replace_text
                    elif not exact_match and search_text in val_str:
                        ocurre = True
                        nuevo_val = val_str.replace(search_text, replace_text)

                    if ocurre:
                        try:
                            if "." in nuevo_val and nuevo_val.replace(".", "", 1).isdigit():
                                celda.value = float(nuevo_val)
                            elif nuevo_val.isdigit():
                                celda.value = int(nuevo_val)
                            else:
                                celda.value = nuevo_val
                        except Exception:
                            celda.value = nuevo_val

                        total_reemplazos += 1
                        detalles_reemplazos.append({
                            "hoja": ws.title,
                            "coordenada": celda.coordinate,
                            "antes": val_str,
                            "despues": str(celda.value)
                        })

        wb.save(destino)
        wb.close()

        log.info("[EXCEL REEMPLAZO GLOBAL] '%s' -> '%s' (%d ocurrencias)", search_text, replace_text, total_reemplazos)
        return {
            "exito": True,
            "archivo_salida": str(destino),
            "texto_buscado": search_text,
            "texto_reemplazo": replace_text,
            "total_reemplazos": total_reemplazos,
            "detalles": detalles_reemplazos
        }
