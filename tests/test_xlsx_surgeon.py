"""
tests/test_xlsx_surgeon.py — Pruebas unitarias completas para XlsxSurgeon.
Valida inspeccion, cirugia atomica de celdas con preservacion de estilos,
inyeccion de tablas estructuradas y busqueda/reemplazo quirurgico.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import (
    inspect_excel_cells,
    inspect_excel_sheets,
    surgical_inject_excel_table,
    surgical_replace_excel_cell,
    surgical_search_replace_excel,
)
from src.xlsx_surgeon import (
    ErrorCeldaInvalida,
    ErrorHojaNoEncontrada,
    XlsxSurgeon,
)


@pytest.fixture
def libro_temporal(tmp_path: Path) -> Path:
    """Genera un archivo Excel sintetico con datos y formatos para pruebas."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Finanzas"

    # Encabezados con formato especifico
    ws["A1"] = "Concepto"
    ws["B1"] = "Monto"
    ws["C1"] = "Estado"

    fuente_encabezado = Font(name="Space Grotesk", size=12, bold=True, color="FFFFFF")
    relleno_encabezado = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    for celda_coord in ["A1", "B1", "C1"]:
        c = ws[celda_coord]
        c.font = fuente_encabezado
        c.fill = relleno_encabezado
        c.alignment = Alignment(horizontal="center")

    # Filas con datos y estilos
    datos = [
        ("Servidor Cloud", 1500, "Pagado"),
        ("Dominio Web", 25, "Pendiente"),
        ("Suscripcion API", 200, "Pagado"),
    ]

    borde_fino = Border(
        bottom=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
    )

    for idx, (concepto, monto, estado) in enumerate(datos, start=2):
        ws[f"A{idx}"] = concepto
        ws[f"B{idx}"] = monto
        ws[f"C{idx}"] = estado

        ws[f"A{idx}"].font = Font(name="Inter", size=10)
        ws[f"B{idx}"].font = Font(name="JetBrains Mono", size=10, bold=True)
        ws[f"B{idx}"].number_format = "$#,##0.00"
        ws[f"B{idx}"].border = borde_fino
        ws[f"C{idx}"].font = Font(name="Inter", size=10)

    # Formula
    ws["A5"] = "Total"
    ws["B5"] = "=SUM(B2:B4)"
    ws["B5"].font = Font(name="JetBrains Mono", size=11, bold=True)
    ws["B5"].number_format = "$#,##0.00"

    # Segunda hoja
    ws2 = wb.create_sheet(title="Metricas")
    ws2["A1"] = "KPI"
    ws2["B1"] = "Valor"
    ws2["A2"] = "Usuarios"
    ws2["B2"] = 12500

    ruta_archivo = tmp_path / "libro_prueba.xlsx"
    wb.save(str(ruta_archivo))
    return ruta_archivo


def test_inspeccionar_hojas(libro_temporal: Path) -> None:
    """Debe listar correctamente las hojas y sus metadatos."""
    cirujano = XlsxSurgeon(libro_temporal, solo_lectura=True)
    hojas = cirujano.inspeccionar_hojas()

    assert len(hojas) == 2
    nombres = [h["nombre"] for h in hojas]
    assert "Finanzas" in nombres
    assert "Metricas" in nombres

    hoja_finanzas = next(h for h in hojas if h["nombre"] == "Finanzas")
    assert hoja_finanzas["max_filas"] >= 5
    assert hoja_finanzas["max_columnas"] >= 3


def test_inspeccionar_celdas(libro_temporal: Path) -> None:
    """Debe extraer detalles de celda, formulas y estilos."""
    cirujano = XlsxSurgeon(libro_temporal, solo_lectura=True)
    resultado = cirujano.inspeccionar_celdas(nombre_hoja="Finanzas", rango_celdas="B2")

    assert resultado["total_celdas"] == 1
    celda = resultado["celdas"][0]
    assert celda["coordenada"] == "B2"
    assert celda["valor"] == "1500"
    assert celda["estilo"]["formato_numero"] == "$#,##0.00"
    assert celda["estilo"]["fuente"]["nombre"] == "JetBrains Mono"
    assert celda["estilo"]["fuente"]["negrita"] is True


