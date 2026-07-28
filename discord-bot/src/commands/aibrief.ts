/**
 * /aibrief command — starts a new multi-agent AI Brief pipeline.
 *
 * Flow:
 *   1. /aibrief → Setup form (input method + execution mode)
 *   2. User picks: URL / Paste Text / File  +  Autonomous / Human Control
 *   3. Clicks Continue → modal for URL/text, or file-upload prompt
 *   4. If Human Control → pre-flight catalog (trust/validate per stage)
 *   5. If Autonomous → trust all, skip catalog, auto-run
 *   6. Each stage runs → trusted = auto-advance, validate = show buttons
 *   7. After pdf_generation: PDF is IMMEDIATELY uploaded to thread
 *   8. Post-validation is informational only
 *
 * Agents NEVER block the flow. They rate + explain. User decides.
 */

import {
  ChatInputCommandInteraction,
  SlashCommandBuilder,
  ChannelType,
  TextChannel,
  AttachmentBuilder,
  EmbedBuilder,
  Message,
} from "discord.js";
import { createSession, runStage, healthCheck } from "../services/pipeline-client";
import { readFileSync, existsSync, unlinkSync, readdirSync } from "fs";
import { resolve } from "path";
import {
  buildRunningEmbed,
  buildStageEmbed,
  buildApprovalButtons,
  buildPdfDeliveryEmbed,
  buildCompleteEmbed,
  buildCatalogEmbed,
  buildTrustSelectMenu,
  buildCatalogButtons,
  buildPreferenceSummaryEmbed,
  buildSetupEmbed,
  buildInputMethodSelect,
  buildFileUploadEmbed,
  buildExecModeSelect,
  buildDebateTurnEmbed,
  buildCompletionActions,
} from "../utils/embeds";
import { STAGES, getNextStage, getStage } from "../utils/stages";

import { getClient } from "../utils/bot-client";
import dbOps from "../services/database";
import { randomUUID } from "crypto";
import {
  executeAgentAction,
  getAgentActionCached,
  populateAgentActionsFromStageResult,
} from "../services/agent-wrapper";
import { PERSPECTIVE_AGENTS, PERSPECTIVES } from "../utils/agent-catalog";
import {
  runAnalystAction,
  runRoundTableAction,
  runSynthesisAction,
  runSendEmailAction,
} from "../services/pipeline-client";
import { isGoogleDriveConfigured, uploadPdfToGoogleDrive } from "../services/google-drive";

// Derived lookup for labels (used in Discord messages)
const PERSPECTIVE_LABELS: Record<string, string> = {
  historical: "Historical",
  economic: "Economic",
  social: "Social",
  future: "Future",
};

// ═══════════════════════════════════════════════════════════════
//  SETUP STATE — tracks user selections before session creation
// ═══════════════════════════════════════════════════════════════

export interface SetupState {
  userId: string;
  channelId: string;
  threadId?: string;
  inputMethod?: "url" | "text" | "file";
  execMode?: "autonomous" | "human";
  sourceUrl?: string;
  sourceText?: string;
  pages?: number;
}

// Key: `${userId}_${channelId}` — one active setup per user per channel
const setupStates = new Map<string, SetupState & { createdAt: number }>();

// Cleanup stale setup states older than 10 minutes (prevents memory leak)
const SETUP_TTL_MS = 10 * 60 * 1000;
setInterval(() => {
  const now = Date.now();
  for (const [key, state] of setupStates) {
    if (now - state.createdAt > SETUP_TTL_MS) {
      setupStates.delete(key);
    }
  }
}, 60_000); // Check every minute

function setupKey(userId: string, channelId: string): string {
  return `${userId}_${channelId}`;
}

export function getSetupState(userId: string, channelId: string): SetupState | undefined {
  return setupStates.get(setupKey(userId, channelId));
}

export function updateSetupState(userId: string, channelId: string, updates: Partial<SetupState>): SetupState {
  const key = setupKey(userId, channelId);
  const current = setupStates.get(key) || { userId, channelId, createdAt: Date.now() };
  const updated = { ...current, ...updates };
  setupStates.set(key, updated);
  return updated;
}

export function deleteSetupState(userId: string, channelId: string): void {
  setupStates.delete(setupKey(userId, channelId));
}

// ═══════════════════════════════════════════════════════════════
//  SLASH COMMAND
// ═══════════════════════════════════════════════════════════════

export const data = new SlashCommandBuilder()
  .setName("aibrief")
  .setDescription("Start a new AI Brief — multi-agent content pipeline");

export async function execute(interaction: ChatInputCommandInteraction) {
  // Defer immediately — Discord gives only 3 seconds to respond
  await interaction.deferReply();

  // Check if Python API is up
  const apiUp = await healthCheck();
  if (!apiUp) {
    await interaction.editReply({
      content:
        "The AI Brief engine is not running. Start it first:\n" +
        "```\ncd catfun && python -m aibrief.api\n```",
    });
    return;
  }

  // Create a dedicated thread immediately — all interaction happens inside it
  let parentChannel: TextChannel;
  const rawChannel = await interaction.client.channels.fetch(interaction.channelId);

  if (rawChannel && rawChannel.isThread() && rawChannel.parentId) {
    // Command was used inside an existing thread — resolve the parent text channel
    const parent = await interaction.client.channels.fetch(rawChannel.parentId);
    if (!parent || !(parent instanceof TextChannel)) {
      await interaction.editReply({ content: "Please use /aibrief in a text channel, not inside a thread." });
      return;
    }
    parentChannel = parent;
  } else if (rawChannel && rawChannel instanceof TextChannel) {
    parentChannel = rawChannel;
  } else {
    await interaction.editReply({ content: "Please use /aibrief in a text channel." });
    return;
  }

  const thread = await parentChannel.threads.create({
    name: `AI Brief — ${interaction.user.displayName} — ${new Date().toLocaleDateString()}`,
    autoArchiveDuration: 1440,
    type: ChannelType.PublicThread,
  });

  // Point the user to the thread from the main channel — prominent embed
  const sessionEmbed = new EmbedBuilder()
    .setTitle("AI Brief — Session Started")
    .setDescription(`Your dedicated workspace is ready.\nHead over to ${thread} to begin.`)
    .setColor(0x5865f2);

  await interaction.editReply({ embeds: [sessionEmbed] });

  // Initialize setup state with the thread ID
  updateSetupState(interaction.user.id, thread.id, {
    userId: interaction.user.id,
    channelId: interaction.channelId,
    threadId: thread.id,
  });

  // Post setup inside the thread
  const setupEmbed = buildSetupEmbed("input");
  const inputSelect = buildInputMethodSelect();

  await thread.send({
    embeds: [setupEmbed],
    components: [inputSelect],
  });
}

// ═══════════════════════════════════════════════════════════════
//  SETUP COMPLETION — creates session + thread after form input
// ═══════════════════════════════════════════════════════════════

/**
 * Called after URL/text/file content is received.
 * Creates the API session, SQLite session, thread, then proceeds
 * to catalog (human) or auto-run (autonomous).
 *
 * CACHE: If the URL was processed in a previous run, skips the Python API
 * entirely and uses stored data — zero external API calls.
 */
