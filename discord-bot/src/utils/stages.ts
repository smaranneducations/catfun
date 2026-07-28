/**
 * Pipeline stages — maps to the Python orchestrator phases.
 *
 * UPDATED: Removed World Pulse, Content Strategy, Topic Discovery.
 * User provides the URL directly, so discovery is unnecessary.
 * Added Content Extraction as the first step.
 */

export interface StageDefinition {
  id: string;
  name: string;
  emoji: string;
  agent: string;
  color: number;
  description: string;
  phase_number: string;
}

export const STAGES: StageDefinition[] = [
  {
    id: "content_extraction",
    name: "Content Extraction",
    emoji: "",
    agent: "System",
    color: 0x3498db,
    description: "Fetching article, extracting text, identifying topic and key facts",
    phase_number: "1",
  },
  {
    id: "design_dna",
    name: "Design DNA",
    emoji: "",
    agent: "Vesper",
    color: 0xe67e22,
    description: "Detecting emotion from article and selecting visual style, palette, fonts",
    phase_number: "2",
  },
  {
    id: "analyst_pairs",
    name: "Analyst Debates",
    emoji: "",
    agent: "Clio, Aurelia, Sage, Nova",
    color: 0xe74c3c,
    description: "4 analysts debate with their reviewers — historical, economic, social, future",
    phase_number: "3",
  },
  {
    id: "round_table",
    name: "Round Table",
    emoji: "",
    agent: "All Analysts",
    color: 0xc0392b,
    description: "Analysts challenge each other across disciplines",
    phase_number: "4",
  },
  {
    id: "editorial",
    name: "Editorial Oversight",
    emoji: "",
    agent: "Paramount",
    color: 0xf39c12,
    description: "Editor-in-chief reviews all perspectives for quality and coherence",
    phase_number: "5",
  },
  {
    id: "content_synthesis",
    name: "Content Synthesis",
    emoji: "",
    agent: "Quill + Sterling",
    color: 0x1abc9c,
    description: "Writer creates poster pages, copy reviewer ensures luxury quality",
    phase_number: "6",
  },
  {
    id: "neutrality_check",
    name: "Neutrality Check",
    emoji: "",
    agent: "Justice",
    color: 0x2c3e50,
    description: "Ethical guardrail enforcement — checking for bias and tone balance",
    phase_number: "7",
  },
  {
    id: "discussion_potential",
    name: "Discussion Potential",
    emoji: "",
    agent: "Spark",
    color: 0xff6b35,
    description: "Scoring engagement potential and generating discussion hooks",
    phase_number: "8",
  },
  {
    id: "pre_validation",
    name: "Quality Gate",
    emoji: "",
    agent: "Sentinel-A",
    color: 0x7f8c8d,
    description: "Content and structure quality validation (17 rules)",
    phase_number: "9",
  },
  {
    id: "visuals",
    name: "Visual Generation",
    emoji: "",
    agent: "Prism",
    color: 0xe91e63,
    description: "Generating images — backgrounds, foregrounds, cover art",
    phase_number: "10",
  },
  {
    id: "pdf_generation",
    name: "PDF Generation",
    emoji: "",
    agent: "System",
    color: 0x9b59b6,
    description: "Building the luxury poster PDF — your PDF will be delivered here",
    phase_number: "11",
  },
  {
    id: "post_validation",
    name: "Layout Review (Info)",
    emoji: "",
    agent: "Sentinel-B",
    color: 0x27ae60,
    description: "Layout and visual quality score — informational only, does not block",
    phase_number: "12",
  },
  {
    id: "send_email",
    name: "Email Draft",
    emoji: "",
    agent: "Herald",
    color: 0x5865f2,
    description: "Crafts a Unicode-formatted LinkedIn post (headline, body, hashtags) for publish after completion",
    phase_number: "13",
  },
];

export function getStage(id: string): StageDefinition | undefined {
  return STAGES.find((s) => s.id === id);
}

export function getStageIndex(id: string): number {
  return STAGES.findIndex((s) => s.id === id);
}

export function getNextStage(currentId: string): StageDefinition | undefined {
  const idx = getStageIndex(currentId);
  if (idx === -1 || idx >= STAGES.length - 1) return undefined;
  return STAGES[idx + 1];
}
