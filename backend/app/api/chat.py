"""Route POST /api/v1/chat — invocation de l'agent LangGraph avec checkpoints Mongo."""
import logging

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.models.chat import ChatRequest, ChatResponse, ToolCallTrace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """Invoque l'agent sur un thread persisté et renvoie réponse + reasoning trace.

    LangGraph récupère l'historique du thread depuis Mongo à chaque appel, n'a
    besoin que du nouveau message en entrée. Idem pour les checkpoints internes :
    chaque step du graph est snapshoté, permettant time-travel debugging.
    """
    agent = request.app.state.agent

    # Injection du FEN dans le message courant (contexte du tour uniquement,
    # pas dans l'historique persistant — la position d'un tour passé est périmée).
    content = payload.message
    if payload.fen:
        content = f"[Current board FEN: {payload.fen}]\n\n{payload.message}"

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
