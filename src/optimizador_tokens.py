"""
optimizador_tokens.py — Utilidades de ahorro de tokens, paginacion y diffs compactos para LUCERO.
Garantiza respuestas JSON compactas, truncamiento seguro a 8,000 caracteres y navegacion por rangos.
"""

from __future__ import annotations

import difflib
import json
from typing import Any

LIMITE_CARACTERES_RESPUESTA: int = 8000


def serializar_respuesta_compacta(
    datos: Any,
    limite: int = LIMITE_CARACTERES_RESPUESTA,
    nota_paginacion: str | None = None,
) -> str:
    """
    Serializa datos a JSON compacto (sin indentacion) y aplica un limite duro de caracteres.
    Si excede el limite, trunca de forma segura e incluye instrucciones de paginacion.
    """
    if limite <= 0:
        raise ValueError("El limite de caracteres debe ser mayor que cero.")

    if isinstance(datos, str):
        texto_serializado = datos
    else:
        texto_serializado = json.dumps(
            datos,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

    if len(texto_serializado) <= limite:
        return texto_serializado

    margen_metadatos = 260
    corte = max(100, limite - margen_metadatos)
    instruccion = nota_paginacion or (
        "Usa parametros de rango o paginacion (offset/limit, start_line/end_line) para obtener el resto."
    )
    envoltura = {
        "truncado": True,
        "total_caracteres": len(texto_serializado),
        "limite_caracteres": limite,
        "nota_paginacion": instruccion,
        "contenido_parcial": texto_serializado[:corte],
    }
    return json.dumps(envoltura, ensure_ascii=False, separators=(",", ":"))


def paginar_lista(
    elementos: list[Any],
    inicio: int = 0,
    limite: int = 50,
) -> dict[str, Any]:
    """
    Pagina una lista devolviendo metadatos compactos de avance.
    """
    if inicio < 0:
        raise ValueError("El parametro 'inicio' (offset) no puede ser negativo.")
    if limite <= 0:
        raise ValueError("El parametro 'limite' debe ser mayor que cero.")

    total = len(elementos)
    fin = min(total, inicio + limite)
    rebanada = elementos[inicio:fin]
    hay_mas = fin < total

    resultado: dict[str, Any] = {
        "total": total,
        "inicio": inicio,
        "mostrados": len(rebanada),
        "hay_mas": hay_mas,
        "elementos": rebanada,
    }
    if hay_mas:
        resultado["siguiente_inicio"] = fin
    return resultado


def numerar_lineas(
    lineas: list[str],
    inicio_base_1: int = 1,
) -> str:
    """
    Formatea una lista de lineas prefijandolas con su numero de linea (ej. '42: contenido').
    """
    if inicio_base_1 < 1:
        raise ValueError("El numero inicial de linea debe ser >= 1.")
    return "\n".join(
        f"{idx}: {linea}"
        for idx, linea in enumerate(lineas, start=inicio_base_1)
    )


def extraer_rango_lineas(
    texto: str,
    linea_inicio: int | None = None,
    linea_fin: int | None = None,
) -> dict[str, Any]:
    """
    Extrae un rango de lineas (base 1, inclusivo) devolviendo las lineas numeradas.
    """
    if texto is None:
        raise ValueError("El texto de entrada no puede ser nulo.")

    todas = texto.splitlines()
    total_lineas = len(todas)

    if total_lineas == 0:
        return {
            "total_lineas": 0,
            "inicio": 0,
            "fin": 0,
            "contenido": "",
        }

    inicio = 1 if linea_inicio is None else max(1, linea_inicio)
    fin = total_lineas if linea_fin is None else min(total_lineas, linea_fin)

    if inicio > fin:
        return {
            "total_lineas": total_lineas,
            "inicio": inicio,
            "fin": fin,
            "contenido": "",
        }

    seleccion = todas[inicio - 1 : fin]
    return {
        "total_lineas": total_lineas,
        "inicio": inicio,
        "fin": fin,
        "contenido": numerar_lineas(seleccion, inicio_base_1=inicio),
    }


def buscar_con_contexto(
    texto: str,
    consulta: str,
    lineas_contexto: int = 2,
    max_coincidencias: int = 20,
    sensible_mayusculas: bool = False,
) -> dict[str, Any]:
    """
    Busca 'consulta' en 'texto' devolviendo coincidencias con margen superior e inferior
    y numeros de linea, evitando volcar el documento completo.
    """
    if not consulta or not consulta.strip():
        raise ValueError("La consulta de busqueda no puede estar vacia.")
    if lineas_contexto < 0:
        raise ValueError("Las lineas de contexto no pueden ser negativas.")
    if max_coincidencias <= 0:
        raise ValueError("El maximo de coincidencias debe ser mayor que cero.")

    todas = texto.splitlines()
    total_lineas = len(todas)
    objetivo = consulta if sensible_mayusculas else consulta.lower()

    coincidencias: list[dict[str, Any]] = []
    for idx, linea in enumerate(todas):
        comparar = linea if sensible_mayusculas else linea.lower()
        if objetivo in comparar:
            ini = max(0, idx - lineas_contexto)
            fin = min(total_lineas, idx + lineas_contexto + 1)
            fragmento = numerar_lineas(todas[ini:fin], inicio_base_1=ini + 1)
            coincidencias.append(
                {
                    "linea": idx + 1,
                    "fragmento": fragmento,
                }
            )
            if len(coincidencias) >= max_coincidencias:
                break

    return {
        "consulta": consulta,
        "total_lineas_documento": total_lineas,
        "total_coincidencias_mostradas": len(coincidencias),
        "coincidencias": coincidencias,
    }


def generar_diff_compacto(
    texto_antes: str,
    texto_despues: str,
    etiqueta: str = "documento",
    contexto: int = 1,
    limite_chars: int = 1200,
) -> str:
    """
    Genera un diff unificado compacto (-U1 por defecto) entre dos versiones de texto.
    """
    lineas_antes = (texto_antes or "").splitlines()
    lineas_despues = (texto_despues or "").splitlines()
    diff = list(
        difflib.unified_diff(
            lineas_antes,
            lineas_despues,
            fromfile=f"a/{etiqueta}",
            tofile=f"b/{etiqueta}",
            n=max(0, contexto),
            lineterm="",
        )
    )
    resultado = "\n".join(diff)
    if len(resultado) > limite_chars:
        return resultado[:limite_chars] + "\n...[diff truncado]"
    return resultado


def _formatear_escalar_toon(valor: Any) -> str:
    """Formatea un valor escalar en TOON, entrecomillando solo si es necesario."""
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return str(valor)
    texto = str(valor)
    if texto == "" or texto != texto.strip():
        return json.dumps(texto, ensure_ascii=False)
    caracteres_especiales = (",", ":", "\n", "\r", '"', "{", "}", "[", "]")
    if any(c in texto for c in caracteres_especiales):
        return json.dumps(texto, ensure_ascii=False)
    return texto


def _es_lista_tabular(elementos: list[Any]) -> list[str] | None:
    """
    Verifica si una lista de dicts es apta para formato tabular TOON.
    Devuelve las columnas si todos son dicts; de lo contrario None.
    """
    if not elementos or not all(isinstance(el, dict) for el in elementos):
        return None
    columnas: list[str] = []
    vistas: set[str] = set()
    for el in elementos:
        for clave in el.keys():
            clave_str = str(clave)
            if clave_str not in vistas:
                vistas.add(clave_str)
                columnas.append(clave_str)
    return columnas if columnas else None


def _formatear_celda_toon(valor: Any) -> str:
    """Formatea un valor dentro de una fila tabular TOON."""
    if isinstance(valor, (dict, list)):
        compacto = json.dumps(valor, ensure_ascii=False, separators=(",", ":"), default=str)
        return json.dumps(compacto, ensure_ascii=False)
    return _formatear_escalar_toon(valor)


def _renderizar_toon(datos: Any, nivel: int = 0, nombre_clave: str | None = None) -> list[str]:
    """Renderiza recursivamente estructuras Python a lineas TOON."""
    sangria = "  " * nivel
    prefijo = f"{sangria}{nombre_clave}" if nombre_clave is not None else sangria

    if isinstance(datos, dict):
        lineas: list[str] = []
        if nombre_clave is not None:
            lineas.append(f"{sangria}{nombre_clave}:")
            nivel_hijos = nivel + 1
        else:
            nivel_hijos = nivel
        for k, v in datos.items():
            lineas.extend(_renderizar_toon(v, nivel=nivel_hijos, nombre_clave=str(k)))
        return lineas

    if isinstance(datos, list):
        total = len(datos)
        columnas = _es_lista_tabular(datos)
        if columnas is not None:
            encabezado_cols = ",".join(columnas)
            clave_hdr = f"{prefijo}[{total}]{{{encabezado_cols}}}:" if nombre_clave else f"{sangria}[{total}]{{{encabezado_cols}}}:"
            lineas = [clave_hdr]
            sangria_fila = "  " * (nivel + 1)
            for fila in datos:
                celdas = [_formatear_celda_toon(fila.get(col)) for col in columnas]
                lineas.append(f"{sangria_fila}{','.join(celdas)}")
            return lineas

        if all(not isinstance(el, (dict, list)) for el in datos):
            valores = ",".join(_formatear_escalar_toon(el) for el in datos)
            clave_hdr = f"{prefijo}[{total}]:" if nombre_clave else f"{sangria}[{total}]:"
            return [f"{clave_hdr} {valores}" if valores else clave_hdr]

        clave_hdr = f"{prefijo}[{total}]:" if nombre_clave else f"{sangria}[{total}]:"
        lineas = [clave_hdr]
        for el in datos:
            if isinstance(el, dict):
                sub = _renderizar_toon(el, nivel=nivel + 1, nombre_clave=None)
                if sub:
                    primera = sub[0].lstrip()
                    lineas.append(f"{'  ' * (nivel + 1)}- {primera}")
                    lineas.extend(sub[1:])
            else:
                lineas.append(f"{'  ' * (nivel + 1)}- {_formatear_escalar_toon(el)}")
        return lineas

    valor_str = _formatear_escalar_toon(datos)
    if nombre_clave is not None:
        return [f"{prefijo}: {valor_str}"]
    return [f"{sangria}{valor_str}"]


def serializar_toon(
    datos: Any,
    limite: int = LIMITE_CARACTERES_RESPUESTA,
    nota_paginacion: str | None = None,
) -> str:
    """
    Serializa estructuras tabulares y jerarquicas en formato TOON (Token-Oriented Object Notation)
    para reducir significativamente el consumo de tokens, aplicando truncamiento seguro.
    """
    if limite <= 0:
        raise ValueError("El limite de caracteres debe ser mayor que cero.")

    texto = "\n".join(_renderizar_toon(datos))
    if len(texto) <= limite:
        return texto

    margen = 220
    corte = max(100, limite - margen)
    parcial = texto[:corte]
    ultimo_salto = parcial.rfind("\n")
    if ultimo_salto > 80:
        parcial = parcial[:ultimo_salto]

    instruccion = nota_paginacion or (
        "Usa parametros de rango o paginacion (offset/limit) para obtener el resto."
    )
    pie = (
        f"\ntruncado: true\n"
        f"total_caracteres: {len(texto)}\n"
        f"limite_caracteres: {limite}\n"
        f"nota_paginacion: {_formatear_escalar_toon(instruccion)}"
    )
    return parcial + pie
