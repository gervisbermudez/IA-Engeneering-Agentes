# Pre-entrega 5: agente de razonamiento cíclico

Agente ReAct. El modelo decide, turno a turno, si llama a una herramienta o si ya puede responder. No hay un `if` que elija la herramienta.

## Requisitos

- Python 3.12
- Una clave de OpenAI (o de Gemini, si cambiás el proveedor)

## Cómo levantarlo

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Completá `.env`:

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=tu_clave_de_openai
```

Para usar Gemini, cambiá `LLM_PROVIDER=gemini` y completá `GOOGLE_API_KEY`.

```bash
python main.py
```

Eso corre tres turnos y escribe `traza_ejecucion.json`:

1. «¿Cuántos pedidos tuvo el cliente 102 y cuál fue el total?». `buscar_pedidos` no trae el importe, así que el modelo también llama a `total_pedidos`. Son dos herramientas para una sola respuesta.
2. «¿y el último?», con el mismo `thread_id` (`cliente-102`). El hilo ya tiene el cliente, así que llama a `ultimo_pedido(102)`.
3. «¿Cuántos pedidos tuvo el cliente 999 y cuál fue el total?». No está en la base: la herramienta devuelve un error y el modelo pide que confirmes el id.

`checkpoints.sqlite` guarda el checkpointer. No se sube al repo. `recursion_limit` está en 10.

La consigna nombra `SqliteSaver`. Esa clase es síncrona y no implementa los métodos async. El runtime del entregable es `asyncio`, así que el checkpointer es `AsyncSqliteSaver`: el mismo SQLite, con la interfaz que `ainvoke` necesita.

## Grafo

`EstadoAgente` hereda de `MessagesState`. Los mensajes se acumulan con el reducer `add_messages`.

```
START → modelo → tools_condition → herramientas → modelo → … → END
```

El modelo usa `bind_tools`. No hay un `if` que elija la herramienta. La arista `herramientas → modelo` es el ciclo.

## Herramientas

| Herramienta | Qué devuelve |
| --- | --- |
| `buscar_pedidos(cliente_id)` | Cantidad e ids. Sin total (`incompleto: true`), o un error si el id no existe. |
| `total_pedidos(cliente_id)` | `{"pedidos": 3, "total": 14500}` para el cliente 102. |
| `ultimo_pedido(cliente_id)` | Id, fecha e importe del pedido más reciente. |

El cliente 102 tiene 3 pedidos y un total de 14500. El último es el 9003, del 2026-06-18, por 4200.