export async function handleSetupComplete(
  userId: string,
  channelId: string,
  sourceUrl: string,
  sourceText: string,
  pages: number
) {
  const state = getSetupState(userId, channelId);
  const execMode = state?.execMode || "human";

  // Clean up setup state
  deleteSetupState(userId, channelId);

  const botClient = getClient();
  // channelId IS the thread (thread was created in execute())
  const thread = await botClient.channels.fetch(channelId);
  if (!thread || !thread.isTextBased()) return;

  try {
    // ── Check URL cache BEFORE calling Python API ──
    let urlCacheData: Record<string, any> | null = null;
    if (sourceUrl) {
      const cache = dbOps.getUrlCache(sourceUrl);
      if (cache && cache.stage_results_json) {
        try {
          urlCacheData = JSON.parse(cache.stage_results_json);
          console.log(`[CACHE] Found cached results for URL — ${Object.keys(urlCacheData!).length} stages cached. ZERO API calls needed.`);
        } catch { /* ignore parse error */ }
      }
    }

    // Generate local session ID
    const sessionId = randomUUID().slice(0, 8);

    let apiSessionId = "cached_replay";

    if (urlCacheData) {
      // ── CACHED: Skip Python API session entirely ──
      console.log(`[CACHE] Skipping Python API session — using cached data`);
    } else {
      // ── FRESH: Create Python API session ──
      const apiSession = await createSession(sourceUrl, sourceText, pages);
      apiSessionId = apiSession.session_id;
    }

    // Save to SQLite — thread_id = channelId (we're already inside the thread)
    dbOps.createSession({
      id: sessionId,
      api_session_id: apiSessionId,
      thread_id: channelId,
      channel_id: state?.channelId || channelId,
      user_id: userId,
      source_url: sourceUrl || sourceText,
      source_text: sourceText,
      pages,
    });

    // Enforce per-user session limit — clean up old sessions + PDFs immediately
    cleanupOldSessions(userId);

    if (urlCacheData) {
      dbOps.updateSession(sessionId, { cached_run_id: "local_replay" });
      // Pre-populate agent_actions ledger from cached URL data
      // This means the wrapper can replay from agent_actions directly
      for (const [stageKey, stageResult] of Object.entries(urlCacheData)) {
        try {
          populateAgentActionsFromStageResult(sessionId, stageKey, stageResult as Record<string, any>, "trust");
        } catch (e) {
          console.warn(`[CACHE] Could not populate agent_actions for ${stageKey}:`, e);
        }
      }
      console.log(`[CACHE] Pre-populated agent_actions ledger from URL cache`);
    }

    if (execMode === "autonomous") {
      // ── AUTONOMOUS: trust all stages, skip catalog, start immediately ──
      const prefs: Record<string, "trust" | "validate"> = {};
      for (const s of STAGES) {
        prefs[s.id] = "trust";
      }
      dbOps.setBulkPreferences(sessionId, prefs);

      const summaryEmbed = buildPreferenceSummaryEmbed(prefs);
      await (thread as any).send({
        content: "**Fully Autonomous mode** — all stages trusted. Pipeline starting...",
        embeds: [summaryEmbed],
      });

      // Start pipeline
      dbOps.updateSession(sessionId, { current_stage: STAGES[0].id, status: "running", sub_step: null, sub_action: null });
      await runNextStage(channelId);
    } else {
      // ── HUMAN CONTROL: show catalog for trust/validate configuration ──
      const displaySource = sourceUrl || "(pasted text)";
      const catalogEmbed = buildCatalogEmbed(displaySource, pages);
      const trustSelect = buildTrustSelectMenu();
      const catalogButtons = buildCatalogButtons();

      // Message A: Catalog + dropdown (select menu only)
      await (thread as any).send({
        embeds: [catalogEmbed],
        components: [trustSelect],
      });

      // Message B: Buttons only (Trust All / Validate All / Start Pipeline)
      // Separate message = no interference from dropdown interactions
      await (thread as any).send({
        components: [catalogButtons],
      });

      dbOps.updateSession(sessionId, { status: "catalog_review" });
    }
  } catch (err: any) {
    console.error("Error in handleSetupComplete:", err);
    await (thread as any).send(`Failed to start AI Brief: ${err.message}`);
  }
}

/**
 * Wait for a file upload from the user, read it, then ask for execution mode.
 */
export async function waitForFileUpload(userId: string, channelId: string, pages: number) {
  const botClient = getClient();
  const channel = await botClient.channels.fetch(channelId);
  if (!channel || !channel.isTextBased()) return;

  // Send the file upload prompt
  const fileEmbed = buildFileUploadEmbed();
  await (channel as any).send({ embeds: [fileEmbed] });

  // Create a message collector waiting for a file from this user
  const filter = (m: Message) =>
    m.author.id === userId && m.attachments.size > 0;

  try {
    const collected = await (channel as any).awaitMessages({
      filter,
      max: 1,
      time: 120_000, // 2 minutes
      errors: ["time"],
    });

    const msg = collected.first() as Message;
    const attachment = msg.attachments.first();
    if (!attachment) {
      await (channel as any).send("No file found. Please run `/aibrief` again.");
      deleteSetupState(userId, channelId);
      return;
    }

    // Download file content
    const resp = await fetch(attachment.url);
    const text = await resp.text();

    if (!text || text.length < 10) {
      await (channel as any).send("File appears empty or unreadable. Please try again with a text file.");
      deleteSetupState(userId, channelId);
      return;
    }

    // Save content to setup state
    updateSetupState(userId, channelId, {
      sourceText: text.slice(0, 10000),
      pages,
    });

    // Ask execution mode
    const contentEmbed = buildSetupEmbed("content_received", {
      contentSummary: `${attachment.name} (${text.length} chars)`,
    });
    const modeSelect = buildExecModeSelect();

    await (channel as any).send({
      embeds: [contentEmbed],
      components: [modeSelect],
    });
  } catch {
    await (channel as any).send("File upload timed out (2 minutes). Please run `/aibrief` again.");
    deleteSetupState(userId, channelId);
  }
}

/**
 * Start the pipeline after user has reviewed the catalog and clicked Start.
 */
export async function startPipeline(threadId: string) {
  const session = dbOps.getSessionByThread(threadId);
  if (!session) return;

  dbOps.updateSession(session.id, { current_stage: STAGES[0].id, status: "running", sub_step: null, sub_action: null });
  await runNextStage(threadId);
}

// Prevent concurrent stage runs on the same thread
const runningThreads = new Set<string>();

// In-memory store for pending re-run feedback.
// When user clicks Re-run and submits feedback, it's stored here keyed by threadId.
// The wrapper checks this FIRST — if feedback exists, cache is skipped and API is called fresh.
const pendingRerunFeedback = new Map<string, string[]>();

/**
 * Look up cached stage result for a URL. Returns null if not cached.
 * Checks both url_cache table and previous session stage_runs.
 */
function getCachedStageResult(sourceUrl: string, stageId: string): Record<string, any> | null {
  if (!sourceUrl) return null;

  // Method 1: Check the url_cache table (aggregated results from completed pipelines)
  const cache = dbOps.getUrlCache(sourceUrl);
  if (cache && cache.stage_results_json) {
    try {
      const allResults = JSON.parse(cache.stage_results_json);
      if (allResults[stageId]) {
        return allResults[stageId];
      }
    } catch { /* ignore */ }
  }

  // Method 2: Check previous sessions with the same URL
  const sessions = dbOps.listSessions();
  for (const s of sessions) {
    if (s.source_url === sourceUrl && (s.status === "complete" || s.status === "error")) {
      const stageRun = dbOps.getLatestStageRun(s.id, stageId);
      if (stageRun && stageRun.status === "success" && stageRun.output_json) {
        try {
          return JSON.parse(stageRun.output_json);
        } catch { /* ignore */ }
      }
    }
  }

  return null;
}

// ═══════════════════════════════════════════════════════════════
//  ROUND TABLE agent mapping (matches Python ROUND_TABLE_PAIRS)
// ═══════════════════════════════════════════════════════════════
const ROUND_TABLE_AGENTS = [
  { key: "economist", name: "Economist", code: "Aurelia", target: "Historian" },
  { key: "historian", name: "Historian", code: "Clio", target: "Futurist" },
  { key: "futurist",  name: "Futurist",  code: "Nova",    target: "Sociologist" },
  { key: "sociologist", name: "Sociologist", code: "Sage", target: "Economist" },
];

/**
 * Run the next stage in the pipeline for a given thread.
 *
 * For TRUST stages: runs the whole stage via bulk API, auto-advances.
 * For VALIDATE stages: runs ONE action at a time via granular API,
 * shows Approve/Re-run buttons, and waits.
 *
 * Multi-action stages (analyst_pairs, round_table, content_synthesis)
 * use sub_step + sub_action to track position within the action sequence.
 */
export async function runNextStage(threadId: string) {
  // Guard against concurrent runs on the same thread
  if (runningThreads.has(threadId)) {
    console.log(`[GUARD] Stage already running in thread ${threadId} — skipping duplicate`);
    return;
  }
  runningThreads.add(threadId);

  const session = dbOps.getSessionByThread(threadId);
  if (!session) { runningThreads.delete(threadId); return; }

  const stageId = session.current_stage;
  const stageDef = STAGES.find((s) => s.id === stageId);
  if (!stageDef) {
    console.error(`Unknown stage: ${stageId}`);
    runningThreads.delete(threadId);
    return;
  }

  const botClient = getClient();
  const thread = await botClient.channels.fetch(threadId);
  if (!thread || !thread.isTextBased()) { runningThreads.delete(threadId); return; }

  try {
    const pref = dbOps.getPreference(session.id, stageId);

    // ══════════════════════════════════════════════════════════════
    //  TRUST MODE: run entire stage via bulk API, auto-advance
    // ══════════════════════════════════════════════════════════════
    if (pref === "trust") {
      await runStageTrustMode(session, stageId, stageDef, thread as any, threadId);
      return;
    }

    // ══════════════════════════════════════════════════════════════
    //  VALIDATE MODE: run ONE action at a time, each with approval
    // ══════════════════════════════════════════════════════════════
    await runStageValidateMode(session, stageId, stageDef, thread as any, threadId);

  } catch (err: any) {
    console.error(`Error in stage ${stageId}:`, err);
    const errEmbed = buildRunningEmbed(stageDef)
      .setDescription(`Error: ${err.message}`)
      .setColor(0xe74c3c);
    await (thread as any).send({ embeds: [errEmbed] });
    dbOps.updateSession(session.id, { status: "error" });
  } finally {
    runningThreads.delete(threadId);
  }
}

