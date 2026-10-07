"""Corre el agente, persiste el hilo y guarda la traza ReAct."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from grafo import RECURSION_LIMIT, config_hilo, construir_grafo

RAIZ = Path(__file__).resolve().parent
TRAZA = RAIZ / "traza_ejecucion.json"
CHECKPOINTS = RAIZ / "checkpoints.sqlite"

HILO = "cliente-102"
HILO_ERROR = "cliente-inexistente"


def extraer_texto(mensaje: BaseMessage) -> str:
    """Normaliza el content de un mensaje (a veces llega como lista de bloques)."""
    contenido: str | list[str | dict[str, Any]] = mensaje.content
    if isinstance(contenido, str):
        return contenido
    partes: list[str] = []
    for bloque in contenido:
        if isinstance(bloque, str):
            partes.append(bloque)
        elif isinstance(bloque, dict):
            partes.append(str(bloque.get("text", "")))
    return "".join(partes)


def serializar_traza(mensajes: list[BaseMessage]) -> list[dict[str, Any]]:
    """Convierte los mensajes de LangGraph a un JSON simple para el repo."""
    traza: list[dict[str, Any]] = []
    for mensaje in mensajes:
        entrada: dict[str, Any] = {
            "tipo": type(mensaje).__name__,
            "contenido": extraer_texto(mensaje),
        }
        if isinstance(mensaje, AIMessage) and mensaje.tool_calls:
            entrada["tool_calls"] = [
                {"nombre": llamada["name"], "argumentos": llamada["args"]}
                for llamada in mensaje.tool_calls
            ]
        if isinstance(mensaje, ToolMessage):
            entrada["herramienta"] = mensaje.name
        traza.append(entrada)
    return traza


async def main() -> None:
    load_dotenv(RAIZ / ".env")

    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINTS)) as checkpointer:
        app = construir_grafo(checkpointer)

        print("=" * 80)
        print("Turno 1: '¿Cuántos pedidos tuvo el cliente 102 y cuál fue el total?'")
        print("=" * 80)
        resultado1 = await app.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content="¿Cuántos pedidos tuvo el cliente 102 y cuál fue el total?"
                    )
                ]
            },
            config=config_hilo(HILO),
        )
        print(extraer_texto(resultado1["messages"][-1]))

        print("\n" + "=" * 80)
        print("Turno 2 (mismo thread_id): '¿y el último?'")
        print("=" * 80)
        resultado2 = await app.ainvoke(
            {"messages": [HumanMessage(content="¿y el último?")]},
            config=config_hilo(HILO),
        )
        print(extraer_texto(resultado2["messages"][-1]))

        print("\n" + "=" * 80)
        print("Error: '¿Cuántos pedidos tuvo el cliente 999 y cuál fue el total?'")
        print("=" * 80)
        resultado_error = await app.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content="¿Cuántos pedidos tuvo el cliente 999 y cuál fue el total?"
                    )
                ]
            },
            config=config_hilo(HILO_ERROR),
        )
        print(extraer_texto(resultado_error["messages"][-1]))

    traza = {
        "recursion_limit": RECURSION_LIMIT,
        "turno_1_multi_paso": serializar_traza(resultado1["messages"]),
        "turno_2_memoria": serializar_traza(resultado2["messages"]),
        "prueba_error_y_aclaracion": serializar_traza(resultado_error["messages"]),
    }
    TRAZA.write_text(
        json.dumps(traza, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nTraza guardada en {TRAZA.name}")


if __name__ == "__main__":
    asyncio.run(main())
