/**
 * Agent Action Wrapper — the core orchestration layer.
 *
 * Every API call in the pipeline goes through this wrapper. It:
 *   1. Checks the agent_actions ledger for a cached result (replay)
 *   2. If not cached, executes the API call
 *   3. Saves the result to agent_actions with full input/output/prompt data
 *   4. If the user_flag is "validate": shows the output + Approve/Re-run buttons, stops
 *   5. If the user_flag is "trust": shows auto-approved output, signals to continue
 *
 * This is the SINGLE source of truth. The agent_actions table replaces the need
 * for separate caching mechanisms for individual agent outputs.
 */

import { EmbedBuilder } from "discord.js";
import dbOps from "./database";
import { buildApprovalButtons } from "../utils/embeds";

// ── Types ──

export interface WrapperInput {
  sessionId: string;
  threadChannel: any;             // Discord TextBasedChannel (thread)
  stageId: string;
  agentName: string;
  agentCodename: string;
  action: string;                 // e.g., "prepare", "review", "extract"
  actionLabel: string;            // human-readable
  perspective?: string;           // for analyst debates
  roundNumber?: number;
  executionOrder: number;         // global sequence number in this session
  userFlag: "trust" | "validate"; // inherited from stage preference

  // Cross-session caching: the source URL from the session
  sourceUrl?: string;

  // Prompt tracking
  promptFixed?: string;           // the constant instruction part
  promptVariablesJson?: string;   // JSON mapping of variable sources
  inputDataJson?: string;         // the actual resolved input data sent to the agent

  // User feedback from a re-run — when present, cache is skipped and API is called fresh
  userComments?: string[];

  // The actual API call — only executed if no cache hit (or user feedback present)
  apiFn: () => Promise<any>;

  // How to build the Discord embed from the result
  buildEmbed: (result: any) => EmbedBuilder;

  // Optional: extract summary, score, confidence from the result
  extractMeta?: (result: any) => {
    summary?: string;
    score?: number;
    confidence?: number;
    approved?: boolean;
  };
}

export interface WrapperResult {
  continue: boolean;              // true = caller should advance, false = waiting for user
  output: any;                    // the agent's output (from cache or API)
  actionId: number;               // the DB row ID in agent_actions
  cached: boolean;                // whether this was a cache hit
}

// ── Main Wrapper Function ──