def test_reemplazar_celda_quirurgica_preserva_estilo(libro_temporal: Path) -> None:
    """Debe modificar el valor de la celda conservando intacto su estilo."""
    cirujano = XlsxSurgeon(libro_temporal)
    informe = cirujano.reemplazar_celda_quirurgica(
        nombre_hoja="Finanzas",
        coordenada="B2",
        nuevo_valor="3500",
    )

    assert informe["valor_anterior"] == "1500"
    assert informe["valor_nuevo"] == "3500"
    assert informe["estilo_preservado"] is True

    ruta_salida = cirujano.guardar()
    assert ruta_salida.exists()

    # Recargar y verificar que el estilo no sufrio corrupcion
    cirujano_reabierto = XlsxSurgeon(ruta_salida, solo_lectura=True)
    celda_mod = cirujano_reabierto.inspeccionar_celdas(nombre_hoja="Finanzas", rango_celdas="B2")["celdas"][0]
    assert celda_mod["valor"] == "3500"
    assert celda_mod["estilo"]["formato_numero"] == "$#,##0.00"
    assert celda_mod["estilo"]["fuente"]["nombre"] == "JetBrains Mono"
    assert celda_mod["estilo"]["fuente"]["negrita"] is True


def test_reemplazar_celda_con_formula(libro_temporal: Path) -> None:
    """Debe permitir inyectar o modificar formulas."""
    cirujano = XlsxSurgeon(libro_temporal)
    informe = cirujano.reemplazar_celda_quirurgica(
        nombre_hoja="Finanzas",
        coordenada="B5",
        nuevo_valor="=SUM(B2:B3)",
        es_formula=True,
    )

    assert informe["valor_nuevo"] == "=SUM(B2:B3)"
    ruta_guardada = cirujano.guardar()

    cirujano_verif = XlsxSurgeon(ruta_guardada, solo_lectura=True)
    info_b5 = cirujano_verif.inspeccionar_celdas(nombre_hoja="Finanzas", rango_celdas="B5")["celdas"][0]
    assert info_b5["es_formula"] is True
    assert info_b5["valor"] == "=SUM(B2:B3)"


def test_inyectar_tabla_quirurgica(tmp_path: Path) -> None:
    """Debe inyectar tablas completas con formato sobrio de forma limpia."""
    archivo_nuevo = tmp_path / "tabla_inyectada.xlsx"
    cirujano = XlsxSurgeon()  # Nuevo en memoria

    encabezados = ["ID", "Producto", "Cantidad", "Precio Unitario"]
    filas = [
        ["P-001", "Sensor Optico", 10, 45.50],
        ["P-002", "Controlador Micro", 5, 120.00],
        ["P-003", "Modulo Rele", 20, 15.25],
    ]

    informe = cirujano.inyectar_tabla_quirurgica(
        nombre_hoja=None,  # hoja activa
        celda_inicio="B3",
        encabezados=encabezados,
        filas=filas,
        nombre_tabla="InventarioSensores",
        aplicar_estilo_aurora=True,
    )

    assert informe["total_filas_datos"] == 3
    assert informe["total_columnas"] == 4
    assert informe["rango_inyectado"] == "B3:E6"

    ruta_guardada = cirujano.guardar(archivo_nuevo)
    assert ruta_guardada.exists()

    # Verificar lectura
    cirujano_lectura = XlsxSurgeon(ruta_guardada)
    hojas = cirujano_lectura.inspeccionar_hojas()
    assert hojas[0]["total_tablas"] == 1
    assert "InventarioSensores" in hojas[0]["nombres_tablas"]


