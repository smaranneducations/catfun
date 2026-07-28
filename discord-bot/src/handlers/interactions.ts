/**
 * Interaction handler — routes button clicks, modal submissions,
 * select menus, and slash commands.
 */

import {
  Interaction,
  ButtonInteraction,
  ModalSubmitInteraction,
  StringSelectMenuInteraction,
} from "discord.js";
import {
  handleApproval,
  handleRerun,
  startPipeline,
  updateSetupState,
  handleSetupComplete,
  waitForFileUpload,
  execute as executeAibrief,
} from "../commands/aibrief";
import { execute as executePing } from "../commands/ping";
import dbOps from "../services/database";
import { readFileSync, existsSync } from "fs";
import {
  buildRejectModal,
  buildSetupEmbed,
  buildExecModeSelect,
  buildUrlInputModal,
  buildTextInputModal,
} from "../utils/embeds";
import { getStage, STAGES } from "../utils/stages";
import { publishLinkedIn } from "../services/pipeline-client";

export async function handleInteraction(interaction: Interaction) {
  // ── Slash commands ──
  if (interaction.isChatInputCommand()) {
    const { commandName } = interaction;
    try {
      if (commandName === "aibrief") {
        await executeAibrief(interaction);
      } else if (commandName === "ping") {
        await executePing(interaction);
      }
    } catch (err) {
      console.error(`Error handling command ${commandName}:`, err);
      const msg = { content: "An error occurred.", ephemeral: true };
      if (interaction.deferred || interaction.replied) {
        await interaction.editReply(msg).catch(() => {});
      } else {
        await interaction.reply(msg as any).catch(() => {});
      }
    }
    return;
  }

  // ── Button clicks ──
  if (interaction.isButton()) {
    try {
      await handleButton(interaction);
    } catch (err) {
      console.error("[BUTTON ERROR]", interaction.customId, err);
      if (!interaction.replied && !interaction.deferred) {
        await interaction.reply({ content: "Something went wrong.", ephemeral: true }).catch(() => {});
      }
    }
    return;
  }

  // ── Select menu interactions ──
  if (interaction.isStringSelectMenu()) {
    try {
      await handleSelectMenu(interaction);
    } catch (err) {
      console.error("[SELECT ERROR]", interaction.customId, err);
      if (!interaction.replied && !interaction.deferred) {
        await interaction.reply({ content: "Something went wrong.", ephemeral: true }).catch(() => {});
      }
    }
    return;
  }

  // ── Modal submissions ──
  if (interaction.isModalSubmit()) {
    try {
      await handleModal(interaction);
    } catch (err) {
      console.error("[MODAL ERROR]", interaction.customId, err);
      if (!interaction.replied && !interaction.deferred) {
        await interaction.reply({ content: "Something went wrong.", ephemeral: true }).catch(() => {});
      }
    }
    return;
  }
}