// ──────────────────────────────────────────────────────────────
//  TRUST MODE — run full stage via bulk API, auto-advance
// ──────────────────────────────────────────────────────────────
async function runStageTrustMode(
  session: any, stageId: string, stageDef: any, thread: any, threadId: string
) {
  dbOps.updateSession(session.id, { status: "running" });
  const runningEmbed = buildRunningEmbed(stageDef);
  const runningMsg = await thread.send({ embeds: [runningEmbed] });

  const dbComments = dbOps.getComments(session.id, stageId);
  const commentTexts = dbComments.map((c: any) => c.content);

  // Check cache
  let result: { stage_id: string; status: string; result: Record<string, any>; duration_seconds: number; error?: string };
  const cached = getCachedStageResult(session.source_url, stageId);

  if (cached) {
    console.log(`[CACHE] Using cached result for stage: ${stageId} (0 API calls)`);
    result = { stage_id: stageId, status: "success", result: cached, duration_seconds: 0 };
  } else if (stageId === "send_email") {
    // send_email uses its own granular endpoint, not the bulk runStage
    console.log(`[${session.api_session_id}] Running stage: send_email (trust mode)`);
    result = await runSendEmailAction(session.api_session_id, {
      user_comments: commentTexts,
    });
  } else {
    console.log(`[${session.api_session_id}] Running stage: ${stageId} (trust mode)`);
    result = await runStage(session.api_session_id, stageId, commentTexts);
  }

  if (result.status === "error") {
    await runningMsg.edit({ content: `Stage failed: ${result.error}` });
    dbOps.updateSession(session.id, { status: "error" });
    return;
  }

  // Save to DB
  const stageRunId = dbOps.saveStageRun({
    session_id: session.id, stage_id: stageId, status: "success",
    output_json: JSON.stringify(result.result),
    duration_sec: result.duration_seconds, message_id: runningMsg.id,
    user_comments: commentTexts.length > 0 ? JSON.stringify(commentTexts) : undefined,
  });
  storeAgentData(session.id, stageId, stageRunId, result.result);
  enrichSessionFromStage(session.id, stageId, result.result);
  populateAgentActionsFromStageResult(session.id, stageId, result.result, "trust");

  // Special: deliver PDF immediately
  if (stageId === "pdf_generation" && result.result.pdf_ready) {
    await deliverPdf(threadId, session.api_session_id, result.result.pdf_path);
  }

  // Show result
  const stageEmbed = buildStageEmbed(stageDef, result.result, commentTexts);
  stageEmbed.addFields({ name: "Auto-Approved", value: "Trust Agent — auto-advancing.", inline: false });
  await runningMsg.edit({ embeds: [stageEmbed], components: [] });

  // Post debate embeds for trusted analyst_pairs
  if (stageId === "analyst_pairs" && result.result.full_debates?.length > 0) {
    await postDebateTurns(thread, result.result.full_debates);
  }

  console.log(`[${session.api_session_id}] Stage ${stageId} auto-approved (${result.duration_seconds.toFixed(1)}s)`);

  // Advance
  const next = getNextStage(stageId);
  if (next) {
    dbOps.updateSession(session.id, { current_stage: next.id, sub_step: null, sub_action: null });
    runningThreads.delete(threadId);
    await runNextStage(threadId);
  } else {
    await completePipeline(session, threadId, thread);
  }
}

