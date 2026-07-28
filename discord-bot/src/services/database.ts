/**
 * SQLite database — single source of truth for AI Brief.
 *
 * Design principle: store EVERYTHING so that any pipeline run can be
 * replayed from any stage without making a single LLM API call.
 *
 * Tables:
 *   sessions         — one row per pipeline run (who, what URL, status)
 *   stage_runs       — EVERY execution of every stage (supports re-runs)
 *                      stores both input_json AND output_json
 *   agent_messages   — individual agent messages within a stage
 *                      (each analyst, reviewer comment, score, confidence)
 *   debate_turns     — individual rounds within analyst debates
 *                      (preparer submissions, reviewer feedback, revisions)
 *   comments         — user comments per stage (with weight, action)
 *   likes            — user likes/boosts on agent outputs
 *   images           — references to ALL images (path, type, association)
 *   posts            — LinkedIn/social post data (text, title, URL)
 *   embeddings       — dedup vectors for topic similarity
 *   url_cache        — quick lookup for previously processed URLs
 *   stage_preferences — user trust/validate settings per stage
 *
 * Image files stay on disk (PNG/JPG). Everything else is in SQLite.
 * Images table has full path + metadata so we never lose track.
 */

import Database from "better-sqlite3";
import { resolve } from "path";
import { mkdirSync } from "fs";

const DB_PATH = resolve(__dirname, "../../data/aibrief.db");
console.log(`[DB] Path: ${DB_PATH}`);
mkdirSync(resolve(__dirname, "../../data"), { recursive: true });

// timeout helps when OneDrive / a zombie bot briefly holds the file
const db = new Database(DB_PATH, { timeout: 15000 });
db.pragma("busy_timeout = 15000");
db.pragma("journal_mode = WAL");
db.pragma("foreign_keys = ON");
console.log("[DB] Opened OK");

// ═══════════════════════════════════════════════════════════════
//  SCHEMA
// ═══════════════════════════════════════════════════════════════

// Migrate: drop old schema if it lacks new columns
try {
  const cols = db.prepare("PRAGMA table_info(sessions)").all() as {name: string}[];
  if (cols.length > 0 && !cols.some(c => c.name === "headline")) {
    console.log("[DB] Old schema detected, dropping all tables to recreate...");
    dropAllTables();
  }
  // Check for new tables added in this version
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all() as {name: string}[];
  const tableNames = tables.map(t => t.name);
  if (tableNames.includes("sessions") && !tableNames.includes("debate_turns")) {
    console.log("[DB] Missing new tables (debate_turns, url_cache), dropping all to recreate...");
    dropAllTables();
  }
} catch { /* fresh DB */ }

function dropAllTables() {
  db.exec("DROP TABLE IF EXISTS likes");
  db.exec("DROP TABLE IF EXISTS comments");
  db.exec("DROP TABLE IF EXISTS debate_turns");
  db.exec("DROP TABLE IF EXISTS agent_messages");
  db.exec("DROP TABLE IF EXISTS stage_runs");
  db.exec("DROP TABLE IF EXISTS images");
  db.exec("DROP TABLE IF EXISTS posts");
  db.exec("DROP TABLE IF EXISTS embeddings");
  db.exec("DROP TABLE IF EXISTS stage_preferences");
  db.exec("DROP TABLE IF EXISTS url_cache");
  db.exec("DROP TABLE IF EXISTS sessions");
}

db.exec(`CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, api_session_id TEXT, thread_id TEXT UNIQUE, channel_id TEXT,
  user_id TEXT NOT NULL, source_url TEXT, source_text TEXT, pages INTEGER DEFAULT 4,
  current_stage TEXT DEFAULT '', status TEXT DEFAULT 'created',
  headline TEXT, publisher TEXT, article_text TEXT,
  emotion TEXT, style_id TEXT, palette_id TEXT, font_id TEXT, design_name TEXT, imagen_style TEXT,
  pdf_path TEXT, brief_title TEXT,
  combined_score REAL, pre_visual_score REAL, post_visual_score REAL, discussion_score REAL,
  total_debates INTEGER DEFAULT 0, total_rounds INTEGER DEFAULT 0, duration_seconds REAL,
  cached_run_id TEXT, sub_step INTEGER DEFAULT NULL, sub_action INTEGER DEFAULT NULL,
  created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
)`);

// Add columns for existing databases
try { db.exec(`ALTER TABLE sessions ADD COLUMN sub_step INTEGER DEFAULT NULL`); } catch {}
try { db.exec(`ALTER TABLE sessions ADD COLUMN sub_action INTEGER DEFAULT NULL`); } catch {}

