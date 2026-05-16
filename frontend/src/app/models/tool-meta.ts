// Mapping centralisé des tools agent → présentation visuelle.
// IMPORTANT : les classes Tailwind doivent être écrites EN LITTÉRAL ici (pas
// construites par concat), sinon le purge Tailwind les supprime en prod.

import {
  AlertTriangle,
  BookOpen,
  Cpu,
  LucideIconData,
  Search,
  Video,
} from 'lucide-angular';

export interface ToolMeta {
  label: string;
  icon: LucideIconData;
  bgClass: string;
  textClass: string;
  description: string;
}

export const TOOL_META: Record<string, ToolMeta> = {
  opening_theory_lookup: {
    label: 'Théorie des ouvertures',
    icon: BookOpen,
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-800',
    description:
      'Recherche les coups joués par les maîtres dans une position connue.',
  },
  stockfish_evaluate: {
    label: 'Évaluation Stockfish',
    icon: Cpu,
    bgClass: 'bg-purple-100',
    textClass: 'text-purple-800',
    description: "Demande au moteur d'échecs le meilleur coup objectif.",
  },
  wikichess_search: {
    label: 'Connaissance théorique',
    icon: Search,
    bgClass: 'bg-emerald-100',
    textClass: 'text-emerald-800',
    description:
      'Cherche du contexte (plans, structures, histoire) dans la base Wikichess.',
  },
  find_chess_videos: {
    label: 'Vidéos pédagogiques',
    icon: Video,
    bgClass: 'bg-rose-100',
    textClass: 'text-rose-800',
    description: "Cherche des vidéos YouTube pertinentes sur l'ouverture.",
  },
};

export const FALLBACK_TOOL_META: ToolMeta = {
  label: 'Outil inconnu',
  icon: AlertTriangle,
  bgClass: 'bg-amber-100',
  textClass: 'text-amber-800',
  description: '',
};

export function getToolMeta(name: string): ToolMeta {
  return TOOL_META[name] ?? FALLBACK_TOOL_META;
}
