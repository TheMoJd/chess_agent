// Mirror exact des Pydantic backend (cf. backend/app/models/user.py).

export interface UserPublic {
  id: string;
  email: string;
  messages_used: number;
  quota: number;
  created_at: string; // ISO datetime
}

export interface Token {
  access_token: string;
  token_type: string;
  user: UserPublic;
}

export interface AuthCredentials {
  email: string;
  password: string;
}