export async function executeAgentAction(input: WrapperInput): Promise<WrapperResult> {
  const {
    sessionId, threadChannel, stageId, agentName, agentCodename,
    action, actionLabel, perspective, roundNumber = 1, executionOrder,
    userFlag, sourceUrl, promptFixed, promptVariablesJson, inputDataJson,
    userComments, apiFn, buildEmbed, extractMeta,
  } = input;

  // ─────────────────────────────────────────────
  // STEP 0: Check for user input (re-run feedback)
  // If user has provided feedback, ALWAYS skip cache and run the API fresh.
  // The user's word overrides any cached result.
  // ─────────────────────────────────────────────
  const hasUserFeedback = userComments && userComments.length > 0;
  if (hasUserFeedback) {
    console.log(`[WRAPPER] User feedback present for ${agentCodename}.${action} — skipping cache, running fresh`);
  }

  // ─────────────────────────────────────────────
  // STEP 1: Check for cached result (ONLY if no user feedback)
  // ─────────────────────────────────────────────
  let output: any;
  let wasCached = false;
  let durationSec = 0;
  let cacheSource = "";
  let localCached: any = null;

  if (!hasUserFeedback) {
    // 1a: Check current session's agent_actions ledger
    localCached = dbOps.getAgentAction(
      sessionId, stageId, perspective ?? null, action, roundNumber
    );

    if (localCached && (localCached.status === "success" || localCached.status === "completed" || localCached.status === "auto_approved") && localCached.output_json) {
      try {
        output = JSON.parse(localCached.output_json);
        wasCached = true;
        cacheSource = "local";
        console.log(`[WRAPPER] Local cache hit: ${agentCodename}.${action} (${stageId}${perspective ? "/" + perspective : ""}) — 0 API calls`);
      } catch {
        console.warn(`[WRAPPER] Local cache parse failed for ${agentCodename}.${action} — trying cross-session`);
      }
    }

    // 1b: Cross-session cache — find from ANY previous session with the same URL
    if (!wasCached && sourceUrl) {
      const crossCached = dbOps.getCrossSessionCachedAction(
        sourceUrl, stageId, perspective ?? null, action, roundNumber
      );
      if (crossCached && crossCached.output_json) {
        try {
          output = JSON.parse(crossCached.output_json);
          wasCached = true;
          cacheSource = "cross-session";
          console.log(`[WRAPPER] Cross-session cache hit: ${agentCodename}.${action} from session ${crossCached.session_id} — 0 API calls`);
        } catch {
          console.warn(`[WRAPPER] Cross-session cache parse failed for ${agentCodename}.${action} — running fresh`);
        }
      }
    }
  }

  // ─────────────────────────────────────────────
  // STEP 2: Execute the API call if not cached (or user feedback present)
  // ─────────────────────────────────────────────
  if (!wasCached) {
    // Show "running" indicator
    const runningEmbed = new EmbedBuilder()
      .setTitle(`${actionLabel}`)
      .setDescription(`Running...`)
      .setColor(0x3498db);
    const runningMsg = await threadChannel.send({ embeds: [runningEmbed] });

    const startTime = Date.now();
    try {
      output = await apiFn();
      durationSec = (Date.now() - startTime) / 1000;
      console.log(`[WRAPPER] ${agentCodename}.${action} completed (${durationSec.toFixed(1)}s)`);

      // Clean up running message
      await runningMsg.delete().catch(() => {});
    } catch (err: any) {
      durationSec = (Date.now() - startTime) / 1000;
      console.error(`[WRAPPER] ${agentCodename}.${action} failed:`, err.message);

      // Save error to agent_actions (write-through — save immediately)
      const errorId = dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: agentName,
        agent_codename: agentCodename,
        action,
        action_label: actionLabel,
        stage: stageId,
        perspective,
        round_number: roundNumber,
        execution_order: executionOrder,
        prompt_fixed: promptFixed,
        prompt_variables_json: promptVariablesJson,
        input_data_json: inputDataJson,
        output_json: JSON.stringify({ error: err.message }),
        output_summary: `Error: ${err.message}`,
        user_flag: userFlag,
        duration_sec: durationSec,
        status: "error",
      });

      await runningMsg.edit({
        embeds: [new EmbedBuilder()
          .setTitle(`${actionLabel} — Failed`)
          .setDescription(`Error: ${err.message}`)
          .setColor(0xe74c3c)],
      });

      return { continue: false, output: null, actionId: errorId, cached: false };
    }
  }

  // ─────────────────────────────────────────────
  // STEP 3: Extract metadata from the result
  // ─────────────────────────────────────────────
  const meta = extractMeta ? extractMeta(output) : {};

  // ─────────────────────────────────────────────
  // STEP 4: WRITE-THROUGH — save to DB IMMEDIATELY before displaying
  // This ensures every result is persisted for cross-session reuse
  // ─────────────────────────────────────────────
  let actionDbId: number;

  if (wasCached && cacheSource === "local" && localCached) {
    // Local cache hit — reuse the existing row
    actionDbId = localCached.id;
  } else {
    // Fresh API result OR cross-session cache → save to THIS session's ledger
    actionDbId = dbOps.saveAgentAction({
      session_id: sessionId,
      agent_name: agentName,
      agent_codename: agentCodename,
      action,
      action_label: actionLabel,
      stage: stageId,
      perspective,
      round_number: roundNumber,
      execution_order: executionOrder,
      prompt_fixed: promptFixed,
      prompt_variables_json: promptVariablesJson,
      input_data_json: inputDataJson,
      output_json: JSON.stringify(output),
      output_summary: meta.summary,
      score: meta.score,
      confidence: meta.confidence,
      approved: meta.approved,
      user_flag: userFlag,
      duration_sec: durationSec,
      status: wasCached ? "completed" : "success",
    });
    console.log(`[WRAPPER] Write-through: saved ${agentCodename}.${action} to agent_actions (id=${actionDbId}, source=${cacheSource || "api"})`);
  }

  // ─────────────────────────────────────────────
  // STEP 5: Display the result embed
  // ─────────────────────────────────────────────
  const resultEmbed = buildEmbed(output);

  // Add cache indicator if this was a replay
  if (wasCached) {
    resultEmbed.addFields({
      name: "Cached",
      value: `Result loaded from ${cacheSource} cache — 0 API calls`,
      inline: false,
    });
  }

  if (userFlag === "trust") {
    // ── TRUST: show auto-approved, signal to continue ──
    resultEmbed.addFields({
      name: "Auto-Approved",
      value: `${agentCodename} — ${actionLabel}`,
      inline: false,
    });
    await threadChannel.send({ embeds: [resultEmbed] });

    // Mark as auto-approved in the ledger
    if (!wasCached || cacheSource === "cross-session") {
      dbOps.updateAgentAction(actionDbId, { user_approved: 1, status: "auto_approved" });
    }

    return { continue: true, output, actionId: actionDbId, cached: wasCached };
  } else {
    // ── VALIDATE: show output + prompt description + Approve/Re-run buttons ──
    await threadChannel.send({ embeds: [resultEmbed] });

    // Build prompt context for the user so they know what this agent was told to do
    const promptDescription = promptFixed
      ? `**Agent Prompt:**\n> ${promptFixed.slice(0, 500)}${promptFixed.length > 500 ? "..." : ""}\n\n`
      : "";

    // Post approval buttons as a separate message (always the last message)
    const buttons = buildApprovalButtons(stageId);
    const buttonMsg = await threadChannel.send({
      content:
        `**${actionLabel}**\n` +
        promptDescription +
        `Approve to continue, or Re-run with new instructions:`,
      components: [buttons],
    });

    // Store the button message ID on the action for reference
    dbOps.updateAgentAction(actionDbId, { message_id: buttonMsg.id, status: "awaiting_approval" });

    return { continue: false, output, actionId: actionDbId, cached: wasCached };
  }
}