// ──────────────────────────────────────────────────────────────
//  VALIDATE MODE — one action at a time with approval gates
// ──────────────────────────────────────────────────────────────
async function runStageValidateMode(
  session: any, stageId: string, stageDef: any, thread: any, threadId: string
) {
  dbOps.updateSession(session.id, { status: "running" });

  // ── Consume any pending re-run feedback for this thread ──
  const rerunFeedback = pendingRerunFeedback.get(threadId);
  if (rerunFeedback) {
    pendingRerunFeedback.delete(threadId);
    console.log(`[RERUN] Consumed feedback for thread ${threadId}: ${rerunFeedback.length} comment(s)`);
  }

  // ── Multi-action stages: route to specific handlers ──
  if (stageId === "analyst_pairs") {
    await runAnalystValidateAction(session, thread, threadId, rerunFeedback);
    return;
  }
  if (stageId === "round_table") {
    await runRoundTableValidateAction(session, thread, threadId, rerunFeedback);
    return;
  }
  if (stageId === "content_synthesis") {
    await runSynthesisValidateAction(session, thread, threadId, rerunFeedback);
    return;
  }

  // ── Single-action stages: one executeAgentAction call ──
  const actionDef = getSingleActionDef(stageId);
  const dbComments = dbOps.getComments(session.id, stageId);
  const commentTexts = dbComments.map((c: any) => c.content);
  // Merge re-run feedback with existing comments for the API call
  const allComments = rerunFeedback ? [...commentTexts, ...rerunFeedback] : commentTexts;

  // ── send_email stage: uses its own granular API endpoint ──
  const apiFn = stageId === "send_email"
    ? async () => {
        console.log(`[${session.api_session_id}] Running stage: send_email (validate)`);
        const r = await runSendEmailAction(session.api_session_id, {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Craft post failed");
        return r.result;
      }
    : async () => {
        console.log(`[${session.api_session_id}] Running stage: ${stageId} (validate)`);
        const r = await runStage(session.api_session_id, stageId, allComments);
        if (r.status === "error") throw new Error(r.error || "Stage failed");
        return r.result;
      };

  // ── send_email embed: show the full Unicode-formatted post text ──
  const buildEmbedFn = stageId === "send_email"
    ? (result: any) => {
        const postText = result.post_text || "";
        const docTitle = result.document_title || "";
        // Discord embed description max is 4096 chars
        const truncated = postText.length > 3800
          ? postText.slice(0, 3800) + "\n\n... (truncated for preview)"
          : postText;
        return new EmbedBuilder()
          .setTitle(`Herald — ${docTitle || "LinkedIn draft"}`)
          .setDescription(truncated || "No post text generated")
          .setColor(0x5865f2)
          .setFooter({ text: "Phase 13 — LinkedIn draft | Approve to continue" });
      }
    : (result: any) => buildStageEmbed(stageDef, result, commentTexts);

  const wrapperResult = await executeAgentAction({
    sessionId: session.id,
    threadChannel: thread,
    stageId,
    agentName: actionDef.agentName,
    agentCodename: actionDef.agentCodename,
    action: actionDef.action,
    actionLabel: `${actionDef.agentCodename} — ${stageDef.name}`,
    executionOrder: getNextOrder(session.id),
    userFlag: "validate",
    sourceUrl: session.source_url,
    promptFixed: actionDef.promptFixed,
    userComments: rerunFeedback,
    apiFn,
    buildEmbed: buildEmbedFn,
    extractMeta: (result: any) => ({
      score: result.overall_score ?? result.total_score ?? result.engagement_score,
      approved: result.approved,
      summary: result.headline || result.verdict || result.brief_title || result.document_title || "",
    }),
  });

  // Save to stage_runs for legacy compatibility
  if (wrapperResult.output) {
    const stageRunId = dbOps.saveStageRun({
      session_id: session.id, stage_id: stageId, status: "success",
      output_json: JSON.stringify(wrapperResult.output),
      duration_sec: 0, user_comments: commentTexts.length > 0 ? JSON.stringify(commentTexts) : undefined,
    });
    storeAgentData(session.id, stageId, stageRunId, wrapperResult.output);
    enrichSessionFromStage(session.id, stageId, wrapperResult.output);

    if (stageId === "pdf_generation" && wrapperResult.output.pdf_ready) {
      await deliverPdf(threadId, session.api_session_id, wrapperResult.output.pdf_path);
    }
  }

  if (!wrapperResult.continue) {
    // Waiting for user approval
    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    console.log(`[${session.api_session_id}] ${stageId} — awaiting approval`);
  }
  // If continue=true (shouldn't happen for validate), advance would be handled elsewhere
}

// ──────────────────────────────────────────────────────────────
//  ANALYST PAIRS — per-action validate mode
//  sub_step = perspective index (0-3)
//  sub_action = 0:prepare, 1:review, 2:revise (repeats for rounds)
// ──────────────────────────────────────────────────────────────
async function runAnalystValidateAction(session: any, thread: any, threadId: string, rerunFeedback?: string[]) {
  const subStep = session.sub_step ?? 0;
  const subAction = session.sub_action ?? 0;
  const perspective = PERSPECTIVES[subStep];
  const pAgents = PERSPECTIVE_AGENTS[perspective];
  const pLabel = PERSPECTIVE_LABELS[perspective] || perspective;

  dbOps.updateSession(session.id, { sub_step: subStep, sub_action: subAction });

  // Action 0: PREPARE
  if (subAction === 0) {
    const result = await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "analyst_pairs",
      agentName: pAgents.preparer,
      agentCodename: pAgents.prep_code,
      action: "prepare",
      actionLabel: `${pAgents.prep_code} — Initial ${pLabel} Analysis`,
      perspective,
      roundNumber: 1,
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: `Analyze this article from a ${perspective} perspective. Provide thesis, key arguments, evidence, and a confidence score.`,
      userComments: rerunFeedback,
      apiFn: async () => {
        const r = await runAnalystAction(session.api_session_id, perspective, "prepare", {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Prepare failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const embed = new EmbedBuilder()
          .setTitle(`${pAgents.prep_code} — ${result.perspective_title || result.title || pLabel}`)
          .setDescription(
            `**Confidence:** ${result.confidence || "?"}/10\n` +
            (result.pull_quote ? `> *${result.pull_quote}*\n\n` : "") +
            (result.key_arguments?.map((a: string) => `- ${a}`).join("\n") ||
             result.historical_parallels?.map((a: any) => `- ${typeof a === "string" ? a : a.parallel || a.event || JSON.stringify(a)}`).join("\n") ||
             "")
          )
          .setColor(0xe74c3c)
          .setFooter({ text: `Phase 3.${subStep + 1} — ${pLabel} | Prepare` });
        return embed;
      },
      extractMeta: (result: any) => ({
        confidence: result.confidence,
        summary: result.perspective_title || result.title || "",
      }),
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    console.log(`[${session.api_session_id}] Analyst ${perspective} PREPARE — awaiting approval`);
    return;
  }

  // Action 1: REVIEW (round N)
  if (subAction % 2 === 1) {
    const roundNum = Math.ceil(subAction / 2);

    const result = await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "analyst_pairs",
      agentName: pAgents.reviewer,
      agentCodename: pAgents.rev_code,
      action: "review",
      actionLabel: `${pAgents.rev_code} — Review Round ${roundNum} (${pLabel})`,
      perspective,
      roundNumber: roundNum,
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: `Critically review the ${perspective} analysis. Score it, identify weaknesses, issue demands for improvement, and decide whether to approve or require revision.`,
      userComments: rerunFeedback,
      apiFn: async () => {
        const r = await runAnalystAction(session.api_session_id, perspective, "review", {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Review failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const review = result.review || result;
        const score = result.score ?? review.overall_score ?? 0;
        const approved = result.approved ?? review.approved ?? false;
        const demands = result.demands || review.demands || [];
        const strengths = result.strengths || review.strengths || [];
        const verdict = result.verdict || review.verdict || "";

        const embed = new EmbedBuilder()
          .setTitle(`${pAgents.rev_code} — Review Round ${roundNum}`)
          .setDescription(
            `**Score:** ${score}/10 ${approved ? "✅ Approved" : "❌ Needs revision"}\n\n` +
            (strengths.length > 0 ? `**Strengths:**\n${strengths.map((s: string) => `✅ ${s}`).join("\n")}\n\n` : "") +
            (demands.length > 0 ? `**Demands:**\n${demands.map((d: string) => `- ${d}`).join("\n")}\n\n` : "") +
            (verdict ? `**Verdict:** ${verdict}` : "")
          )
          .setColor(approved ? 0x27ae60 : 0xe74c3c)
          .setFooter({ text: `Phase 3.${subStep + 1} — ${pLabel} | Review R${roundNum}` });
        return embed;
      },
      extractMeta: (result: any) => ({
        score: result.score ?? result.review?.overall_score,
        approved: result.approved ?? result.review?.approved,
        summary: result.verdict || result.review?.verdict || "",
      }),
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    console.log(`[${session.api_session_id}] Analyst ${perspective} REVIEW R${roundNum} — awaiting approval`);
    return;
  }

  // Action 2, 4: REVISE (round N)
  if (subAction % 2 === 0 && subAction >= 2) {
    const roundNum = subAction / 2;

    const result = await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "analyst_pairs",
      agentName: pAgents.preparer,
      agentCodename: pAgents.prep_code,
      action: "revise",
      actionLabel: `${pAgents.prep_code} — Revision Round ${roundNum} (${pLabel})`,
      perspective,
      roundNumber: roundNum,
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: `Address the reviewer's demands and improve your ${perspective} analysis. Incorporate feedback while maintaining your core thesis.`,
      apiFn: async () => {
        const r = await runAnalystAction(session.api_session_id, perspective, "revise");
        if (r.status === "error") throw new Error(r.error || "Revise failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const embed = new EmbedBuilder()
          .setTitle(`${pAgents.prep_code} — Revision Round ${roundNum}`)
          .setDescription(
            `**${pAgents.prep_code}** has revised the ${pLabel.toLowerCase()} analysis based on reviewer feedback.\n\n` +
            `**Title:** ${result.perspective_title || result.title || "Revised analysis"}\n` +
            `**Confidence:** ${result.confidence || "?"}/10`
          )
          .setColor(0xf39c12)
          .setFooter({ text: `Phase 3.${subStep + 1} — ${pLabel} | Revision R${roundNum}` });
        return embed;
      },
      extractMeta: (result: any) => ({
        confidence: result.confidence,
        summary: result.perspective_title || result.title || "",
      }),
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    console.log(`[${session.api_session_id}] Analyst ${perspective} REVISE R${roundNum} — awaiting approval`);
    return;
  }
}

// ──────────────────────────────────────────────────────────────
//  ROUND TABLE — per-action validate mode
//  sub_step = agent index (0-3), sub_action = 0:challenge, 1:respond
// ──────────────────────────────────────────────────────────────
async function runRoundTableValidateAction(session: any, thread: any, threadId: string, rerunFeedback?: string[]) {
  const subStep = session.sub_step ?? 0;
  const subAction = session.sub_action ?? 0;
  const agent = ROUND_TABLE_AGENTS[subStep];

  dbOps.updateSession(session.id, { sub_step: subStep, sub_action: subAction });

  if (subAction === 0) {
    // CHALLENGE
    await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "round_table",
      agentName: agent.name,
      agentCodename: agent.code,
      action: "challenge",
      actionLabel: `${agent.code} challenges ${agent.target}`,
      perspective: agent.key,
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: `Challenge ${agent.target}'s analysis from your perspective.`,
      userComments: rerunFeedback,
      apiFn: async () => {
        const r = await runRoundTableAction(session.api_session_id, agent.key, "challenge", {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Challenge failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const challenge = result.challenge || result;
        const summary = typeof challenge === "object"
          ? (challenge.rebuttal || challenge.challenge || challenge.main_point || challenge.summary || JSON.stringify(challenge).slice(0, 400))
          : String(challenge).slice(0, 400);
        return new EmbedBuilder()
          .setTitle(`${agent.code} challenges ${agent.target}`)
          .setDescription(summary)
          .setColor(0xc0392b)
          .setFooter({ text: `Phase 4 — Round Table | Challenge ${subStep + 1}/4` });
      },
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    return;
  }

  if (subAction === 1) {
    // RESPOND
    await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "round_table",
      agentName: agent.name,
      agentCodename: agent.code,
      action: "respond",
      actionLabel: `${agent.code} — Respond to Challenges`,
      perspective: agent.key,
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: `Respond to challenges directed at you. Defend, concede, or refine.`,
      userComments: rerunFeedback,
      apiFn: async () => {
        const r = await runRoundTableAction(session.api_session_id, agent.key, "respond", {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Respond failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const updated = result.updated_perspective || result;
        const summary = typeof updated === "object"
          ? (updated.perspective_title || updated.title || `Addressed ${result.challenges_addressed || 0} challenge(s)`)
          : String(updated).slice(0, 300);
        return new EmbedBuilder()
          .setTitle(`${agent.code} — Response`)
          .setDescription(`${summary}`)
          .setColor(0x27ae60)
          .setFooter({ text: `Phase 4 — Round Table | Response ${subStep + 1}/4` });
      },
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    return;
  }
}

// ──────────────────────────────────────────────────────────────
//  CONTENT SYNTHESIS — per-action validate mode
//  sub_action = 0:synthesise, 1:review, 2:revise, 3:review, 4:revise, ...
// ──────────────────────────────────────────────────────────────
async function runSynthesisValidateAction(session: any, thread: any, threadId: string, rerunFeedback?: string[]) {
  const subAction = session.sub_action ?? 0;

  dbOps.updateSession(session.id, { sub_step: 0, sub_action: subAction });

  // Action 0: SYNTHESISE
  if (subAction === 0) {
    await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "content_synthesis",
      agentName: "Content Writer",
      agentCodename: "Quill",
      action: "synthesise",
      actionLabel: "Quill — Synthesise Poster Pages",
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: "Synthesise all perspectives into structured poster page content.",
      userComments: rerunFeedback,
      apiFn: async () => {
        const r = await runSynthesisAction(session.api_session_id, "synthesise", {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Synthesis failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const pages = result.pages || [];
        return new EmbedBuilder()
          .setTitle(`Quill — ${result.brief_title || "Poster Draft"}`)
          .setDescription(
            `**${pages.length} pages** created\n` +
            pages.map((p: any) => `- ${p.page_type}: ${p.page_title || p.hero_statement || ""}`).join("\n")
          )
          .setColor(0x1abc9c)
          .setFooter({ text: "Phase 6 — Content Synthesis | Initial Draft" });
      },
      extractMeta: (result: any) => ({
        summary: result.brief_title || "",
      }),
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    return;
  }

  // Odd sub_action: REVIEW by Sterling
  if (subAction % 2 === 1) {
    const roundNum = Math.ceil(subAction / 2);

    await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "content_synthesis",
      agentName: "Copy Reviewer",
      agentCodename: "Sterling",
      action: "review",
      actionLabel: `Sterling — Copy Review Round ${roundNum}`,
      roundNumber: roundNum,
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: "Review poster content for writing quality, tone, and luxury standard.",
      userComments: rerunFeedback,
      apiFn: async () => {
        const r = await runSynthesisAction(session.api_session_id, "review", {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Review failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const review = result.review || result;
        const score = result.score ?? review.overall_score ?? 0;
        const approved = result.approved ?? review.approved ?? false;
        const demands = result.demands || review.demands || [];
        return new EmbedBuilder()
          .setTitle(`Sterling — Copy Review Round ${roundNum}`)
          .setDescription(
            `**Score:** ${score}/10 ${approved ? "✅ Approved" : "❌ Needs revision"}\n\n` +
            (demands.length > 0 ? `**Demands:**\n${demands.map((d: string) => `- ${d}`).join("\n")}` : "")
          )
          .setColor(approved ? 0x27ae60 : 0xe74c3c)
          .setFooter({ text: `Phase 6 — Content Synthesis | Review R${roundNum}` });
      },
      extractMeta: (result: any) => ({
        score: result.score ?? result.review?.overall_score,
        approved: result.approved ?? result.review?.approved,
      }),
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    return;
  }

  // Even sub_action >= 2: REVISE by Quill
  if (subAction % 2 === 0 && subAction >= 2) {
    const roundNum = subAction / 2;

    await executeAgentAction({
      sessionId: session.id,
      threadChannel: thread,
      stageId: "content_synthesis",
      agentName: "Content Writer",
      agentCodename: "Quill",
      action: "revise",
      actionLabel: `Quill — Content Revision Round ${roundNum}`,
      roundNumber: roundNum,
      executionOrder: getNextOrder(session.id),
      userFlag: "validate",
      sourceUrl: session.source_url,
      promptFixed: "Revise poster content based on copy reviewer's feedback.",
      userComments: rerunFeedback,
      apiFn: async () => {
        const r = await runSynthesisAction(session.api_session_id, "revise", {
          user_comments: rerunFeedback || [],
        });
        if (r.status === "error") throw new Error(r.error || "Revise failed");
        return r.result;
      },
      buildEmbed: (result: any) => {
        const pages = result.pages || [];
        return new EmbedBuilder()
          .setTitle(`Quill — Revision Round ${roundNum}`)
          .setDescription(
            `Revised based on Sterling's feedback.\n**${pages.length} pages** updated.`
          )
          .setColor(0xf39c12)
          .setFooter({ text: `Phase 6 — Content Synthesis | Revision R${roundNum}` });
      },
    });

    dbOps.updateSession(session.id, { status: "awaiting_approval" });
    return;
  }
}

// ──────────────────────────────────────────────────────────────
//  HELPER: Get action definition for single-action stages
// ──────────────────────────────────────────────────────────────
function getSingleActionDef(stageId: string): {
  agentName: string; agentCodename: string; action: string; promptFixed: string;
} {
  const defs: Record<string, { agentName: string; agentCodename: string; action: string; promptFixed: string }> = {
    content_extraction: { agentName: "System", agentCodename: "System", action: "extract", promptFixed: "Fetch article and extract content." },
    design_dna: { agentName: "DesignDNA", agentCodename: "Vesper", action: "create_identity", promptFixed: "Detect emotion and select visual identity." },
    editorial: { agentName: "Editor-in-Chief", agentCodename: "Paramount", action: "review_perspectives", promptFixed: "Review all perspectives for quality and coherence." },
    neutrality_check: { agentName: "Content Reviewer", agentCodename: "Justice", action: "review", promptFixed: "Check content for bias and neutrality." },
    discussion_potential: { agentName: "Discussion Analyst", agentCodename: "Spark", action: "evaluate", promptFixed: "Score engagement potential." },
    pre_validation: { agentName: "PreVisualValidator", agentCodename: "Sentinel-A", action: "validate", promptFixed: "Quality gate — 17 rules." },
    visuals: { agentName: "VisualGenerator", agentCodename: "Prism", action: "generate", promptFixed: "Generate all poster images." },
    pdf_generation: { agentName: "System", agentCodename: "System", action: "generate_pdf", promptFixed: "Build PDF poster." },
    post_validation: { agentName: "PostVisualValidator", agentCodename: "Sentinel-B", action: "validate", promptFixed: "Layout review — 18 rules." },
    send_email: { agentName: "LinkedIn Expert", agentCodename: "Herald", action: "craft_post", promptFixed: "Craft a Unicode-formatted LinkedIn post with headline hook, key insights, source URL, Discord invite link, and hashtags." },
  };
  return defs[stageId] || { agentName: "System", agentCodename: "System", action: "run", promptFixed: "" };
}

function getNextOrder(sessionId: string): number {
  const actions = dbOps.getAgentActions(sessionId);
  if (actions.length === 0) return 1;
  return Math.max(...actions.map((a: any) => a.execution_order || 0)) + 1;
}

// ──────────────────────────────────────────────────────────────
//  PIPELINE COMPLETE — shared by trust and validate paths
// ──────────────────────────────────────────────────────────────
async function completePipeline(session: any, threadId: string, thread: any) {
  dbOps.updateSession(session.id, { status: "complete" });
  const freshSession = dbOps.getSessionByThread(threadId);
  const completeEmbed = buildCompleteEmbed({
    headline: freshSession?.headline || freshSession?.source_url || session.source_url,
    combined_score: freshSession?.combined_score,
    duration_seconds: freshSession?.duration_seconds,
  });

  // Prefer Google Drive for a shareable link (large PDFs use resumable upload in google-drive.ts).
  let driveUrl = "";
  const localPdfPath = freshSession?.pdf_path;
  if (isGoogleDriveConfigured() && localPdfPath && localPdfPath !== "delivered" && existsSync(localPdfPath)) {
    try {
      const fileName = localPdfPath.replace(/\\/g, "/").split("/").pop() || "AI_Brief.pdf";
      driveUrl = await uploadPdfToGoogleDrive(localPdfPath, fileName);
      completeEmbed.addFields({
        name: "PDF Review Link",
        value: `[Open in Google Drive](${driveUrl})`,
        inline: false,
      });
    } catch (err: any) {
      const detail = err?.message && typeof err.message === "string" ? err.message : String(err);
      console.error("[GDRIVE] Upload failed at completion:", detail);
      const short = detail.length > 200 ? `${detail.slice(0, 200)}…` : detail;
      completeEmbed.addFields({
        name: "PDF Review Link",
        value:
          `Google Drive upload failed (${short}). Use the PDF attached in this thread above, or check Drive OAuth/folder access in server logs.`,
        inline: false,
      });
    }
  } else if (!isGoogleDriveConfigured()) {
    completeEmbed.addFields({
      name: "PDF Review Link",
      value: "Google Drive is not configured. Ask admin to set Drive credentials in `.env`.",
      inline: false,
    });
  }

  // send_email stage already generated LinkedIn-ready copy — always offer publish (no Drive required).
  const completionRow = buildCompletionActions(driveUrl || undefined);
  await thread.send({ embeds: [completeEmbed], components: [completionRow] });

  saveToUrlCache(freshSession || session);
  cleanupOldSessions(session.user_id);
}

/**
 * Store agent messages and debate turns from a stage's result into the DB.
 * This enables full offline replay and the rich discussion panel.
 */
function storeAgentData(sessionId: string, stageId: string, stageRunId: number, result: Record<string, any>) {
  try {
    // ── content_extraction: store extraction result ──
    if (stageId === "content_extraction") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "ContentExtractor",
        agent_codename: "System",
        role: "extractor",
        message_type: "extraction",
        content_json: JSON.stringify({
          headline: result.headline,
          publisher: result.publisher,
          description: result.description,
          content_length: result.content_length,
          article_text_preview: result.article_text_preview,
          cached_run_id: result.cached_run_id,
        }),
        content_summary: result.headline || "",
        round_number: 1,
      });
    }

    // ── design_dna: store design decisions ──
    if (stageId === "design_dna") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "DesignDirector",
        agent_codename: "Vesper",
        role: "designer",
        message_type: "design_decision",
        content_json: JSON.stringify({
          emotion: result.emotion,
          emotion_reasoning: result.emotion_reasoning,
          style_id: result.style_id,
          design_name: result.design_name,
          palette_id: result.palette_id,
          font_id: result.font_id,
          imagen_style: result.imagen_style,
          primary_color: result.primary_color,
          secondary_color: result.secondary_color,
          accent_color: result.accent_color,
          visual_motif: result.visual_motif,
        }),
        content_summary: `${result.emotion} — ${result.design_name} (${result.style_id})`,
        round_number: 1,
      });
    }

    // ── round_table: store cross-challenge interactions ──
    if (stageId === "round_table") {
      if (result.challenge_highlights?.length > 0) {
        for (const [i, challenge] of result.challenge_highlights.entries()) {
          dbOps.saveAgentMessage({
            session_id: sessionId,
            stage_run_id: stageRunId,
            stage_id: stageId,
            agent_name: String(challenge.pair || challenge.challenger || `Challenger ${i + 1}`),
            role: "challenger",
            message_type: "cross_challenge",
            content_json: JSON.stringify(challenge),
            content_summary: String(challenge.summary || "").slice(0, 200),
            round_number: i + 1,
          });
        }
      }
      // Store updated perspectives
      if (result.perspectives_after) {
        dbOps.saveAgentMessage({
          session_id: sessionId,
          stage_run_id: stageRunId,
          stage_id: stageId,
          agent_name: "AllAnalysts",
          role: "updated",
          message_type: "perspective_update",
          content_json: JSON.stringify(result.perspectives_after),
          content_summary: `${result.perspectives_updated || 0} perspectives updated after ${result.cross_challenges || 0} cross-challenges`,
          round_number: 99,
        });
      }
    }

    // ── content_synthesis: store writer output ──
    if (stageId === "content_synthesis") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "ContentWriter",
        agent_codename: "Quill",
        role: "writer",
        message_type: "synthesis",
        content_json: JSON.stringify({
          brief_title: result.brief_title,
          subtitle: result.subtitle,
          page_count: result.page_count,
          pages: result.pages,
        }),
        content_summary: result.brief_title || "",
        round_number: 1,
      });
    }

    // ── visuals: store generation details ──
    if (stageId === "visuals") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "VisualGenerator",
        agent_codename: "Prism",
        role: "generator",
        message_type: "generation",
        content_json: JSON.stringify({
          visual_count: result.visual_count,
          types: result.types,
          paths: result.paths,
        }),
        content_summary: `Generated ${result.visual_count || 0} visuals: ${(result.types || []).join(", ")}`,
        round_number: 1,
      });
    }

    // ── pdf_generation: store PDF creation details ──
    if (stageId === "pdf_generation") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "PDFAssembler",
        agent_codename: "System",
        role: "assembler",
        message_type: "generation",
        content_json: JSON.stringify({
          pdf_path: result.pdf_path,
          pdf_exists: result.pdf_exists,
          pdf_size_kb: result.pdf_size_kb,
          pdf_ready: result.pdf_ready,
        }),
        content_summary: `PDF ${result.pdf_exists ? "generated" : "failed"} — ${result.pdf_size_kb || 0}KB`,
        round_number: 1,
      });
    }

    // ── analyst_pairs: store each debate's full conversation ──
    if (stageId === "analyst_pairs" && result.full_debates) {
      for (const debate of result.full_debates) {
        for (const round of debate.rounds || []) {
          dbOps.saveDebateTurn({
            session_id: sessionId,
            stage_run_id: stageRunId,
            debate_label: debate.label || "unknown",
            preparer_name: debate.preparer_name || "?",
            reviewer_name: debate.reviewer_name || "?",
            round_number: round.round || 1,
            preparer_submission_json: round.preparer_submission ? JSON.stringify(round.preparer_submission) : undefined,
            reviewer_feedback_json: round.reviewer_feedback ? JSON.stringify(round.reviewer_feedback) : undefined,
            preparer_revision_json: round.preparer_revision ? JSON.stringify(round.preparer_revision) : undefined,
            demands_json: round.demands?.length > 0 ? JSON.stringify(round.demands) : undefined,
            verdict: round.verdict || undefined,
            score: round.score,
            approved: round.approved || false,
          });

          // Also store as agent messages for the discussion panel
          dbOps.saveAgentMessage({
            session_id: sessionId,
            stage_run_id: stageRunId,
            stage_id: stageId,
            agent_name: debate.preparer_name || "Analyst",
            role: "preparer",
            message_type: "submission",
            content_json: round.preparer_submission ? JSON.stringify(round.preparer_submission) : undefined,
            content_summary: round.preparer_submission?.title || round.preparer_submission?.key_insight || "",
            confidence: round.preparer_submission?.confidence,
            round_number: round.round || 1,
          });

          dbOps.saveAgentMessage({
            session_id: sessionId,
            stage_run_id: stageRunId,
            stage_id: stageId,
            agent_name: debate.reviewer_name || "Reviewer",
            role: "reviewer",
            message_type: "feedback",
            content_json: round.reviewer_feedback ? JSON.stringify(round.reviewer_feedback) : undefined,
            content_summary: round.reviewer_feedback?.verdict || round.verdict || "",
            score: round.score,
            approved: round.approved || false,
            round_number: round.round || 1,
          });
        }
      }
    }

    // ── editorial: store per-agent feedback ──
    if (stageId === "editorial" && result.feedback_per_agent) {
      for (const [agentName, feedback] of Object.entries(result.feedback_per_agent as Record<string, any>)) {
        dbOps.saveAgentMessage({
          session_id: sessionId,
          stage_run_id: stageRunId,
          stage_id: stageId,
          agent_name: "EditorInChief",
          agent_codename: "Paramount",
          role: "editor",
          message_type: "review",
          content_json: JSON.stringify(feedback),
          content_summary: `Feedback for ${agentName}: ${(feedback as any)?.feedback || ""}`.slice(0, 200),
          score: (feedback as any)?.score,
          round_number: 1,
        });
      }
    }

    // ── neutrality_check: store review ──
    if (stageId === "neutrality_check") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "ContentReviewer",
        agent_codename: "Justice",
        role: "reviewer",
        message_type: "review",
        content_json: JSON.stringify({
          tone_score: result.tone_score,
          issues: result.issues,
          strengths: result.strengths,
          verdict: result.verdict,
        }),
        content_summary: result.verdict || "",
        score: result.tone_score,
        approved: result.approved || false,
        round_number: 1,
      });
    }

    // ── discussion_potential: store evaluation ──
    if (stageId === "discussion_potential") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "DiscussionAnalyst",
        agent_codename: "Spark",
        role: "analyst",
        message_type: "evaluation",
        content_json: JSON.stringify({
          engagement_score: result.engagement_score,
          verdict: result.verdict,
          discussion_hooks: result.discussion_hooks,
          reasoning: result.reasoning,
        }),
        content_summary: result.reasoning || result.verdict || "",
        score: result.engagement_score,
        round_number: 1,
      });
    }

    // ── pre_validation / post_validation: store validation results ──
    if (stageId === "pre_validation" || stageId === "post_validation") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: stageId === "pre_validation" ? "Sentinel-A" : "Sentinel-B",
        role: "validator",
        message_type: "validation",
        content_json: JSON.stringify({
          total_score: result.total_score,
          explanation: result.explanation,
          critical_failures: result.critical_failures,
          rules_checked: result.rules_checked,
          verdict: result.verdict,
        }),
        content_summary: result.explanation || result.verdict || "",
        score: result.total_score,
        approved: result.approved || false,
        round_number: 1,
      });
    }
    // ── send_email: store the LinkedIn post draft ──
    if (stageId === "send_email") {
      dbOps.saveAgentMessage({
        session_id: sessionId,
        stage_run_id: stageRunId,
        stage_id: stageId,
        agent_name: "LinkedInExpert",
        agent_codename: "Herald",
        role: "writer",
        message_type: "email_draft",
        content_json: JSON.stringify({
          post_text: result.post_text,
          document_title: result.document_title,
          hashtags: result.hashtags,
          news_url: result.news_url,
        }),
        content_summary: result.document_title || result.headline || "",
        round_number: 1,
      });
    }

    // ── Also populate agent_actions execution ledger ──
    const pref = dbOps.getPreference(sessionId, stageId);
    populateAgentActionsFromStageResult(sessionId, stageId, result, pref);

  } catch (err) {
    console.error(`Error storing agent data for ${stageId}:`, err);
    // Don't fail the stage if DB storage fails
  }
}

