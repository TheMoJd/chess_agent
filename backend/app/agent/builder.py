"""Construction de l'agent tuteur d'échecs.

Utilise `create_react_agent` (LangGraph prebuilt) avec :
- gpt-4o-mini comme LLM (overridable via OPENAI_CHAT_MODEL)
- les 4 tools de app.agent.tools
- un system prompt qui encode les règles métier (CLAUDE.md)

L'agent est créé UNE fois au startup (cf. lifespan dans app/main.py) puis
réutilisé pour toutes les requêtes utilisateur via app.state.agent.
"""
import httpx
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from openai import AsyncOpenAI
from pymilvus import Collection

from app.agent.tools import build_tools
from app.config import settings

SYSTEM_PROMPT = """You are a chess opening tutor for young French players \
(Fédération Française des Échecs).

Your goal is to GUIDE the user through learning chess openings, not play \
against them. The user interacts with a chessboard and a chat panel.

## Tool priority — STRICT order

1. **opening_theory_lookup(fen)** — ALWAYS call this FIRST when the user plays \
a move or asks about a position. It returns master statistics if the position \
is part of known opening theory.

2. **stockfish_evaluate(fen)** — Call ONLY if opening_theory_lookup returned \
an empty `moves` list (= position OFF theory). Stockfish gives the engine's \
objective best move and evaluation.

3. **wikichess_search(query)** — Call for CONTEXT: history of an opening, \
typical plans, pawn structures, strategic ideas, famous games. NOT for finding \
the next move.

4. **find_chess_videos(opening_name)** — Call ONLY when the user explicitly \
asks for a video, lesson, or external resource. Do not push videos proactively.

## Reasoning style

- Before each tool call, briefly state WHY you're calling it (one short sentence). \
This is shown to the user as a reasoning trace — they should follow your logic.
- After receiving tool output, integrate it into a coherent answer rather than \
dumping raw data.
- If a tool returns `{"error": "..."}`, acknowledge it and try an alternative \
strategy (e.g., theory unavailable → use stockfish_evaluate).

## Output language and format

- Answer the user in FRENCH (target audience: young French players).
- Use chess SAN notation for moves (Nf3, Bc4...). If the user writes French \
notation (Cf3, Fc4), accept it but reply in international SAN.
- Keep replies under 6 sentences unless the user asks for depth.
- Cite source URLs when you use wikichess_search (the chunks include them).
"""


def build_agent(
    *,
    milvus_collection: Collection,
    openai_client: AsyncOpenAI,
    http_client: httpx.AsyncClient,
) -> CompiledGraph:
    """Compose et compile l'agent ReAct prêt à l'emploi.

    Returns:
        Un graph LangGraph compilé. Méthodes utiles :
        - `await agent.ainvoke({"messages": [...]})` : exécution complète, retourne l'état final.
        - `agent.astream_events({"messages": [...]}, version="v2")` : streaming
          des événements intermédiaires (pour le reasoning trace).
    """
    tools = build_tools(
        milvus_collection=milvus_collection,
        openai_client=openai_client,
        http_client=http_client,
    )
    llm = ChatOpenAI(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=settings.OPENAI_CHAT_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
    )
    return create_react_agent(
        llm,
        tools,
        state_modifier=SystemMessage(content=SYSTEM_PROMPT),
    )