db.exec(`CREATE TABLE IF NOT EXISTS stage_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id),
  stage_id TEXT NOT NULL, run_number INTEGER DEFAULT 1, status TEXT DEFAULT 'pending',
  input_json TEXT, output_json TEXT, duration_sec REAL DEFAULT 0,
  message_id TEXT, error TEXT, user_comments TEXT,
  started_at TEXT DEFAULT (datetime('now')), completed_at TEXT
)`);

db.exec(`CREATE TABLE IF NOT EXISTS agent_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id),
  stage_run_id INTEGER REFERENCES stage_runs(id), stage_id TEXT NOT NULL,
  agent_name TEXT NOT NULL, agent_codename TEXT, role TEXT,
  message_type TEXT DEFAULT 'output', content_json TEXT, content_summary TEXT,
  score REAL, confidence REAL, approved INTEGER,
  needs_user_input INTEGER DEFAULT 0, question_for_user TEXT,
  round_number INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now'))
)`);

// ── Agent Actions: the complete execution ledger ──
// Every individual agent action is a row. Inputs map to other agents' outputs.
// This is the single source of truth for replay — no API calls needed if this is populated.
db.exec(`CREATE TABLE IF NOT EXISTS agent_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  agent_name TEXT NOT NULL,
  agent_codename TEXT,
  action TEXT NOT NULL,
  action_label TEXT,
  stage TEXT NOT NULL,
  perspective TEXT,
  round_number INTEGER DEFAULT 1,
  execution_order INTEGER NOT NULL,
  prompt_fixed TEXT,
  prompt_variables_json TEXT,
  input_data_json TEXT,
  output_json TEXT,
  output_summary TEXT,
  score REAL,
  confidence REAL,
  approved INTEGER,
  user_flag TEXT DEFAULT 'trust',
  user_approved INTEGER DEFAULT NULL,
  user_feedback TEXT,
  duration_sec REAL DEFAULT 0,
  status TEXT DEFAULT 'pending',
  message_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_agent_actions_session ON agent_actions(session_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_agent_actions_lookup ON agent_actions(session_id, stage, perspective, action)`);

// Index for cross-session cache lookup (find results by source_url across sessions)
db.exec(`CREATE INDEX IF NOT EXISTS idx_sessions_source_url ON sessions(source_url)`);

db.exec(`CREATE TABLE IF NOT EXISTS debate_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  stage_run_id INTEGER REFERENCES stage_runs(id),
  debate_label TEXT NOT NULL,
  preparer_name TEXT NOT NULL,
  reviewer_name TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  preparer_submission_json TEXT,
  reviewer_feedback_json TEXT,
  preparer_revision_json TEXT,
  demands_json TEXT,
  verdict TEXT,
  score REAL,
  approved INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
)`);

db.exec(`CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id),
  stage_id TEXT NOT NULL, user_id TEXT NOT NULL, user_name TEXT,
  content TEXT NOT NULL, weight REAL DEFAULT 5.0, action TEXT DEFAULT 'comment',
  reply_to_agent TEXT, reply_to_message_id INTEGER REFERENCES agent_messages(id),
  created_at TEXT DEFAULT (datetime('now'))
)`);

db.exec(`CREATE TABLE IF NOT EXISTS likes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id),
  stage_id TEXT NOT NULL, user_id TEXT NOT NULL,
  agent_message_id INTEGER REFERENCES agent_messages(id),
  target_agent TEXT, target_text TEXT, boost_weight REAL DEFAULT 2.0,
  created_at TEXT DEFAULT (datetime('now'))
)`);

db.exec(`CREATE TABLE IF NOT EXISTS images (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT REFERENCES sessions(id),
  image_type TEXT NOT NULL, image_key TEXT NOT NULL, file_path TEXT NOT NULL,
  file_name TEXT, size_kb REAL,
  run_id TEXT, style_id TEXT, page_index INTEGER, agent_codename TEXT,
  prompt_used TEXT, model_used TEXT, cached INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')), UNIQUE(image_type, image_key)
)`);

db.exec(`CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id),
  platform TEXT DEFAULT 'linkedin', post_text TEXT, document_title TEXT,
  post_id TEXT, post_url TEXT, status TEXT DEFAULT 'draft', pdf_path TEXT,
  created_at TEXT DEFAULT (datetime('now'))
)`);

db.exec(`CREATE TABLE IF NOT EXISTS embeddings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT REFERENCES sessions(id),
  topic TEXT NOT NULL, summary TEXT, vector_json TEXT,
  model TEXT DEFAULT 'text-embedding-3-small', created_at TEXT DEFAULT (datetime('now'))
)`);

db.exec(`CREATE TABLE IF NOT EXISTS url_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  session_id TEXT REFERENCES sessions(id),
  cached_run_id TEXT,
  headline TEXT,
  publisher TEXT,
  stage_results_json TEXT,
  pdf_path TEXT,
  combined_score REAL,
  created_at TEXT DEFAULT (datetime('now')),
  last_used_at TEXT DEFAULT (datetime('now'))
)`);