/**
 * Save completed session data to URL cache for future reuse.
 */
function saveToUrlCache(session: any) {
  try {
    const url = session.source_url;
    if (!url || url === session.source_text) return; // Only cache URL-based runs

    const stageRuns = dbOps.getStageRunsBySession(session.id);
    const stageResults: Record<string, any> = {};
    for (const run of stageRuns) {
      if (run.status === "success" && run.output_json) {
        try {
          stageResults[run.stage_id] = JSON.parse(run.output_json);
        } catch { /* ignore */ }
      }
    }

    dbOps.saveUrlCache({
      url,
      session_id: session.id,
      headline: session.headline,
      publisher: session.publisher,
      stage_results_json: JSON.stringify(stageResults),
      pdf_path: session.pdf_path,
      combined_score: session.combined_score,
    });

    console.log(`[CACHE] Saved results for URL: ${url.slice(0, 80)}`);
  } catch (err) {
    console.error("Error saving URL cache:", err);
  }
}

/**
 * Enforce per-user session limit (default: 5).
 * Deletes old sessions from the DB and removes their PDF files from disk.
 * Also sweeps the output folder for orphan PDFs not tracked by any session.
 */
const MAX_SESSIONS_PER_USER = 5;
const PDF_OUTPUT_DIR = resolve(__dirname, "../../../aibrief/output");

