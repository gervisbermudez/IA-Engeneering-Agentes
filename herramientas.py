"""Herramientas del agente. Simulan la base de pedidos de TechCorp."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

# 4200 + 6100 + 4200 = 14500. El último pedido es el 9003.
_PEDIDOS: dict[int, list[dict[str, Any]]] = {
    102: [
        {"pedido_id": 9001, "fecha": "2026-01-12", "total": 4200},
        {"pedido_id": 9002, "fecha": "2026-03-04", "total": 6100},
        {"pedido_id": 9003, "fecha": "2026-06-18", "total": 4200},
    ],
    205: [
        {"pedido_id": 9101, "fecha": "2026-04-01", "total": 3200},
    ],
}


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


@tool
def buscar_pedidos(cliente_id: int) -> str:
    """Lista cuántos pedidos tiene un cliente en la base de TechCorp.

    Usala cuando el usuario pregunte por los pedidos de un cliente y ya
    tengas su cliente_id numérico (por ejemplo 102). No acepta nombres.

    El resultado trae la cantidad y los ids, pero no el monto total: el
    campo ``incompleto`` queda en true. No inventes el total. Para el
    importe llamá a ``total_pedidos`` con el mismo cliente_id.

    Si el cliente no existe, devuelve un error. No repitas esa llamada:
    pedile al usuario que confirme el id.
    """
    if cliente_id <= 0:
        return _json(
            {
                "ok": False,
                "error": "cliente_id_invalido",
                "detalle": "El cliente_id tiene que ser un entero positivo.",
            }
        )

    pedidos = _PEDIDOS.get(cliente_id)
    if pedidos is None:
        return _json(
            {
                "ok": False,
                "error": "cliente_no_encontrado",
                "detalle": (
                    f"No hay pedidos para el cliente {cliente_id}. "
                    "Pedile al usuario que confirme el identificador."
                ),
            }
        )

    return _json(
        {
            "ok": True,
            "cliente_id": cliente_id,
            "pedidos": len(pedidos),
            "pedido_ids": [pedido["pedido_id"] for pedido in pedidos],
            "incompleto": True,
            "aviso": (
                "Este listado no trae el monto total. "
                "Llamá a total_pedidos con el mismo cliente_id."
            ),
        }
    )


@tool
def total_pedidos(cliente_id: int) -> str:
    """Devuelve el monto total de los pedidos de un cliente.

    Usala después de ``buscar_pedidos``, cuando el listado venga con
    ``incompleto: true`` y el usuario haya pedido el total. Una llamada
    alcanza para el monto. No dice cuál fue el último pedido: para eso
    está ``ultimo_pedido``.

    Si el cliente no existe, devuelve un error. No repitas el mismo id.
    """
    pedidos = _PEDIDOS.get(cliente_id)
    if pedidos is None:
        return _json(
            {
                "ok": False,
                "error": "cliente_no_encontrado",
                "detalle": (
                    f"No hay pedidos para el cliente {cliente_id}. "
                    "Confirmá el id con el usuario."
                ),
            }
        )

    return _json(
        {
            "ok": True,
            "cliente_id": cliente_id,
            "pedidos": len(pedidos),
            "total": sum(int(pedido["total"]) for pedido in pedidos),
        }
    )


@tool
def ultimo_pedido(cliente_id: int) -> str:
    """Devuelve el pedido más reciente de un cliente: id, fecha e importe.

    Usala cuando pregunten por el último pedido. Si el hilo ya tiene el
    cliente_id de una consulta anterior, reutilizá ese id: no se lo
    vuelvas a pedir al usuario.

    Si el cliente no existe, devuelve un error.
    """
    pedidos = _PEDIDOS.get(cliente_id)
    if not pedidos:
        return _json(
            {
                "ok": False,
                "error": "cliente_no_encontrado",
                "detalle": (
                    f"No hay pedidos para el cliente {cliente_id}. "
                    "Confirmá el id con el usuario."
                ),
            }
        )

    ultimo = max(pedidos, key=lambda pedido: str(pedido["fecha"]))
    return _json({"ok": True, "cliente_id": cliente_id, "ultimo": ultimo})


herramientas = [buscar_pedidos, total_pedidos, ultimo_pedido]