db.exec(`CREATE TABLE IF NOT EXISTS stage_preferences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  stage_id TEXT NOT NULL,
  preference TEXT DEFAULT 'validate',
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(session_id, stage_id)
)`);

// Indexes
db.exec(`CREATE INDEX IF NOT EXISTS idx_sessions_thread ON sessions(thread_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_stage_runs_session ON stage_runs(session_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_stage_runs_stage ON stage_runs(session_id, stage_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_agent_messages_session ON agent_messages(session_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_agent_messages_stage ON agent_messages(session_id, stage_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_debate_turns_session ON debate_turns(session_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_debate_turns_label ON debate_turns(session_id, debate_label)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_comments_session ON comments(session_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_comments_stage ON comments(session_id, stage_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_images_session ON images(session_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_images_type ON images(image_type)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_posts_session ON posts(session_id)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_embeddings_topic ON embeddings(topic)`);
db.exec(`CREATE INDEX IF NOT EXISTS idx_url_cache_url ON url_cache(url)`);

// ═══════════════════════════════════════════════════════════════
//  PREPARED STATEMENTS
// ═══════════════════════════════════════════════════════════════

const stmts = {
  // -- Sessions --
  insertSession: db.prepare(`
    INSERT INTO sessions (id, api_session_id, thread_id, channel_id, user_id, source_url, source_text, pages, status)
    VALUES (@id, @api_session_id, @thread_id, @channel_id, @user_id, @source_url, @source_text, @pages, @status)
  `),

  updateSession: db.prepare(`
    UPDATE sessions SET
      current_stage = COALESCE(@current_stage, current_stage),
      status = COALESCE(@status, status),
      pdf_path = COALESCE(@pdf_path, pdf_path),
      api_session_id = COALESCE(@api_session_id, api_session_id),
      headline = COALESCE(@headline, headline),
      publisher = COALESCE(@publisher, publisher),
      article_text = COALESCE(@article_text, article_text),
      emotion = COALESCE(@emotion, emotion),
      style_id = COALESCE(@style_id, style_id),
      palette_id = COALESCE(@palette_id, palette_id),
      font_id = COALESCE(@font_id, font_id),
      design_name = COALESCE(@design_name, design_name),
      imagen_style = COALESCE(@imagen_style, imagen_style),
      brief_title = COALESCE(@brief_title, brief_title),
      combined_score = COALESCE(@combined_score, combined_score),
      pre_visual_score = COALESCE(@pre_visual_score, pre_visual_score),
      post_visual_score = COALESCE(@post_visual_score, post_visual_score),
      discussion_score = COALESCE(@discussion_score, discussion_score),
      total_debates = COALESCE(@total_debates, total_debates),
      total_rounds = COALESCE(@total_rounds, total_rounds),
      duration_seconds = COALESCE(@duration_seconds, duration_seconds),
      cached_run_id = COALESCE(@cached_run_id, cached_run_id),
      sub_step = CASE WHEN @sub_step_set = 1 THEN @sub_step ELSE sub_step END,
      sub_action = CASE WHEN @sub_action_set = 1 THEN @sub_action ELSE sub_action END,
      updated_at = datetime('now')
    WHERE id = @id
  `),

  getSessionByThread: db.prepare(`SELECT * FROM sessions WHERE thread_id = @thread_id`),
  listSessions: db.prepare(`SELECT * FROM sessions ORDER BY created_at DESC LIMIT 50`),

  // -- Stage Runs --
  insertStageRun: db.prepare(`
    INSERT INTO stage_runs (session_id, stage_id, run_number, status, input_json, output_json, duration_sec, message_id, error, user_comments, completed_at)
    VALUES (@session_id, @stage_id, @run_number, @status, @input_json, @output_json, @duration_sec, @message_id, @error, @user_comments, datetime('now'))
  `),

  getLatestStageRun: db.prepare(`
    SELECT * FROM stage_runs
    WHERE session_id = @session_id AND stage_id = @stage_id
    ORDER BY run_number DESC LIMIT 1
  `),

  getStageRunsBySession: db.prepare(`
    SELECT * FROM stage_runs WHERE session_id = @session_id ORDER BY id
  `),

  getStageRunCount: db.prepare(`
    SELECT COALESCE(MAX(run_number), 0) as max_run
    FROM stage_runs WHERE session_id = @session_id AND stage_id = @stage_id
  `),

  // -- Agent Messages --
  insertAgentMessage: db.prepare(`
    INSERT INTO agent_messages (session_id, stage_run_id, stage_id, agent_name, agent_codename, role, message_type, content_json, content_summary, score, confidence, approved, needs_user_input, question_for_user, round_number)
    VALUES (@session_id, @stage_run_id, @stage_id, @agent_name, @agent_codename, @role, @message_type, @content_json, @content_summary, @score, @confidence, @approved, @needs_user_input, @question_for_user, @round_number)
  `),

  // -- Debate Turns --
  insertDebateTurn: db.prepare(`
    INSERT INTO debate_turns (session_id, stage_run_id, debate_label, preparer_name, reviewer_name, round_number, preparer_submission_json, reviewer_feedback_json, preparer_revision_json, demands_json, verdict, score, approved)
    VALUES (@session_id, @stage_run_id, @debate_label, @preparer_name, @reviewer_name, @round_number, @preparer_submission_json, @reviewer_feedback_json, @preparer_revision_json, @demands_json, @verdict, @score, @approved)
  `),

  // -- Comments --
  insertComment: db.prepare(`
    INSERT INTO comments (session_id, stage_id, user_id, user_name, content, weight, action, reply_to_agent, reply_to_message_id)
    VALUES (@session_id, @stage_id, @user_id, @user_name, @content, @weight, @action, @reply_to_agent, @reply_to_message_id)
  `),

  getCommentsByStage: db.prepare(`
    SELECT * FROM comments WHERE session_id = @session_id AND stage_id = @stage_id ORDER BY created_at
  `),

  // -- URL Cache --
  upsertUrlCache: db.prepare(`
    INSERT OR REPLACE INTO url_cache (url, session_id, cached_run_id, headline, publisher, stage_results_json, pdf_path, combined_score, last_used_at)
    VALUES (@url, @session_id, @cached_run_id, @headline, @publisher, @stage_results_json, @pdf_path, @combined_score, datetime('now'))
  `),

  getUrlCache: db.prepare(`
    SELECT * FROM url_cache WHERE url = @url
  `),

  updateUrlCacheLastUsed: db.prepare(`
    UPDATE url_cache SET last_used_at = datetime('now') WHERE url = @url
  `),

  // -- Stage Preferences --
  upsertPreference: db.prepare(`
    INSERT OR REPLACE INTO stage_preferences (session_id, stage_id, preference)
    VALUES (@session_id, @stage_id, @preference)
  `),

  getPreference: db.prepare(`
    SELECT preference FROM stage_preferences
    WHERE session_id = @session_id AND stage_id = @stage_id
  `),

  getPreferencesBySession: db.prepare(`
    SELECT stage_id, preference FROM stage_preferences
    WHERE session_id = @session_id
  `),

  // -- Agent Actions (execution ledger) --
  insertAgentAction: db.prepare(`
    INSERT INTO agent_actions (
      session_id, agent_name, agent_codename, action, action_label,
      stage, perspective, round_number, execution_order,
      prompt_fixed, prompt_variables_json, input_data_json,
      output_json, output_summary, score, confidence, approved,
      user_flag, duration_sec, status, message_id
    ) VALUES (
      @session_id, @agent_name, @agent_codename, @action, @action_label,
      @stage, @perspective, @round_number, @execution_order,
      @prompt_fixed, @prompt_variables_json, @input_data_json,
      @output_json, @output_summary, @score, @confidence, @approved,
      @user_flag, @duration_sec, @status, @message_id
    )
  `),

  getAgentActions: db.prepare(`
    SELECT * FROM agent_actions
    WHERE session_id = @session_id
    ORDER BY execution_order
  `),

  getAgentActionsByStage: db.prepare(`
    SELECT * FROM agent_actions
    WHERE session_id = @session_id AND stage = @stage
    ORDER BY execution_order
  `),

  getAgentAction: db.prepare(`
    SELECT * FROM agent_actions
    WHERE session_id = @session_id AND stage = @stage
      AND (perspective = @perspective OR (@perspective IS NULL AND perspective IS NULL))
      AND action = @action AND round_number = @round_number
    ORDER BY id DESC LIMIT 1
  `),

  // Cross-session cache: find a completed action from ANY session that processed the same URL
  getCrossSessionCachedAction: db.prepare(`
    SELECT aa.* FROM agent_actions aa
    INNER JOIN sessions s ON aa.session_id = s.id
    WHERE s.source_url = @source_url
      AND aa.stage = @stage
      AND (aa.perspective = @perspective OR (@perspective IS NULL AND aa.perspective IS NULL))
      AND aa.action = @action
      AND aa.round_number = @round_number
      AND aa.status IN ('success', 'completed', 'auto_approved')
      AND aa.output_json IS NOT NULL
    ORDER BY aa.id DESC LIMIT 1
  `),

  // Get all completed actions from the most recent session with this URL
  getAllCachedActionsForUrl: db.prepare(`
    SELECT aa.* FROM agent_actions aa
    INNER JOIN sessions s ON aa.session_id = s.id
    WHERE s.source_url = @source_url
      AND aa.status IN ('success', 'completed', 'auto_approved')
      AND aa.output_json IS NOT NULL
      AND aa.session_id != @exclude_session_id
    ORDER BY aa.id DESC
  `),

  updateAgentAction: db.prepare(`
    UPDATE agent_actions SET
      user_approved = @user_approved,
      user_feedback = @user_feedback,
      status = @status,
      message_id = COALESCE(@message_id, message_id)
    WHERE id = @id
  `),

  setBulkPreferences: db.prepare(`
    INSERT OR REPLACE INTO stage_preferences (session_id, stage_id, preference)
    VALUES (@session_id, @stage_id, @preference)
  `),

  // -- Session Cleanup (per-user limit) --
  getSessionsByUser: db.prepare(`
    SELECT id, pdf_path, created_at FROM sessions
    WHERE user_id = @user_id
    ORDER BY created_at DESC
  `),

  deleteSessionById: db.prepare(`DELETE FROM sessions WHERE id = @id`),
  deleteStageRunsBySession: db.prepare(`DELETE FROM stage_runs WHERE session_id = @id`),
  deleteAgentMessagesBySession: db.prepare(`DELETE FROM agent_messages WHERE session_id = @id`),
  deleteDebateTurnsBySession: db.prepare(`DELETE FROM debate_turns WHERE session_id = @id`),
  deleteCommentsBySession: db.prepare(`DELETE FROM comments WHERE session_id = @id`),
  deleteLikesBySession: db.prepare(`DELETE FROM likes WHERE session_id = @id`),
  deletePreferencesBySession: db.prepare(`DELETE FROM stage_preferences WHERE session_id = @id`),
  deleteAgentActionsBySession: db.prepare(`DELETE FROM agent_actions WHERE session_id = @id`),
  deleteUrlCacheBySession: db.prepare(`DELETE FROM url_cache WHERE session_id = @id`),

  // -- Orphan PDF sweep --
  getAllTrackedPdfPaths: db.prepare(`
    SELECT pdf_path FROM sessions WHERE pdf_path IS NOT NULL AND pdf_path != 'delivered'
  `),
};