function cleanupOldSessions(userId: string) {
  try {
    const { deletedIds, deletedPdfs } = dbOps.cleanupUserSessions(userId, MAX_SESSIONS_PER_USER);

    if (deletedIds.length > 0) {
      console.log(`[CLEANUP] Removed ${deletedIds.length} old session(s) for user ${userId}: ${deletedIds.join(", ")}`);
    }

    // Delete PDF files that belonged to deleted sessions
    for (const pdfPath of deletedPdfs) {
      try {
        if (existsSync(pdfPath)) {
          unlinkSync(pdfPath);
          console.log(`[CLEANUP] Deleted session PDF: ${pdfPath}`);
        }
      } catch (e) {
        console.warn(`[CLEANUP] Could not delete PDF ${pdfPath}:`, (e as Error).message);
      }
    }

    // Sweep orphan PDFs: files on disk not referenced by any session in the DB
    sweepOrphanPdfs();
  } catch (err) {
    console.error("[CLEANUP] Error cleaning up old sessions:", err);
  }
}

/**
 * Remove PDF files from the output directory that are not referenced
 * by any session's pdf_path in the database.
 */
function sweepOrphanPdfs() {
  try {
    if (!existsSync(PDF_OUTPUT_DIR)) return;

    // Collect all pdf_path values currently tracked in the DB
    const allTracked = dbOps.getAllTrackedPdfPaths();
    const trackedSet = new Set(allTracked.map((p) => p.replace(/\\/g, "/").toLowerCase()));

    const files = readdirSync(PDF_OUTPUT_DIR).filter((f) => f.toLowerCase().endsWith(".pdf"));
    let removed = 0;

    for (const file of files) {
      const fullPath = resolve(PDF_OUTPUT_DIR, file).replace(/\\/g, "/").toLowerCase();
      if (!trackedSet.has(fullPath)) {
        try {
          unlinkSync(resolve(PDF_OUTPUT_DIR, file));
          removed++;
        } catch (e) {
          // ignore individual file errors
        }
      }
    }

    if (removed > 0) {
      console.log(`[CLEANUP] Swept ${removed} orphan PDF(s) from output folder`);
    }
  } catch (err) {
    console.warn("[CLEANUP] Orphan sweep error:", err);
  }
}