async function handleButton(interaction: ButtonInteraction) {
  const customId = interaction.customId;
  const threadId = interaction.channelId;

  if (!threadId) {
    await interaction.reply({ content: "Could not determine channel.", ephemeral: true });
    return;
  }

  const session = dbOps.getSessionByThread(threadId);

  // ═══════════════════════════════════════════════════════
  //  CATALOG BUTTONS (pre-flight)
  // ═══════════════════════════════════════════════════════

  if (customId === "catalog_trust_all") {
    if (!session) {
      console.log("[CATALOG] Trust All — no session found for thread", threadId);
      await interaction.reply({ content: "Session not found.", ephemeral: true });
      return;
    }
    if (session.user_id !== interaction.user.id) {
      await interaction.reply({ content: "Only the session owner can configure stages.", ephemeral: true });
      return;
    }

    const prefs: Record<string, "trust" | "validate"> = {};
    for (const s of STAGES) {
      prefs[s.id] = "trust";
    }
    dbOps.setBulkPreferences(session.id, prefs);

    // Buttons-only message — deferUpdate is safe (no select menu here)
    await interaction.deferUpdate();
    return;
  }

  if (customId === "catalog_validate_all") {
    if (!session) {
      console.log("[CATALOG] Validate All — no session found for thread", threadId);
      await interaction.reply({ content: "Session not found.", ephemeral: true });
      return;
    }
    if (session.user_id !== interaction.user.id) {
      await interaction.reply({ content: "Only the session owner can configure stages.", ephemeral: true });
      return;
    }

    const prefs: Record<string, "trust" | "validate"> = {};
    for (const s of STAGES) {
      prefs[s.id] = "validate";
    }
    dbOps.setBulkPreferences(session.id, prefs);

    // Buttons-only message — deferUpdate is safe (no select menu here)
    await interaction.deferUpdate();
    return;
  }

  if (customId === "catalog_start") {
    console.log("[CATALOG] Start Pipeline clicked. Thread:", threadId, "Session:", session?.id, "Status:", session?.status);

    // Acknowledge immediately — remove buttons so user sees instant feedback
    await interaction.deferUpdate();

    if (!session) {
      console.log("[CATALOG] ERROR — no session found for thread", threadId);
      await interaction.followUp({ content: "Session not found for this thread.", ephemeral: true });
      return;
    }
    if (session.user_id !== interaction.user.id) {
      await interaction.followUp({ content: "Only the session owner can start the pipeline.", ephemeral: true });
      return;
    }
    if (session.status !== "catalog_review") {
      console.log("[CATALOG] Status is", session.status, "not catalog_review — rejecting");
      await interaction.followUp({ content: `Pipeline already started (status: "${session.status}").`, ephemeral: true });
      return;
    }

    // Remove catalog components and show starting message
    const prefs = dbOps.getPreferences(session.id);
    const fullPrefs: Record<string, "trust" | "validate"> = {};
    for (const s of STAGES) {
      fullPrefs[s.id] = prefs[s.id] || "validate";
    }

    const trustedNames = STAGES.filter(s => fullPrefs[s.id] === "trust").map(s => s.name);
    const trustedCount = trustedNames.length;
    const validateCount = STAGES.length - trustedCount;
    const prefLine = trustedCount > 0
      ? `**Pipeline starting** — ${trustedCount} trusted, ${validateCount} manual. Trusted: ${trustedNames.join(", ")}`
      : `**Pipeline starting** — all ${validateCount} stages require manual approval.`;

    // Edit the original catalog message — remove buttons, show summary
    await interaction.editReply({ content: prefLine, embeds: [], components: [] });

    console.log("[CATALOG] Starting pipeline for session", session.id);

    // Start pipeline — goes straight to first stage
    await startPipeline(threadId);
    return;
  }

  // ═══════════════════════════════════════════════════════
  //  PIPELINE STAGE BUTTONS
  // ═══════════════════════════════════════════════════════

  if (customId.startsWith("approve_")) {
    const stageId = customId.replace("approve_", "");

    if (!session) {
      await interaction.reply({ content: "Session not found for this thread.", ephemeral: true });
      return;
    }

    if (session.user_id !== interaction.user.id) {
      await interaction.reply({
        content: "Only the person who started this brief can approve stages.",
        ephemeral: true,
      });
      return;
    }

    // Remove buttons from the approved message
    await interaction.update({ components: [] });

    const stageDef = getStage(stageId);
    await (interaction.channel as any)?.send(
      `✅ **${interaction.user.displayName}** approved **${stageDef?.name || stageId}** — advancing to next stage.`
    );

    await handleApproval(threadId, stageId);
    return;
  }

  if (customId.startsWith("rerun_")) {
    const stageId = customId.replace("rerun_", "");

    if (!session) {
      await interaction.reply({ content: "Session not found.", ephemeral: true });
      return;
    }

    if (session.user_id !== interaction.user.id) {
      await interaction.reply({
        content: "Only the person who started this brief can re-run stages.",
        ephemeral: true,
      });
      return;
    }

    // Show the structured reject modal
    const modal = buildRejectModal(stageId);
    await interaction.showModal(modal);
    return;
  }

  if (customId === "download_pdf") {
    if (!session) {
      await interaction.reply({ content: "Session not found.", ephemeral: true });
      return;
    }

    await interaction.deferReply({ ephemeral: true });
    try {
      // Try local file first
      if (session.pdf_path && session.pdf_path !== "delivered" && existsSync(session.pdf_path)) {
        const buf = readFileSync(session.pdf_path);
        await interaction.editReply({
          content: "Here's your PDF:",
          files: [{ attachment: buf, name: "AI_Brief.pdf" }],
        });
      } else {
        // Fall back to HTTP download
        const resp = await fetch(
          `${process.env.PYTHON_API_URL || "http://localhost:8900"}/session/${session.api_session_id}/pdf/download`,
          { signal: AbortSignal.timeout(120_000) }
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const buf = Buffer.from(await resp.arrayBuffer());
        await interaction.editReply({
          content: "Here's your PDF:",
          files: [{ attachment: buf, name: "AI_Brief.pdf" }],
        });
      }
    } catch (err: any) {
      await interaction.editReply(`Failed: ${err.message}`);
    }
    return;
  }

  // ── Publish to LinkedIn ──
  if (customId === "post_linkedin") {
    if (!session) {
      await interaction.reply({ content: "Session not found.", ephemeral: true });
      return;
    }
    if (session.user_id !== interaction.user.id) {
      await interaction.reply({
        content: "Only the person who started this brief can publish to LinkedIn.",
        ephemeral: true,
      });
      return;
    }

    await interaction.deferReply({ ephemeral: true });
    try {
      // Pull the draft generated in the send_email stage.
      const sendEmailAction = dbOps.getAgentAction(
        session.id, "send_email", null, "craft_post", 1
      );

      let postText = "";
      let documentTitle = "";
      if (sendEmailAction?.output_json) {
        try {
          const output = JSON.parse(sendEmailAction.output_json);
          postText = output.post_text || "";
          documentTitle = output.document_title || "";
        } catch {
          // Leave empty and let backend craft fallback text.
        }
      }

      const publishResult = await publishLinkedIn(session.api_session_id, {
        post_text: postText,
        document_title: documentTitle,
        pdf_path: session.pdf_path || "",
        story: {
          headline: session.headline || "",
          publisher: session.publisher || "",
          news_url: session.source_url || "",
        },
      });

      const status = publishResult.status || "unknown";
      dbOps.saveStageRun({
        session_id: session.id,
        stage_id: "linkedin_publish",
        status: status === "success" ? "success" : "error",
        output_json: JSON.stringify(publishResult),
        duration_sec: 0,
        error: publishResult.error,
      });

      if (status === "success") {
        await interaction.editReply(
          `Posted to LinkedIn successfully.\n${publishResult.url ? `URL: ${publishResult.url}` : ""}`
        );
      } else {
        await interaction.editReply(
          `LinkedIn publish failed: ${publishResult.error || "Unknown error"}`
        );
      }
    } catch (err: any) {
      await interaction.editReply(`LinkedIn publish failed: ${err.message}`);
    }
    return;
  }
}

// ═══════════════════════════════════════════════════════════════
//  SELECT MENU HANDLER
// ═══════════════════════════════════════════════════════════════

async function handleSelectMenu(interaction: StringSelectMenuInteraction) {
  const customId = interaction.customId;
  const channelId = interaction.channelId;

  if (!channelId) {
    await interaction.reply({ content: "Could not determine channel.", ephemeral: true });
    return;
  }

  // ── Input method selection → immediately ask for content ──
  if (customId === "setup_input_method") {
    const value = interaction.values[0] as "url" | "text" | "file";
    updateSetupState(interaction.user.id, channelId, { inputMethod: value });

    if (value === "url") {
      const modal = buildUrlInputModal();
      await interaction.showModal(modal);
      return;
    }

    if (value === "text") {
      const modal = buildTextInputModal();
      await interaction.showModal(modal);
      return;
    }

    if (value === "file") {
      await interaction.update({ components: [] });
      const pages = 4;
      updateSetupState(interaction.user.id, channelId, { pages });
      await waitForFileUpload(interaction.user.id, channelId, pages);
      return;
    }
    return;
  }

  // ── Execution mode selection → proceed directly ──
  if (customId === "setup_exec_mode") {
    const value = interaction.values[0] as "autonomous" | "human";
    const state = updateSetupState(interaction.user.id, channelId, { execMode: value });

    // Remove the select menu
    await interaction.update({ components: [] });

    // Proceed directly — we have everything we need
    await handleSetupComplete(
      interaction.user.id,
      channelId,
      state.sourceUrl || "",
      state.sourceText || "",
      state.pages || 4
    );
    return;
  }

  // ── Trust stage selection ──
  if (customId === "trust_stages") {
    const session = dbOps.getSessionByThread(channelId);
    if (!session) {
      await interaction.reply({ content: "Session not found.", ephemeral: true });
      return;
    }

    if (session.user_id !== interaction.user.id) {
      await interaction.reply({ content: "Only the session owner can configure stages.", ephemeral: true });
      return;
    }

    // Selected values = trusted stages, everything else = validate
    const trustedStageIds = interaction.values;
    const prefs: Record<string, "trust" | "validate"> = {};
    for (const s of STAGES) {
      prefs[s.id] = trustedStageIds.includes(s.id) ? "trust" : "validate";
    }
    dbOps.setBulkPreferences(session.id, prefs);

    // Dropdown-only message — deferUpdate is safe (no buttons here)
    await interaction.deferUpdate();
    return;
  }
}

async function handleModal(interaction: ModalSubmitInteraction) {
  const customId = interaction.customId;
  const channelId = interaction.channelId;

  if (!channelId) {
    await interaction.reply({ content: "Could not determine channel.", ephemeral: true });
    return;
  }

  // ═══════════════════════════════════════════════════════
  //  SETUP MODALS (no session yet)
  // ═══════════════════════════════════════════════════════

  if (customId === "modal_setup_url") {
    const url = interaction.fields.getTextInputValue("setup_url") ?? "";
    const pagesStr = interaction.fields.getTextInputValue("setup_pages") ?? "4";
    const pages = Math.min(6, Math.max(2, parseInt(pagesStr, 10) || 4));

    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      await interaction.reply({
        content: "Please provide a valid URL starting with `http://` or `https://`.",
        ephemeral: true,
      });
      return;
    }

    // Save content to setup state
    updateSetupState(interaction.user.id, channelId, {
      sourceUrl: url,
      pages,
    });

    // Show execution mode select
    const contentEmbed = buildSetupEmbed("content_received", {
      contentSummary: url.slice(0, 100),
    });
    const modeSelect = buildExecModeSelect();

    await interaction.reply({
      embeds: [contentEmbed],
      components: [modeSelect],
    });
    return;
  }

  if (customId === "modal_setup_text") {
    const text = interaction.fields.getTextInputValue("setup_text") ?? "";
    const pagesStr = interaction.fields.getTextInputValue("setup_pages") ?? "4";
    const pages = Math.min(6, Math.max(2, parseInt(pagesStr, 10) || 4));

    if (text.length < 20) {
      await interaction.reply({
        content: "Please provide at least 20 characters of content.",
        ephemeral: true,
      });
      return;
    }

    // Save content to setup state
    updateSetupState(interaction.user.id, channelId, {
      sourceText: text,
      pages,
    });

    // Show execution mode select
    const contentEmbed = buildSetupEmbed("content_received", {
      contentSummary: text.slice(0, 80) + (text.length > 80 ? "..." : ""),
    });
    const modeSelect = buildExecModeSelect();

    await interaction.reply({
      embeds: [contentEmbed],
      components: [modeSelect],
    });
    return;
  }

  // ═══════════════════════════════════════════════════════
  //  PIPELINE MODALS (session required)
  // ═══════════════════════════════════════════════════════

  const session = dbOps.getSessionByThread(channelId);
  if (!session) {
    await interaction.reply({ content: "Session not found.", ephemeral: true });
    return;
  }

  // ── Structured reject modal → saves feedback and re-runs the stage ──
  if (customId.startsWith("modal_reject_")) {
    const stageId = customId.replace("modal_reject_", "");

    const issueType = interaction.fields.getTextInputValue("reject_issue_type") ?? "";
    const whatIsWrong = interaction.fields.getTextInputValue("reject_what_wrong") ?? "";
    const whatToFocus = interaction.fields.getTextInputValue("reject_focus") ?? "";

    // Build a combined comment from the structured feedback
    const parts: string[] = [];
    if (issueType) parts.push(`[Issue: ${issueType}]`);
    if (whatIsWrong) parts.push(`Problem: ${whatIsWrong}`);
    if (whatToFocus) parts.push(`Focus on: ${whatToFocus}`);
    const combinedComment = parts.join(" | ");

    // For analyst_pairs sub-steps: store comment under perspective-specific key
    let commentStageId = stageId;
    if (stageId === "analyst_pairs" && session.sub_step !== null && session.sub_step !== undefined) {
      const perspectives = ["historical", "economic", "social", "future"];
      commentStageId = `analyst_${perspectives[session.sub_step] || "historical"}`;
    }

    dbOps.addComment({
      session_id: session.id,
      stage_id: commentStageId,
      user_id: interaction.user.id,
      user_name: interaction.user.displayName,
      content: combinedComment,
      weight: 5.0,
      action: "reject",
    });

    const stageDef = getStage(stageId);

    await interaction.reply({
      content:
        `**Re-running ${stageDef?.name || stageId}** with your structured feedback:\n\n` +
        `> **Issue:** ${issueType}\n` +
        `> **Problem:** ${whatIsWrong}\n` +
        (whatToFocus ? `> **Focus on:** ${whatToFocus}\n` : "") +
        `\n*Your feedback is weighted **5×** over agent input. Re-running now...*`,
    });

    // Pass the user's structured feedback so the wrapper can inject it into the API call
    await handleRerun(channelId, stageId, [combinedComment]);
    return;
  }

}