// ═══════════════════════════════════════════════════════════════
//  PUBLIC API
// ═══════════════════════════════════════════════════════════════

export interface DbSession {
  id: string;
  api_session_id: string;
  thread_id: string;
  channel_id: string;
  user_id: string;
  source_url: string;
  source_text: string;
  pages: number;
  current_stage: string;
  status: string;
  headline: string | null;
  publisher: string | null;
  article_text: string | null;
  emotion: string | null;
  style_id: string | null;
  palette_id: string | null;
  font_id: string | null;
  design_name: string | null;
  imagen_style: string | null;
  pdf_path: string | null;
  brief_title: string | null;
  combined_score: number | null;
  pre_visual_score: number | null;
  post_visual_score: number | null;
  discussion_score: number | null;
  total_debates: number;
  total_rounds: number;
  duration_seconds: number | null;
  cached_run_id: string | null;
  sub_step: number | null;
  sub_action: number | null;
  created_at: string;
  updated_at: string;
}

export interface DbStageRun {
  id: number;
  session_id: string;
  stage_id: string;
  run_number: number;
  status: string;
  input_json: string | null;
  output_json: string | null;
  duration_sec: number;
  message_id: string | null;
  error: string | null;
  user_comments: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface DbComment {
  id: number;
  session_id: string;
  stage_id: string;
  user_id: string;
  user_name: string | null;
  content: string;
  weight: number;
  action: string;
  reply_to_agent: string | null;
  reply_to_message_id: number | null;
  created_at: string;
}

export interface DbAgentAction {
  id: number;
  session_id: string;
  agent_name: string;
  agent_codename: string | null;
  action: string;
  action_label: string | null;
  stage: string;
  perspective: string | null;
  round_number: number;
  execution_order: number;
  prompt_fixed: string | null;
  prompt_variables_json: string | null;
  input_data_json: string | null;
  output_json: string | null;
  output_summary: string | null;
  score: number | null;
  confidence: number | null;
  approved: number | null;
  user_flag: string;
  user_approved: number | null;
  user_feedback: string | null;
  duration_sec: number;
  status: string;
  message_id: string | null;
  created_at: string;
}

export interface DbUrlCache {
  id: number;
  url: string;
  session_id: string | null;
  cached_run_id: string | null;
  headline: string | null;
  publisher: string | null;
  stage_results_json: string | null;
  pdf_path: string | null;
  combined_score: number | null;
  created_at: string;
  last_used_at: string;
}

export const dbOps = {
  // ── Sessions ──
  createSession(data: {
    id: string;
    api_session_id: string;
    thread_id: string;
    channel_id: string;
    user_id: string;
    source_url: string;
    source_text: string;
    pages: number;
  }): void {
    stmts.insertSession.run({ ...data, status: "created" });
  },

  updateSession(id: string, updates: Record<string, any>): void {
    const params: Record<string, any> = { id };
    const fields = [
      "current_stage", "status", "pdf_path", "api_session_id",
      "headline", "publisher", "article_text",
      "emotion", "style_id", "palette_id", "font_id", "design_name", "imagen_style",
      "brief_title", "combined_score", "pre_visual_score", "post_visual_score",
      "discussion_score", "total_debates", "total_rounds", "duration_seconds",
      "cached_run_id",
    ];
    for (const f of fields) {
      params[f] = updates[f] ?? null;
    }
    // sub_step/sub_action need special handling — COALESCE can't set to null
    params.sub_step_set = "sub_step" in updates ? 1 : 0;
    params.sub_step = "sub_step" in updates ? updates.sub_step : null;
    params.sub_action_set = "sub_action" in updates ? 1 : 0;
    params.sub_action = "sub_action" in updates ? updates.sub_action : null;
    stmts.updateSession.run(params);
  },

  getSessionByThread(threadId: string): DbSession | undefined {
    return stmts.getSessionByThread.get({ thread_id: threadId }) as DbSession | undefined;
  },

  listSessions(): DbSession[] {
    return stmts.listSessions.all() as DbSession[];
  },

  // ── Stage Runs ──
  saveStageRun(data: {
    session_id: string;
    stage_id: string;
    status: string;
    input_json?: string;
    output_json: string;
    duration_sec: number;
    message_id?: string;
    error?: string;
    user_comments?: string;
  }): number {
    const row = stmts.getStageRunCount.get({
      session_id: data.session_id,
      stage_id: data.stage_id,
    }) as { max_run: number };
    const runNumber = (row?.max_run || 0) + 1;

    const result = stmts.insertStageRun.run({
      session_id: data.session_id,
      stage_id: data.stage_id,
      run_number: runNumber,
      status: data.status,
      input_json: data.input_json ?? null,
      output_json: data.output_json,
      duration_sec: data.duration_sec,
      message_id: data.message_id ?? null,
      error: data.error ?? null,
      user_comments: data.user_comments ?? null,
    });
    return Number(result.lastInsertRowid);
  },

  getLatestStageRun(sessionId: string, stageId: string): DbStageRun | undefined {
    return stmts.getLatestStageRun.get({
      session_id: sessionId,
      stage_id: stageId,
    }) as DbStageRun | undefined;
  },

  getStageRunsBySession(sessionId: string): DbStageRun[] {
    return stmts.getStageRunsBySession.all({ session_id: sessionId }) as DbStageRun[];
  },

  // ── Agent Messages ──
  saveAgentMessage(data: {
    session_id: string;
    stage_run_id?: number;
    stage_id: string;
    agent_name: string;
    agent_codename?: string;
    role?: string;
    message_type?: string;
    content_json?: string;
    content_summary?: string;
    score?: number;
    confidence?: number;
    approved?: boolean;
    needs_user_input?: boolean;
    question_for_user?: string;
    round_number?: number;
  }): number {
    const result = stmts.insertAgentMessage.run({
      session_id: data.session_id,
      stage_run_id: data.stage_run_id ?? null,
      stage_id: data.stage_id,
      agent_name: data.agent_name,
      agent_codename: data.agent_codename ?? null,
      role: data.role ?? null,
      message_type: data.message_type ?? "output",
      content_json: data.content_json ?? null,
      content_summary: data.content_summary ?? null,
      score: data.score ?? null,
      confidence: data.confidence ?? null,
      approved: data.approved != null ? (data.approved ? 1 : 0) : null,
      needs_user_input: data.needs_user_input ? 1 : 0,
      question_for_user: data.question_for_user ?? null,
      round_number: data.round_number ?? 1,
    });
    return Number(result.lastInsertRowid);
  },

  // ── Debate Turns ──
  saveDebateTurn(data: {
    session_id: string;
    stage_run_id?: number;
    debate_label: string;
    preparer_name: string;
    reviewer_name: string;
    round_number: number;
    preparer_submission_json?: string;
    reviewer_feedback_json?: string;
    preparer_revision_json?: string;
    demands_json?: string;
    verdict?: string;
    score?: number;
    approved?: boolean;
  }): number {
    const result = stmts.insertDebateTurn.run({
      session_id: data.session_id,
      stage_run_id: data.stage_run_id ?? null,
      debate_label: data.debate_label,
      preparer_name: data.preparer_name,
      reviewer_name: data.reviewer_name,
      round_number: data.round_number,
      preparer_submission_json: data.preparer_submission_json ?? null,
      reviewer_feedback_json: data.reviewer_feedback_json ?? null,
      preparer_revision_json: data.preparer_revision_json ?? null,
      demands_json: data.demands_json ?? null,
      verdict: data.verdict ?? null,
      score: data.score ?? null,
      approved: data.approved ? 1 : 0,
    });
    return Number(result.lastInsertRowid);
  },

  // ── Comments ──
  addComment(data: {
    session_id: string;
    stage_id: string;
    user_id: string;
    user_name?: string;
    content: string;
    weight?: number;
    action?: string;
    reply_to_agent?: string;
    reply_to_message_id?: number;
  }): void {
    stmts.insertComment.run({
      session_id: data.session_id,
      stage_id: data.stage_id,
      user_id: data.user_id,
      user_name: data.user_name ?? null,
      content: data.content,
      weight: data.weight ?? 5.0,
      action: data.action ?? "comment",
      reply_to_agent: data.reply_to_agent ?? null,
      reply_to_message_id: data.reply_to_message_id ?? null,
    });
  },

  getComments(sessionId: string, stageId: string): DbComment[] {
    return stmts.getCommentsByStage.all({
      session_id: sessionId,
      stage_id: stageId,
    }) as DbComment[];
  },

  // ── URL Cache ──
  saveUrlCache(data: {
    url: string;
    session_id?: string;
    cached_run_id?: string;
    headline?: string;
    publisher?: string;
    stage_results_json?: string;
    pdf_path?: string;
    combined_score?: number;
  }): void {
    stmts.upsertUrlCache.run({
      url: data.url,
      session_id: data.session_id ?? null,
      cached_run_id: data.cached_run_id ?? null,
      headline: data.headline ?? null,
      publisher: data.publisher ?? null,
      stage_results_json: data.stage_results_json ?? null,
      pdf_path: data.pdf_path ?? null,
      combined_score: data.combined_score ?? null,
    });
  },

  getUrlCache(url: string): DbUrlCache | undefined {
    const row = stmts.getUrlCache.get({ url }) as DbUrlCache | undefined;
    if (row) {
      stmts.updateUrlCacheLastUsed.run({ url });
    }
    return row;
  },

  // ── Stage Preferences ──
  setPreference(sessionId: string, stageId: string, preference: "trust" | "validate"): void {
    stmts.upsertPreference.run({ session_id: sessionId, stage_id: stageId, preference });
  },

  getPreference(sessionId: string, stageId: string): "trust" | "validate" {
    const row = stmts.getPreference.get({ session_id: sessionId, stage_id: stageId }) as { preference: string } | undefined;
    return (row?.preference as "trust" | "validate") || "validate";
  },

  getPreferences(sessionId: string): Record<string, "trust" | "validate"> {
    const rows = stmts.getPreferencesBySession.all({ session_id: sessionId }) as { stage_id: string; preference: string }[];
    const map: Record<string, "trust" | "validate"> = {};
    for (const r of rows) {
      map[r.stage_id] = r.preference as "trust" | "validate";
    }
    return map;
  },

  setBulkPreferences(sessionId: string, prefs: Record<string, "trust" | "validate">): void {
    const tx = db.transaction(() => {
      for (const [stageId, pref] of Object.entries(prefs)) {
        stmts.setBulkPreferences.run({ session_id: sessionId, stage_id: stageId, preference: pref });
      }
    });
    tx();
  },

  // ── Agent Actions (execution ledger) ──
  saveAgentAction(data: {
    session_id: string;
    agent_name: string;
    agent_codename?: string;
    action: string;
    action_label?: string;
    stage: string;
    perspective?: string;
    round_number?: number;
    execution_order: number;
    prompt_fixed?: string;
    prompt_variables_json?: string;
    input_data_json?: string;
    output_json?: string;
    output_summary?: string;
    score?: number;
    confidence?: number;
    approved?: boolean;
    user_flag?: string;
    duration_sec?: number;
    status?: string;
    message_id?: string;
  }): number {
    const result = stmts.insertAgentAction.run({
      session_id: data.session_id,
      agent_name: data.agent_name,
      agent_codename: data.agent_codename ?? null,
      action: data.action,
      action_label: data.action_label ?? null,
      stage: data.stage,
      perspective: data.perspective ?? null,
      round_number: data.round_number ?? 1,
      execution_order: data.execution_order,
      prompt_fixed: data.prompt_fixed ?? null,
      prompt_variables_json: data.prompt_variables_json ?? null,
      input_data_json: data.input_data_json ?? null,
      output_json: data.output_json ?? null,
      output_summary: data.output_summary ?? null,
      score: data.score ?? null,
      confidence: data.confidence ?? null,
      approved: data.approved != null ? (data.approved ? 1 : 0) : null,
      user_flag: data.user_flag ?? "trust",
      duration_sec: data.duration_sec ?? 0,
      status: data.status ?? "success",
      message_id: data.message_id ?? null,
    });
    return Number(result.lastInsertRowid);
  },

  getAgentActions(sessionId: string): DbAgentAction[] {
    return stmts.getAgentActions.all({ session_id: sessionId }) as DbAgentAction[];
  },

  getAgentActionsByStage(sessionId: string, stage: string): DbAgentAction[] {
    return stmts.getAgentActionsByStage.all({ session_id: sessionId, stage }) as DbAgentAction[];
  },

  getAgentAction(sessionId: string, stage: string, perspective: string | null, action: string, round: number = 1): DbAgentAction | undefined {
    return stmts.getAgentAction.get({
      session_id: sessionId, stage, perspective, action, round_number: round,
    }) as DbAgentAction | undefined;
  },

  /**
   * Cross-session cache: find a completed action result from ANY previous session that processed the same URL.
   * Returns undefined if no cached result exists.
   */
  getCrossSessionCachedAction(sourceUrl: string, stage: string, perspective: string | null, action: string, round: number = 1): DbAgentAction | undefined {
    if (!sourceUrl) return undefined;
    return stmts.getCrossSessionCachedAction.get({
      source_url: sourceUrl, stage, perspective, action, round_number: round,
    }) as DbAgentAction | undefined;
  },

  /**
   * Get ALL completed actions from previous sessions that share the same source URL.
   * Used to pre-warm the current session's cache on startup.
   */
  getAllCachedActionsForUrl(sourceUrl: string, excludeSessionId: string): DbAgentAction[] {
    if (!sourceUrl) return [];
    return stmts.getAllCachedActionsForUrl.all({
      source_url: sourceUrl, exclude_session_id: excludeSessionId,
    }) as DbAgentAction[];
  },

  updateAgentAction(id: number, updates: {
    user_approved?: number;
    user_feedback?: string;
    status?: string;
    message_id?: string;
  }): void {
    stmts.updateAgentAction.run({
      id,
      user_approved: updates.user_approved ?? null,
      user_feedback: updates.user_feedback ?? null,
      status: updates.status ?? null,
      message_id: updates.message_id ?? null,
    });
  },

  // ── Session Cleanup — enforce per-user limit ──
  /**
   * Keep only the most recent N sessions per user.
   * Deletes old sessions from ALL related tables and removes PDF files from disk.
   * Returns the list of deleted session IDs and PDF paths.
   */
  cleanupUserSessions(userId: string, maxSessions: number = 5): { deletedIds: string[]; deletedPdfs: string[] } {
    const allSessions = stmts.getSessionsByUser.all({ user_id: userId }) as { id: string; pdf_path: string | null; created_at: string }[];

    if (allSessions.length <= maxSessions) {
      return { deletedIds: [], deletedPdfs: [] };
    }

    // Sessions to delete = everything after the first N (sorted by created_at DESC)
    const toDelete = allSessions.slice(maxSessions);
    const deletedIds: string[] = [];
    const deletedPdfs: string[] = [];

    const tx = db.transaction(() => {
      for (const session of toDelete) {
        const sid = session.id;

        // Delete deepest children first to respect FK constraints:
        // agent_messages & debate_turns reference stage_runs
        stmts.deleteAgentActionsBySession.run({ id: sid });
        stmts.deleteLikesBySession.run({ id: sid });
        stmts.deleteCommentsBySession.run({ id: sid });
        stmts.deleteDebateTurnsBySession.run({ id: sid });
        stmts.deleteAgentMessagesBySession.run({ id: sid });
        // Now safe to delete stage_runs (no more child refs)
        stmts.deleteStageRunsBySession.run({ id: sid });
        stmts.deletePreferencesBySession.run({ id: sid });
        stmts.deleteUrlCacheBySession.run({ id: sid });

        // Delete the session itself
        stmts.deleteSessionById.run({ id: sid });

        deletedIds.push(sid);
        if (session.pdf_path) {
          deletedPdfs.push(session.pdf_path);
        }
      }
    });
    tx();

    return { deletedIds, deletedPdfs };
  },

  /**
   * Get all pdf_path values currently tracked by any session.
   * Used by the orphan PDF sweep to determine which files on disk are still valid.
   */
  getAllTrackedPdfPaths(): string[] {
    const rows = stmts.getAllTrackedPdfPaths.all() as { pdf_path: string }[];
    return rows.map((r) => r.pdf_path);
  },
};

export default dbOps;
