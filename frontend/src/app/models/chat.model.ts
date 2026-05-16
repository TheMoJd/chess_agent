// Mirror exact des Pydantic backend (cf. backend/app/models/chat.py).

export interface ChatRequest {
  session_id: string;
  message: string;
  fen: string | null;
}

export interface ToolCallTrace {
  name: string;
  args: Record<string, unknown>;
  result: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  tool_calls: ToolCallTrace[];
}