def test_buscar_y_reemplazar(libro_temporal: Path) -> None:
    """Debe reemplazar texto respetando la integridad de todas las celdas."""
    cirujano = XlsxSurgeon(libro_temporal)
    res = cirujano.buscar_y_reemplazar(
        texto_buscar="Pagado",
        texto_reemplazo="Liquidado",
    )

    assert res["total_reemplazos"] == 2
    ruta_salida = cirujano.guardar()

    cirujano_revisado = XlsxSurgeon(ruta_salida, solo_lectura=True)
    c3 = cirujano_revisado.inspeccionar_celdas(nombre_hoja="Finanzas", rango_celdas="C2")["celdas"][0]
    c4 = cirujano_revisado.inspeccionar_celdas(nombre_hoja="Finanzas", rango_celdas="C4")["celdas"][0]
    assert c3["valor"] == "Liquidado"
    assert c4["valor"] == "Liquidado"


def test_errores_esperados(libro_temporal: Path) -> None:
    """Debe lanzar excepciones semanticas descriptivas."""
    cirujano = XlsxSurgeon(libro_temporal)

    with pytest.raises(ErrorHojaNoEncontrada):
        cirujano.inspeccionar_celdas(nombre_hoja="HojaFantasma")

    with pytest.raises(ErrorCeldaInvalida):
        cirujano.reemplazar_celda_quirurgica(
            nombre_hoja="Finanzas",
            coordenada="ZZZZZZ$$$Invalida",
            nuevo_valor="Test",
        )


# ─────────────────────────────────────────────────────────────────────────────
# PRUEBAS E2E DE HERRAMIENTAS MCP DE EXCEL (server.py)
# ─────────────────────────────────────────────────────────────────────────────

def test_mcp_inspect_excel_sheets(libro_temporal: Path) -> None:
    """Valida la herramienta MCP inspect_excel_sheets."""
    res_raw = inspect_excel_sheets(str(libro_temporal))
    assert "error:" not in res_raw.lower()
    assert "Finanzas" in res_raw
    assert "Metricas" in res_raw
    assert "total_hojas: 2" in res_raw


def test_mcp_inspect_excel_cells(libro_temporal: Path) -> None:
    """Valida la herramienta MCP inspect_excel_cells."""
    res_raw = inspect_excel_cells(str(libro_temporal), sheet_name="Finanzas", cell_range="B2")
    assert "error:" not in res_raw.lower()
    assert "B2" in res_raw
    assert "1500" in res_raw


def test_mcp_surgical_replace_excel_cell(libro_temporal: Path, tmp_path: Path) -> None:
    """Valida la herramienta MCP surgical_replace_excel_cell."""
    salida = tmp_path / "mcp_replace.xlsx"
    res_raw = surgical_replace_excel_cell(
        excel_path=str(libro_temporal),
        coordinate="B2",
        new_value="8888",
        sheet_name="Finanzas",
        output_path=str(salida),
    )
    assert "error:" not in res_raw.lower()
    assert "8888" in res_raw
    assert salida.exists()


def test_mcp_surgical_inject_excel_table(libro_temporal: Path, tmp_path: Path) -> None:
    """Valida la herramienta MCP surgical_inject_excel_table."""
    salida = tmp_path / "mcp_tabla.xlsx"
    res_raw = surgical_inject_excel_table(
        excel_path=str(libro_temporal),
        start_cell="A10",
        headers=["Codigo", "Descripcion"],
        rows=[["C1", "Item Uno"], ["C2", "Item Dos"]],
        sheet_name="Finanzas",
        table_name="TablaMCP",
        output_path=str(salida),
    )
    assert "error:" not in res_raw.lower()
    assert "total_filas_datos: 2" in res_raw
    assert "total_columnas: 2" in res_raw
    assert salida.exists()


def test_mcp_surgical_search_replace_excel(libro_temporal: Path, tmp_path: Path) -> None:
    """Valida la herramienta MCP surgical_search_replace_excel."""
    salida = tmp_path / "mcp_buscar_reemplazar.xlsx"
    res_raw = surgical_search_replace_excel(
        excel_path=str(libro_temporal),
        search_text="Pagado",
        replace_text="Facturado",
        output_path=str(salida),
    )
    assert "error:" not in res_raw.lower()
    assert "total_reemplazos: 2" in res_raw
    assert salida.exists()

