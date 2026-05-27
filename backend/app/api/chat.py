"""Route POST /api/v1/chat — invocation de l'agent LangGraph avec checkpoints Mongo.

Deux endpoints :
- POST /chat : invocation synchrone, renvoie la réponse complète en JSON.
- POST /chat/stream : Server-Sent Events. Émet les tokens du LLM et les appels
  de tools au fil de l'eau. Format SSE standard (`event: <type>\\ndata: <json>\\n\\n`).
  Côté front, à consommer via fetch + ReadableStream (EventSource ne supporte
  que GET, or on POST un body JSON).
"""
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.api.deps import consume_quota
from app.models.chat import ChatRequest, ChatResponse, ToolCallTrace
from app.models.user import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Agent"])


def _build_user_message(payload: ChatRequest) -> str:
    """Compose le contenu du HumanMessage avec les tags de contexte du tour.

    Pourquoi des tags structurés plutôt qu'une phrase naturelle dans le texte ?
    - La FEN et la couleur user sont des FAITS dont le front est seule source
      de vérité (état UI). On ne veut pas que le LLM les infère depuis la
      conversation — l'inférence dérape quand l'historique est long ou
      contradictoire (cas reporté : user flip en cours de session, le LLM
      retombait sur la couleur d'origine au tour suivant).
    - Format `[Key: value]` = pattern facile à parser pour le LLM, déjà
      utilisé pour la FEN. Cohérence interne du prompt.
    """
    tags = [f"[user_color: {payload.user_color}]"]
    if payload.fen:
        tags.append(f"[Current board FEN: {payload.fen}]")
    return "\n".join(tags) + "\n\n" + payload.message


def _sse_event(event_type: str, data: dict) -> bytes:
    """Formate une frame SSE. Convention : `event:` + `data:` + blank line.

    JSON est sérialisé sur une seule ligne (pas de `indent=`) pour respecter
    le contrat SSE (data doit tenir sur une ligne, ou être préfixée multi-`data:`).
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    payload: ChatRequest,
    user: UserPublic = Depends(consume_quota),  # noqa: ARG001 — décrémente le quota, 429 si épuisé
) -> ChatResponse:
    """Invoque l'agent sur un thread persisté et renvoie réponse + reasoning trace.

    LangGraph récupère l'historique du thread depuis Mongo à chaque appel, n'a
    besoin que du nouveau message en entrée. Idem pour les checkpoints internes :
    chaque step du graph est snapshoté, permettant time-travel debugging.
    """
    agent = request.app.state.agent

    # Injection du FEN dans le message courant (contexte du tour uniquement,
    # pas dans l'historique persistant — la position d'un tour passé est périmée).
    content = _build_user_message(payload)

    new_msg = HumanMessage(content=content)
    config = {"configurable": {"thread_id": payload.session_id}}

    # Compte les messages déjà présents dans le thread pour slicer la trace de CE tour.
    try:
        before_state = await agent.aget_state(config)
        n_before = len(before_state.values.get("messages", []))
    except Exception:
        n_before = 0  # thread tout neuf

    try:
        final_state = await agent.ainvoke({"messages": [new_msg]}, config=config)
    except Exception as exc:
        logger.exception("Agent invocation failed for session=%s", payload.session_id)
        raise HTTPException(
            status_code=500, detail=f"Agent failure: {exc}"
        ) from exc

    new_messages = final_state["messages"][n_before:]
    return _build_response(payload.session_id, new_messages)


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    user: UserPublic = Depends(consume_quota),  # noqa: ARG001 — décrémente AVANT le stream
) -> StreamingResponse:
    """Variante streaming de /chat. Émet des events SSE au fil du raisonnement.

    Types d'events émis :
    - `token` {text} : un chunk de texte du LLM (la réponse finale s'écrit ainsi).
    - `tool_start` {id, name, args} : un tool va être appelé.
    - `tool_end` {id, result} : retour du tool (string brute).
    - `done` {session_id} : fin du stream, l'agent a terminé.
    - `error` {detail} : exception côté backend, le front doit afficher l'erreur.

    Les tokens proviennent UNIQUEMENT du dernier appel LLM (la réponse à
    l'utilisateur). Les appels intermédiaires (LLM → tool → LLM) sont
    matérialisés par les events `tool_start`/`tool_end` côté reasoning trace,
    pas en tant que tokens — sinon on streamerait le JSON des tool calls.
    """
    agent = request.app.state.agent

    content = _build_user_message(payload)

    new_msg = HumanMessage(content=content)
    config = {"configurable": {"thread_id": payload.session_id}}

    async def event_generator() -> AsyncIterator[bytes]:
        try:
            async for event in agent.astream_events(
                {"messages": [new_msg]}, config=config, version="v2"
            ):
                kind = event["event"]

                # Token du LLM. On filtre les chunks vides (LangGraph en émet
                # avant/après les tool calls). `content` peut être une str ou
                # une liste (multimodal) — on ignore le cas liste vu qu'on
                # n'utilise que du texte.
                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk is None:
                        continue
                    text = chunk.content if isinstance(chunk.content, str) else ""
                    if text:
                        yield _sse_event("token", {"text": text})

                # Début d'appel tool. event["run_id"] sert d'identifiant stable
                # pour matcher tool_end plus tard.
                elif kind == "on_tool_start":
                    yield _sse_event(
                        "tool_start",
                        {
                            "id": event["run_id"],
                            "name": event["name"],
                            "args": event["data"].get("input", {}),
                        },
                    )

                # Fin d'appel tool. Output peut être un objet complexe (dict,
                # liste) — on serialize en str pour rester compatible avec le
                # ToolCallTrace.result existant (typé str côté Pydantic).
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    result_str = output if isinstance(output, str) else str(output)
                    yield _sse_event(
                        "tool_end",
                        {"id": event["run_id"], "result": result_str},
                    )

            yield _sse_event("done", {"session_id": payload.session_id})

        except Exception as exc:
            logger.exception(
                "Streaming agent invocation failed for session=%s", payload.session_id
            )
            yield _sse_event("error", {"detail": f"Agent failure: {exc}"})

    # `text/event-stream` est le content-type obligatoire pour SSE — le navigateur
    # n'attend pas le close de la connexion pour livrer les chunks au JS.
    # X-Accel-Buffering désactive le buffering nginx (sinon les events s'accumulent
    # côté proxy et arrivent en bloc à la fin → effet anti-streaming).
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _build_response(session_id: str, new_messages: list) -> ChatResponse:
    """Extrait reply + tool trace des nouveaux messages produits par l'agent."""
    traces: list[ToolCallTrace] = []
    pending_by_id: dict[str, ToolCallTrace] = {}
    reply = ""

    for msg in new_messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    trace = ToolCallTrace(
                        name=tc["name"], args=tc["args"], result=""
                    )
                    traces.append(trace)
                    pending_by_id[tc["id"]] = trace
            else:
                reply = msg.content if isinstance(msg.content, str) else str(msg.content)
        elif isinstance(msg, ToolMessage):
            trace = pending_by_id.get(msg.tool_call_id)
            if trace is not None:
                trace.result = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )

    if not reply:
        reply = "(L'agent n'a produit aucune réponse finale.)"

    return ChatResponse(session_id=session_id, reply=reply, tool_calls=traces)