/**
 * Deliver the PDF to the thread immediately — agents don't block this.
 * Reads the file directly from disk (same machine) to avoid HTTP timeout issues.
 */
async function deliverPdf(threadId: string, apiSessionId: string, pdfPath?: string) {
  const botClient = getClient();
  const thread = await botClient.channels.fetch(threadId);
  if (!thread || !thread.isTextBased()) return;

  try {
    let pdfBuffer: Buffer | null = null;
    let fileName = "AI_Brief.pdf";

    // Attempt 1: Read from local file path (fastest, no network)
    if (pdfPath && existsSync(pdfPath)) {
      console.log(`[PDF] Reading local file: ${pdfPath}`);
      pdfBuffer = readFileSync(pdfPath);
      const parts = pdfPath.replace(/\\/g, "/").split("/");
      fileName = parts[parts.length - 1] || "AI_Brief.pdf";
    }

    // Attempt 2: Try getting path from the API, then read local file
    if (!pdfBuffer) {
      try {
        const resp = await fetch(`${process.env.PYTHON_API_URL || "http://localhost:8900"}/session/${apiSessionId}/pdf`, {
          signal: AbortSignal.timeout(10_000),
        });
        if (resp.ok) {
          const info = await resp.json() as { pdf_path: string };
          if (info.pdf_path && existsSync(info.pdf_path)) {
            console.log(`[PDF] Reading local file from API path: ${info.pdf_path}`);
            pdfBuffer = readFileSync(info.pdf_path);
            const parts = info.pdf_path.replace(/\\/g, "/").split("/");
            fileName = parts[parts.length - 1] || "AI_Brief.pdf";
            pdfPath = info.pdf_path; // save for session update
          }
        }
      } catch (e) {
        console.warn("[PDF] Could not get path from API:", (e as Error).message);
      }
    }

    // Attempt 3: Last resort — HTTP download
    if (!pdfBuffer) {
      console.log("[PDF] Falling back to HTTP download...");
      const resp = await fetch(
        `${process.env.PYTHON_API_URL || "http://localhost:8900"}/session/${apiSessionId}/pdf/download`,
        { signal: AbortSignal.timeout(120_000) }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      pdfBuffer = Buffer.from(await resp.arrayBuffer());
    }

    const sizeKb = Math.round(pdfBuffer.length / 1024);
    const sizeMb = Math.round(sizeKb / 1024);
    const pdfEmbed = buildPdfDeliveryEmbed({ pdf_size_kb: sizeKb });

    // Discord upload limit: ~25MB for most servers
    if (pdfBuffer.length > 24 * 1024 * 1024) {
      console.log(`[PDF] File too large for Discord upload (${sizeMb}MB). Sharing path instead.`);
      pdfEmbed.setDescription(
        `**PDF Generated** (${sizeMb}MB — too large for Discord upload)\n\n` +
        `**File location:**\n\`${pdfPath || fileName}\`\n\n` +
        `Open the file directly from your computer.`
      );
      await (thread as any).send({ embeds: [pdfEmbed] });
    } else {
      const attachment = new AttachmentBuilder(pdfBuffer, { name: fileName });
      await (thread as any).send({
        embeds: [pdfEmbed],
        files: [attachment],
      });
    }

    // Update session with pdf path info
    const session = dbOps.getSessionByThread(threadId);
    if (session) {
      dbOps.updateSession(session.id, { pdf_path: pdfPath || "delivered" });
    }
  } catch (err: any) {
    console.error("Failed to deliver PDF:", err);

    // One retry after 3 seconds
    await (thread as any).send(`PDF delivery failed: ${err.message}. Retrying...`);
    await new Promise((r) => setTimeout(r, 3000));

    try {
      // On retry, try local file first
      if (pdfPath && existsSync(pdfPath)) {
        const pdfBuffer = readFileSync(pdfPath);
        const attachment = new AttachmentBuilder(pdfBuffer, { name: "AI_Brief.pdf" });
        await (thread as any).send({ content: "**PDF delivered:**", files: [attachment] });
        return;
      }
      // Fall back to HTTP
      const resp = await fetch(
        `${process.env.PYTHON_API_URL || "http://localhost:8900"}/session/${apiSessionId}/pdf/download`,
        { signal: AbortSignal.timeout(120_000) }
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const buf = Buffer.from(await resp.arrayBuffer());
      const attachment = new AttachmentBuilder(buf, { name: "AI_Brief.pdf" });
      await (thread as any).send({ content: "**PDF delivered (retry):**", files: [attachment] });
    } catch (retryErr: any) {
      const pathMsg = pdfPath ? `\nFile location: \`${pdfPath}\`` : "";
      await (thread as any).send(`PDF delivery failed: ${retryErr.message}${pathMsg}`);
    }
  }
}

/**
 * Post each debate as a separate rich embed message.
 * Users see the FULL conversation, not a truncated summary.
 */
async function postDebateTurns(thread: any, fullDebates: any[]) {
  for (const debate of fullDebates) {
    const embed = buildDebateTurnEmbed(debate);
    await thread.send({ embeds: [embed] });
    // Small delay to avoid rate limits
    await new Promise((r) => setTimeout(r, 300));
  }
}

/**
 * Handle approval — advance to next action within the stage, or to the next stage.
 *
 * For multi-action stages (analyst_pairs, round_table, content_synthesis):
 *   - Advances sub_action (and sometimes sub_step) within the stage
 *   - Only moves to the next stage when all actions in the current stage are done
 *
 * For single-action stages: moves directly to the next stage.
 */
export async function handleApproval(threadId: string, approvedStageId: string) {
  const session = dbOps.getSessionByThread(threadId);
  if (!session) return;

  const pref = dbOps.getPreference(session.id, approvedStageId);
  const subStep = session.sub_step ?? 0;
  const subAction = session.sub_action ?? 0;

  // ══════════════════════════════════════════════════════════════
  //  ANALYST_PAIRS — advance within perspective debate
  // ══════════════════════════════════════════════════════════════
  if (approvedStageId === "analyst_pairs" && pref !== "trust") {
    // Determine what was just approved
    const perspective = PERSPECTIVES[subStep];

    if (subAction === 0) {
      // Prepare was approved → move to review round 1
      dbOps.updateSession(session.id, { sub_action: 1 });
      await runNextStage(threadId);
      return;
    }

    if (subAction % 2 === 1) {
      // Review was approved — check if reviewer said "approved"
      const lastReview = dbOps.getAgentAction(
        session.id, "analyst_pairs", perspective, "review", Math.ceil(subAction / 2)
      );
      const reviewApproved = lastReview?.approved;
      const roundNum = Math.ceil(subAction / 2);

      if (reviewApproved || roundNum >= 3) {
        // Perspective complete — finalize and move to next perspective
        await runAnalystAction(session.api_session_id, perspective, "finalize");
        const nextPersp = subStep + 1;
        if (nextPersp < PERSPECTIVES.length) {
          dbOps.updateSession(session.id, { sub_step: nextPersp, sub_action: 0 });
          await runNextStage(threadId);
        } else {
          // All perspectives done → advance to next stage
          advanceToNextStage(session, approvedStageId, threadId);
        }
        return;
      }

      // Not approved, more rounds available → revise
      dbOps.updateSession(session.id, { sub_action: subAction + 1 });
      await runNextStage(threadId);
      return;
    }

    if (subAction % 2 === 0 && subAction >= 2) {
      // Revise was approved → move to next review round
      dbOps.updateSession(session.id, { sub_action: subAction + 1 });
      await runNextStage(threadId);
      return;
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  ROUND TABLE — advance within challenge/respond pairs
  // ══════════════════════════════════════════════════════════════
  if (approvedStageId === "round_table" && pref !== "trust") {
    if (subAction === 0) {
      // Challenge approved → respond
      dbOps.updateSession(session.id, { sub_action: 1 });
      await runNextStage(threadId);
      return;
    }
    if (subAction === 1) {
      // Respond approved → next agent or done
      const nextAgent = subStep + 1;
      if (nextAgent < ROUND_TABLE_AGENTS.length) {
        dbOps.updateSession(session.id, { sub_step: nextAgent, sub_action: 0 });
        await runNextStage(threadId);
      } else {
        advanceToNextStage(session, approvedStageId, threadId);
      }
      return;
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  CONTENT SYNTHESIS — advance within synthesise/review/revise
  // ══════════════════════════════════════════════════════════════
  if (approvedStageId === "content_synthesis" && pref !== "trust") {
    if (subAction === 0) {
      // Synthesise approved → Sterling reviews
      dbOps.updateSession(session.id, { sub_action: 1 });
      await runNextStage(threadId);
      return;
    }

    if (subAction % 2 === 1) {
      // Review approved — check if Sterling approved
      const roundNum = Math.ceil(subAction / 2);
      const lastReview = dbOps.getAgentAction(
        session.id, "content_synthesis", null, "review", roundNum
      );
      const reviewApproved = lastReview?.approved;

      if (reviewApproved || roundNum >= 3) {
        // Content approved → advance to next stage
        advanceToNextStage(session, approvedStageId, threadId);
        return;
      }

      // Not approved → Quill revises
      dbOps.updateSession(session.id, { sub_action: subAction + 1 });
      await runNextStage(threadId);
      return;
    }

    if (subAction % 2 === 0 && subAction >= 2) {
      // Revise approved → Sterling reviews again
      dbOps.updateSession(session.id, { sub_action: subAction + 1 });
      await runNextStage(threadId);
      return;
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  SINGLE-ACTION STAGES — advance to next stage
  // ══════════════════════════════════════════════════════════════
  await advanceToNextStage(session, approvedStageId, threadId);
}

/**
 * Advance from the completed stage to the next one, or finish the pipeline.
 */
async function advanceToNextStage(session: any, completedStageId: string, threadId: string) {
  const next = getNextStage(completedStageId);

  if (!next) {
    // Pipeline complete
    const botClient = getClient();
    const thread = await botClient.channels.fetch(threadId);
    if (!thread || !thread.isTextBased()) return;
    await completePipeline(session, threadId, thread);
    return;
  }

  // Reset sub-step/action for the next stage and advance
  dbOps.updateSession(session.id, { current_stage: next.id, sub_step: null, sub_action: null });
  await runNextStage(threadId);
}

/**
 * Handle action re-run — re-run the CURRENT action with user feedback injected.
 * sub_step and sub_action stay the same so the exact same action is re-run.
 *
 * The feedback is stored in `pendingRerunFeedback` so the wrapper can pick it up.
 * When the wrapper sees pending feedback, it SKIPS cache and calls the API fresh
 * with the user's comments injected into the prompt.
 */
export async function handleRerun(threadId: string, stageId: string, feedback?: string[]) {
  const session = dbOps.getSessionByThread(threadId);
  if (!session) return;

  // Store feedback so the wrapper can find it
  if (feedback && feedback.length > 0) {
    pendingRerunFeedback.set(threadId, feedback);
  }

  // Keep current sub_step/sub_action — re-run the same action
  dbOps.updateSession(session.id, { current_stage: stageId, status: "running" });
  await runNextStage(threadId);
}

/**
 * Extract key metadata from stage results and store on the session row.
 * This makes the session row a quick-reference summary without needing
 * to parse stage_runs.output_json.
 */
function enrichSessionFromStage(sessionId: string, stageId: string, result: Record<string, any>) {
  const updates: Record<string, any> = {};

  switch (stageId) {
    case "content_extraction":
      updates.headline = result.headline;
      updates.publisher = result.publisher;
      updates.article_text = result.description;
      break;
    case "design_dna":
      updates.emotion = result.emotion;
      updates.style_id = result.style_id;
      updates.palette_id = result.palette_id;
      updates.font_id = result.font_id;
      updates.design_name = result.design_name;
      updates.imagen_style = result.imagen_style;
      break;
    case "content_synthesis":
      updates.brief_title = result.brief_title;
      break;
    case "discussion_potential":
      updates.discussion_score = result.engagement_score;
      break;
    case "pre_validation":
      updates.pre_visual_score = result.total_score;
      break;
    case "analyst_pairs":
      updates.total_debates = result.analyst_count || 4;
      updates.total_rounds = result.total_debate_rounds;
      break;
    case "pdf_generation":
      updates.pdf_path = result.pdf_path;
      break;
    case "post_validation":
      updates.post_visual_score = result.total_score;
      updates.combined_score = result.combined_score;
      updates.duration_seconds = result.duration_seconds;
      break;
    case "send_email":
      updates.post_text = result.post_text;
      updates.document_title = result.document_title;
      break;
  }

  if (Object.keys(updates).length > 0) {
    dbOps.updateSession(sessionId, updates);
  }
}