// ── Helper: Check if an agent action exists in the ledger (for replay) ──
// Checks local session first, then cross-session by URL.
export function getAgentActionCached(
  sessionId: string,
  stage: string,
  perspective: string | null,
  action: string,
  round: number = 1,
  sourceUrl?: string
): any | null {
  // Local session cache
  const row = dbOps.getAgentAction(sessionId, stage, perspective, action, round);
  if (row && (row.status === "success" || row.status === "completed" || row.status === "auto_approved") && row.output_json) {
    try {
      return JSON.parse(row.output_json);
    } catch {
      /* fall through */
    }
  }

  // Cross-session cache by URL
  if (sourceUrl) {
    const crossRow = dbOps.getCrossSessionCachedAction(sourceUrl, stage, perspective, action, round);
    if (crossRow && crossRow.output_json) {
      try {
        return JSON.parse(crossRow.output_json);
      } catch {
        return null;
      }
    }
  }

  return null;
}

// ── Helper: Populate agent_actions from existing stage result data ──
// Used when migrating from the old caching system (url_cache / stage_runs)
// to the new agent_actions ledger.
export function populateAgentActionsFromStageResult(
  sessionId: string,
  stageId: string,
  result: Record<string, any>,
  userFlag: "trust" | "validate" = "trust"
): void {
  let order = getNextExecutionOrder(sessionId);

  switch (stageId) {
    case "content_extraction":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "System",
        agent_codename: "System",
        action: "extract",
        action_label: "Extract Content from URL",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.headline || "",
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "design_dna":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "DesignDNA",
        agent_codename: "Vesper",
        action: "create_identity",
        action_label: "Detect Emotion and Design Identity",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: `${result.emotion} — ${result.design_name}`,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "analyst_pairs":
      // This is the bulk endpoint — break down by perspective
      if (result.full_debates) {
        for (const debate of result.full_debates) {
          const label = debate.label?.toLowerCase() || "unknown";
          const prepName = debate.preparer_name || "Analyst";
          const revName = debate.reviewer_name || "Reviewer";

          // Initial prepare
          const firstRound = debate.rounds?.[0];
          if (firstRound?.preparer_submission) {
            dbOps.saveAgentAction({
              session_id: sessionId,
              agent_name: prepName,
              agent_codename: prepName,
              action: "prepare",
              action_label: `${prepName} — Initial ${label} Analysis`,
              stage: "analyst_pairs",
              perspective: label,
              round_number: 1,
              execution_order: order++,
              output_json: JSON.stringify(firstRound.preparer_submission),
              output_summary: firstRound.preparer_submission?.title || "",
              confidence: firstRound.preparer_submission?.confidence,
              user_flag: userFlag,
              status: "success",
            });
          }

          // Each debate round
          for (const round of debate.rounds || []) {
            if (round.reviewer_feedback) {
              dbOps.saveAgentAction({
                session_id: sessionId,
                agent_name: revName,
                agent_codename: revName,
                action: "review",
                action_label: `${revName} — Review Round ${round.round || 1}`,
                stage: "analyst_pairs",
                perspective: label,
                round_number: round.round || 1,
                execution_order: order++,
                output_json: JSON.stringify(round.reviewer_feedback),
                output_summary: round.reviewer_feedback?.verdict || round.verdict || "",
                score: round.score,
                approved: round.approved,
                user_flag: userFlag,
                status: "success",
              });
            }
            if (round.preparer_revision) {
              dbOps.saveAgentAction({
                session_id: sessionId,
                agent_name: prepName,
                agent_codename: prepName,
                action: "revise",
                action_label: `${prepName} — Revision Round ${round.round || 1}`,
                stage: "analyst_pairs",
                perspective: label,
                round_number: round.round || 1,
                execution_order: order++,
                output_json: JSON.stringify(round.preparer_revision),
                output_summary: "",
                user_flag: userFlag,
                status: "success",
              });
            }
          }
        }
      }
      break;

    case "round_table":
      if (result.challenge_highlights) {
        // Map challenger names to agent keys for cache consistency
        const challengerKeyMap: Record<string, string> = {
          economist: "economist", aurelia: "economist",
          historian: "historian", clio: "historian",
          futurist: "futurist", nova: "futurist",
          sociologist: "sociologist", sage: "sociologist",
        };
        for (const ch of result.challenge_highlights) {
          const rawName = String(ch.challenger || ch.pair || "").toLowerCase();
          const perspKey = challengerKeyMap[rawName] || rawName.split(" ")[0] || undefined;
          dbOps.saveAgentAction({
            session_id: sessionId,
            agent_name: String(ch.challenger || ch.pair || "Analyst"),
            agent_codename: String(ch.challenger || "Analyst"),
            action: "challenge",
            action_label: `${ch.challenger || "Analyst"} — Cross-Discipline Challenge`,
            stage: stageId,
            perspective: perspKey,
            execution_order: order++,
            output_json: JSON.stringify(ch),
            output_summary: String(ch.summary || "").slice(0, 200),
            user_flag: userFlag,
            status: "success",
          });
        }
      }
      break;

    case "editorial":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "Editor-in-Chief",
        agent_codename: "Paramount",
        action: "review_perspectives",
        action_label: "Paramount — Editorial Review",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.overall_assessment?.slice(0, 200) || result.verdict || "",
        score: result.score,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "content_synthesis":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "Content Writer",
        agent_codename: "Quill",
        action: "synthesise",
        action_label: "Quill — Synthesise Poster Pages",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.brief_title || "",
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "neutrality_check":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "Content Reviewer",
        agent_codename: "Justice",
        action: "review",
        action_label: "Justice — Neutrality and Bias Review",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.verdict || "",
        score: result.tone_score,
        approved: result.approved,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "discussion_potential":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "Discussion Potential Analyst",
        agent_codename: "Spark",
        action: "evaluate",
        action_label: "Spark — Engagement Potential Scoring",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.reasoning || result.verdict || "",
        score: result.engagement_score,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "pre_validation":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "PreVisualValidator",
        agent_codename: "Sentinel-A",
        action: "validate",
        action_label: "Sentinel-A — Quality Gate (17 Rules)",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.explanation || result.verdict || "",
        score: result.total_score,
        approved: result.approved,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "visuals":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "VisualGenerator",
        agent_codename: "Prism",
        action: "generate",
        action_label: "Prism — Generate All Visuals",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: `Generated ${result.visual_count || 0} visuals`,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "pdf_generation":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "System",
        agent_codename: "System",
        action: "generate_pdf",
        action_label: "System — Build PDF Poster",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: `PDF ${result.pdf_exists ? "generated" : "failed"} — ${result.pdf_size_kb || 0}KB`,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "post_validation":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "PostVisualValidator",
        agent_codename: "Sentinel-B",
        action: "validate",
        action_label: "Sentinel-B — Layout Review (18 Rules)",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.explanation || result.verdict || "",
        score: result.total_score,
        approved: result.approved,
        user_flag: userFlag,
        status: "success",
      });
      break;

    case "send_email":
      dbOps.saveAgentAction({
        session_id: sessionId,
        agent_name: "LinkedIn Expert",
        agent_codename: "Herald",
        action: "craft_post",
        action_label: "Herald — Email / LinkedIn Draft",
        stage: stageId,
        execution_order: order++,
        output_json: JSON.stringify(result),
        output_summary: result.document_title || result.headline || "",
        user_flag: userFlag,
        status: "success",
      });
      break;
  }
}

// ── Helper: Get next execution order for a session ──
function getNextExecutionOrder(sessionId: string): number {
  const actions = dbOps.getAgentActions(sessionId);
  if (actions.length === 0) return 1;
  return Math.max(...actions.map((a) => a.execution_order)) + 1;
}

export { getNextExecutionOrder };
