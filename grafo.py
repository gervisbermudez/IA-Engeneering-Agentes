"""StateGraph ReAct: nodo del modelo, nodo de herramientas y ciclo."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from herramientas import herramientas

RECURSION_LIMIT = 10

_SISTEMA = SystemMessage(
    content=(
        "Sos el agente de pedidos de TechCorp. Respondé en español y con las "
        "cifras exactas que devuelvan las herramientas.\n"
        "No inventes cantidades ni importes.\n"
        "buscar_pedidos no trae el total: si el usuario lo pide y el resultado "
        "dice incompleto, llamá a total_pedidos.\n"
        "Si una herramienta devuelve un error, no repitas la misma llamada. "
        "Pedile al usuario que aclare el dato.\n"
        "Si preguntan por el último pedido y el hilo ya tiene el cliente_id, "
        "llamá a ultimo_pedido con ese id."
    )
)


class EstadoAgente(MessagesState):
    """Esquema del estado. Hereda ``messages`` y el reducer ``add_messages``."""


def armar_llm() -> BaseChatModel:
    """OpenAI por defecto. Gemini si LLM_PROVIDER=gemini."""
    proveedor = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if proveedor == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model="gpt-4.1-mini", temperature=0)


def construir_grafo(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Compila el ciclo modelo → herramienta → modelo.

    El modelo decide solo, con ``bind_tools``, si hace falta una herramienta.
    ``tools_condition`` vuelve al nodo de herramientas o termina.
    El checkpointer es ``AsyncSqliteSaver``: el SqliteSaver de LangGraph para
    asyncio. El ``SqliteSaver`` síncrono no implementa los métodos async.
    """
    llm = armar_llm().bind_tools(herramientas)

    async def nodo_modelo(state: EstadoAgente) -> dict[str, list[BaseMessage]]:
        """Pasa el historial al LLM. La respuesta puede traer tool_calls o ser el texto final."""
        respuesta = await llm.ainvoke([_SISTEMA, *state["messages"]])
        return {"messages": [respuesta]}

    grafo: StateGraph[EstadoAgente] = StateGraph(EstadoAgente)
    grafo.add_node("modelo", nodo_modelo)
    grafo.add_node("herramientas", ToolNode(herramientas, handle_tool_errors=True))
    grafo.add_edge(START, "modelo")
    grafo.add_conditional_edges(
        "modelo",
        tools_condition,
        {"tools": "herramientas", END: END},
    )
    grafo.add_edge("herramientas", "modelo")
    return grafo.compile(checkpointer=checkpointer)


def config_hilo(thread_id: str) -> RunnableConfig:
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": RECURSION_LIMIT,
    }
    return config
