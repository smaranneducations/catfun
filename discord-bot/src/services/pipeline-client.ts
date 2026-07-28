/**
 * Pipeline Client — calls the Python FastAPI service per stage.
 *
 * The Python API runs at http://localhost:8900 and exposes:
 *   POST /session                        → create a new pipeline session
 *   POST /session/{id}/run/{stage_id}    → run a specific stage
 *   POST /session/{id}/analyst/{persp}   → run a single analyst perspective
 *   GET  /health                         → health check
 *
 * All calls have explicit timeouts.
 */

import { CONFIG } from "../config";

const API = CONFIG.PYTHON_API_URL;

// Timeout constants (milliseconds)
const TIMEOUT_HEALTH = 3_000;
const TIMEOUT_SESSION = 30_000;
const TIMEOUT_STAGE = 300_000;   // 5 minutes — some stages (visuals, PDF) are slow

export interface SessionInfo {
  session_id: string;
  status: string;
  current_stage: string;
  stages_completed: string[];
  cached_run_id?: string;
}

export interface StageResult {
  stage_id: string;
  status: "success" | "error";
  result: Record<string, any>;
  duration_seconds: number;
  error?: string;
}

export interface LinkedInPublishResult {
  status: string;
  url?: string;
  post_id?: string;
  document_title?: string;
  error?: string;
}

/**
 * Create a new pipeline session.
 */
export async function createSession(
  sourceUrl: string,
  sourceText: string,
  pages: number
): Promise<SessionInfo> {
  const resp = await fetch(`${API}/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_url: sourceUrl,
      source_text: sourceText,
      pages,
    }),
    signal: AbortSignal.timeout(TIMEOUT_SESSION),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Failed to create session: ${resp.status} ${errText}`);
  }

  return (await resp.json()) as SessionInfo;
}

/**
 * Run a specific stage in the pipeline.
 *
 * @param sessionId - The session ID
 * @param stageId - The stage to run
 * @param userComments - User comments to inject (weighted 5x)
 */
export async function runStage(
  sessionId: string,
  stageId: string,
  userComments: string[] = []
): Promise<StageResult> {
  const resp = await fetch(`${API}/session/${sessionId}/run/${stageId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_comments: userComments,
    }),
    signal: AbortSignal.timeout(TIMEOUT_STAGE),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Stage ${stageId} failed: ${resp.status} ${errText}`);
  }

  return (await resp.json()) as StageResult;
}

/**
 * Run a single analyst perspective debate (historical/economic/social/future).
 */
export async function runAnalystPerspective(
  sessionId: string,
  perspective: string,
  userComments: string[] = []
): Promise<StageResult> {
  const resp = await fetch(`${API}/session/${sessionId}/analyst/${perspective}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_comments: userComments,
    }),
    signal: AbortSignal.timeout(TIMEOUT_STAGE),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Analyst ${perspective} failed: ${resp.status} ${errText}`);
  }

  return (await resp.json()) as StageResult;
}

// ═══════════════════════════════════════════════════════════════
//  GRANULAR ACTION ENDPOINTS
//  Each runs ONE agent action and returns immediately.
// ═══════════════════════════════════════════════════════════════

export interface ActionPayload {
  user_comments?: string[];
  previous_work?: Record<string, any> | null;
  review_feedback?: Record<string, any> | null;
}

/**
 * Run a single analyst action: prepare, review, revise, or finalize.
 */
export async function runAnalystAction(
  sessionId: string,
  perspective: string,
  action: "prepare" | "review" | "revise" | "finalize",
  payload: ActionPayload = {}
): Promise<StageResult> {
  const resp = await fetch(
    `${API}/session/${sessionId}/action/analyst/${perspective}/${action}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(TIMEOUT_STAGE),
    }
  );
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Analyst ${perspective}/${action} failed: ${resp.status} ${errText}`);
  }
  return (await resp.json()) as StageResult;
}

/**
 * Run a single round table action: challenge or respond.
 */
export async function runRoundTableAction(
  sessionId: string,
  challengerKey: string,
  action: "challenge" | "respond",
  payload: ActionPayload = {}
): Promise<StageResult> {
  const resp = await fetch(
    `${API}/session/${sessionId}/action/round_table/${challengerKey}/${action}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(TIMEOUT_STAGE),
    }
  );
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`RoundTable ${challengerKey}/${action} failed: ${resp.status} ${errText}`);
  }
  return (await resp.json()) as StageResult;
}

/**
 * Run a single synthesis action: synthesise, review, or revise.
 */
export async function runSynthesisAction(
  sessionId: string,
  action: "synthesise" | "review" | "revise",
  payload: ActionPayload = {}
): Promise<StageResult> {
  const resp = await fetch(
    `${API}/session/${sessionId}/action/synthesis/${action}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(TIMEOUT_STAGE),
    }
  );
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Synthesis/${action} failed: ${resp.status} ${errText}`);
  }
  return (await resp.json()) as StageResult;
}

/**
 * Craft the LinkedIn-style post text for the send_email stage.
 */
export async function runSendEmailAction(
  sessionId: string,
  payload: ActionPayload = {}
): Promise<StageResult> {
  const resp = await fetch(
    `${API}/session/${sessionId}/action/send_email/craft`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(TIMEOUT_STAGE),
    }
  );
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Send email craft failed: ${resp.status} ${errText}`);
  }
  return (await resp.json()) as StageResult;
}

/**
 * Publish a completed session to LinkedIn.
 */
export async function publishLinkedIn(
  sessionId: string,
  payload: { post_text?: string; document_title?: string; pdf_path?: string; story?: Record<string, any> } = {}
): Promise<LinkedInPublishResult> {
  const resp = await fetch(
    `${API}/session/${sessionId}/publish/linkedin`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(TIMEOUT_STAGE),
    }
  );
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`LinkedIn publish failed: ${resp.status} ${errText}`);
  }
  return (await resp.json()) as LinkedInPublishResult;
}

/**
 * Health check — is the Python API running?
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const resp = await fetch(`${API}/health`, { signal: AbortSignal.timeout(TIMEOUT_HEALTH) });
    return resp.ok;
  } catch {
    return false;
  }
}
