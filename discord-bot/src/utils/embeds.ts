import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  StringSelectMenuBuilder,
  StringSelectMenuOptionBuilder,
} from "discord.js";
import { StageDefinition, STAGES, getStageIndex } from "./stages";

/**
 * Build the progress bar string showing all stages.
 */
export function buildProgressBar(currentStageId: string): string {
  const currentIdx = getStageIndex(currentStageId);
  return STAGES.map((_, i) =>
    i < currentIdx ? "✅" : i === currentIdx ? "⭐" : "·"
  ).join("");
}

/**
 * Build a rich embed for a pipeline stage result.
 */
export function buildStageEmbed(
  stage: StageDefinition,
  result: Record<string, any>,
  userComments: string[] = []
): EmbedBuilder {
  const progressBar = buildProgressBar(stage.id);

  const embed = new EmbedBuilder()
    .setColor(stage.color)
    .setTitle(`Phase ${stage.phase_number} — ${stage.name}`)
    .setDescription(stage.description)
    .setFooter({ text: `Agent: ${stage.agent} | ${progressBar}` })
    .setTimestamp();

  // Add result fields based on stage type
  const fields = extractStageFields(stage.id, result);
  for (const field of fields) {
    embed.addFields(field);
  }

  // Show user input if any
  if (userComments.length > 0) {
    const commentText = userComments.map((c) => `> ${c}`).join("\n");
    embed.addFields({
      name: "Your Input (5x weight)",
      value: commentText.length > 1020 ? commentText.slice(0, 1020) + "…" : commentText,
      inline: false,
    });
  }

  return embed;
}

/**
 * Build the "running" embed shown while a stage is executing.
 */
export function buildRunningEmbed(stage: StageDefinition): EmbedBuilder {
  const progressBar = buildProgressBar(stage.id);

  return new EmbedBuilder()
    .setColor(0xf1c40f)
    .setTitle(`Phase ${stage.phase_number} — ${stage.name}`)
    .setDescription(
      `**Running...** ${stage.description}\n\n` +
      `Agent **${stage.agent}** is working on this stage.`
    )
    .setFooter({ text: `Agent: ${stage.agent} | ${progressBar}` })
    .setTimestamp();
}

/**
 * Build the completion embed with PDF info.
 */
export function buildCompleteEmbed(result: Record<string, any>): EmbedBuilder {
  const score = result.combined_score || result.validation_score || "?";
  const topic = result.headline || result.topic || "AI Brief";
  const duration = result.duration_seconds
    ? `${Math.round(result.duration_seconds)}s`
    : "?";

  return new EmbedBuilder()
    .setColor(0x2ecc71)
    .setTitle("Brief Complete!")
    .setDescription(`**${topic}**`)
    .addFields(
      { name: "Score", value: `${score}/100`, inline: true },
      { name: "Duration", value: duration, inline: true }
    )
    .setFooter({ text: "AI Brief • Download your PDF below" })
    .setTimestamp();
}

/**
 * Build the PDF delivery embed — shown immediately after PDF generation.
 */
export function buildPdfDeliveryEmbed(result: Record<string, any>): EmbedBuilder {
  return new EmbedBuilder()
    .setColor(0x2ecc71)
    .setTitle("Your PDF is Ready!")
    .setDescription(
      "PDF has been generated and is attached below.\n" +
      "The pipeline will continue with an informational layout review."
    )
    .addFields(
      { name: "Size", value: `${result.pdf_size_kb || "?"}KB`, inline: true },
      { name: "Status", value: "✅ Generated", inline: true }
    )
    .setTimestamp();
}

/**
 * Build the approval button row for a stage.
 */
export function buildApprovalButtons(
  stageId: string
): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`approve_${stageId}`)
      .setLabel("Approve & Continue")
      .setStyle(ButtonStyle.Success),
    new ButtonBuilder()
      .setCustomId(`rerun_${stageId}`)
      .setLabel("Re-run")
      .setStyle(ButtonStyle.Danger)
  );
}

/**
 * Extract display fields from stage results based on stage type.
 * Returns RICH, detailed fields — NOT summaries.
 */
function extractStageFields(
  stageId: string,
  result: Record<string, any>
): { name: string; value: string; inline: boolean }[] {
  const fields: { name: string; value: string; inline: boolean }[] = [];

  switch (stageId) {
    case "content_extraction": {
      fields.push(
        { name: "Headline", value: truncate(result.headline, 256) || "?", inline: false },
        { name: "Publisher", value: result.publisher || "?", inline: true },
        { name: "Content", value: `${result.content_length || 0} chars`, inline: true },
        { name: "Status", value: result.status === "extracted" ? "✅ Full extraction" : "Partial", inline: true }
      );
      if (result.description) {
        fields.push({
          name: "Summary",
          value: truncate(result.description, 500),
          inline: false,
        });
      }
      if (result.article_text_preview) {
        fields.push({
          name: "Content Preview",
          value: truncate(result.article_text_preview, 300),
          inline: false,
        });
      }
      if (result.cached_run_id) {
        fields.push({
          name: "Cache",
          value: `Previously processed (run: ${result.cached_run_id})`,
          inline: false,
        });
      }
      break;
    }

    case "design_dna": {
      fields.push(
        { name: "Emotion", value: result.emotion || "?", inline: true },
        { name: "Style", value: result.style_id || "?", inline: true },
        { name: "Design", value: result.design_name || "?", inline: true },
        { name: "Palette", value: result.palette_id || "?", inline: true },
        { name: "Font", value: result.font_id || "?", inline: true },
        { name: "Imagen", value: result.imagen_style || "?", inline: true }
      );
      if (result.emotion_reasoning) {
        fields.push({
          name: "Emotion Reasoning",
          value: truncate(result.emotion_reasoning, 400),
          inline: false,
        });
      }
      if (result.primary_color) {
        const colors = [
          result.primary_color, result.secondary_color, result.accent_color
        ].filter(Boolean).join(" / ");
        fields.push({ name: "Colors", value: colors, inline: true });
      }
      if (result.visual_motif) {
        fields.push({ name: "Visual Motif", value: truncate(result.visual_motif, 200), inline: true });
      }
      break;
    }

    case "analyst_pairs": {
      // Show perspective summaries (full debate conversations posted as separate messages)
      if (result.perspectives) {
        for (const [key, data] of Object.entries(result.perspectives as Record<string, any>)) {
          const d = data as any;
          const title = d.perspective_title || key;
          const confidence = d.confidence ? ` (confidence: ${d.confidence}/10)` : "";
          const pullQuote = d.pull_quote ? `\n> *"${truncate(d.pull_quote, 200)}"*` : "";
          const args = (d.key_arguments || []).slice(0, 4).map((a: string) => `• ${a}`).join("\n");
          const value = `${confidence}${pullQuote}\n${args || "No key arguments captured"}`;
          fields.push({ name: `${key.toUpperCase()} — ${truncate(title, 80)}`, value: truncate(value, 1020), inline: false });
        }
      }

      // Show final scores per debate
      if (result.full_debates?.length > 0) {
        const scoreLines = result.full_debates.map((d: any) =>
          `${d.final_approved ? "✅" : "❌"} **${(d.label || "?").toUpperCase()}** — ${d.preparer_name} vs ${d.reviewer_name}: **${d.final_score}/10** (${d.total_rounds} rounds)`
        ).join("\n");
        fields.push({
          name: "Debate Results",
          value: truncate(scoreLines, 1020),
          inline: false,
        });
      }

      // Stats
      fields.push({
        name: "Debate Stats",
        value: `${result.analyst_count || "?"} perspectives • ${result.total_debate_rounds || "?"} debate rounds\n*Full debate conversations posted above*`,
        inline: false,
      });
      break;
    }

    case "round_table": {
      fields.push(
        { name: "Perspectives Updated", value: `${result.perspectives_updated || "?"}`, inline: true },
        { name: "Cross-challenges", value: `${result.cross_challenges || 0}`, inline: true }
      );
      if (result.challenge_highlights?.length > 0) {
        let challengeText = "";
        for (const c of result.challenge_highlights) {
          // Handle both string and object formats
          const pair = typeof c === "object" ? (c.pair || c.challenger || "?") : String(c);
          const summary = typeof c === "object"
            ? (c.summary || c.impact || JSON.stringify(c).replace(/[{}'"]/g, ""))
            : String(c);
          challengeText += `• **${truncate(String(pair), 60)}**: ${truncate(String(summary), 200)}\n`;
          if (typeof c === "object" && c.impact && c.summary) {
            challengeText += `  Impact: ${truncate(c.impact, 150)}\n`;
          }
        }
        fields.push({ name: "Cross-Challenges", value: truncate(challengeText, 1020) || "None", inline: false });
      }
      // Show updated perspective confidence
      if (result.perspectives_after) {
        const perspLines = Object.entries(result.perspectives_after as Record<string, any>)
          .map(([key, data]) => {
            const d = data as any;
            return `• **${key.toUpperCase()}**: ${truncate(d.perspective_title || key, 80)} (confidence: ${d.confidence || "?"}/10)`;
          })
          .join("\n");
        if (perspLines) {
          fields.push({ name: "Updated Perspectives", value: truncate(perspLines, 1020), inline: false });
        }
      }
      break;
    }

    case "editorial": {
      fields.push(
        { name: "Quality Score", value: `**${result.quality_score || "?"}/10**`, inline: true },
        { name: "Ready", value: result.ready_for_synthesis ? "✅ Yes" : "Revisions needed", inline: true }
      );
      if (result.overall_assessment) {
        fields.push({
          name: "Overall Assessment",
          value: truncate(result.overall_assessment, 1020),
          inline: false,
        });
      }
      if (result.verdict) {
        fields.push({ name: "Verdict", value: truncate(result.verdict, 1020), inline: false });
      }
      if (result.revisions_requested?.length > 0) {
        fields.push({
          name: "Revisions Requested",
          value: truncate(result.revisions_requested.map((r: string) => `• ${r}`).join("\n"), 1020),
          inline: false,
        });
      }
      if (result.missing_angles?.length > 0) {
        fields.push({
          name: "Missing Angles",
          value: truncate(result.missing_angles.map((a: string) => `• ${a}`).join("\n"), 1020),
          inline: false,
        });
      }
      // Per-agent feedback (detailed — full justification)
      if (result.feedback_per_agent) {
        for (const [agent, feedback] of Object.entries(result.feedback_per_agent as Record<string, any>)) {
          const fb = feedback as any;
          let agentText = "";
          if (fb.score != null) agentText += `Score: **${fb.score}/10**\n`;
          if (fb.verdict) agentText += `**Verdict**: ${fb.verdict}\n`;
          if (fb.feedback) agentText += `${fb.feedback}\n`;
          if (fb.strengths?.length > 0) {
            agentText += `✅ **Strengths**:\n${fb.strengths.map((s: string) => `  • ${s}`).join("\n")}\n`;
          }
          if (fb.improvements?.length > 0) {
            agentText += `**Improvements needed**:\n${fb.improvements.map((i: string) => `  • ${i}`).join("\n")}\n`;
          }
          if (agentText) {
            fields.push({ name: `${agent}`, value: truncate(agentText, 1020), inline: false });
          }
        }
      }
      break;
    }

    case "content_synthesis": {
      fields.push({
        name: "Brief Title",
        value: `**${result.brief_title || "?"}**`,
        inline: false,
      });
      if (result.subtitle) {
        fields.push({ name: "Subtitle", value: truncate(result.subtitle, 200), inline: false });
      }
      if (result.pages?.length > 0) {
        for (const p of result.pages) {
          let pageText = "";
          if (p.hero_statement) pageText += `**${truncate(p.hero_statement, 120)}**\n`;
          if (p.supporting_line) pageText += `${truncate(p.supporting_line, 120)}\n`;
          if (p.summary_points?.length > 0) {
            pageText += p.summary_points.slice(0, 4).map((s: string) => `• ${truncate(s, 80)}`).join("\n") + "\n";
          }
          if (p.points?.length > 0) {
            pageText += p.points.slice(0, 4).map((pt: any) => {
              const point = pt.point || "";
              const detail = pt.detail ? ` — ${pt.detail}` : "";
              return `• **${truncate(point, 60)}**${truncate(detail, 80)}`;
            }).join("\n") + "\n";
          }
          if (p.quote) pageText += `> *"${truncate(p.quote, 150)}"*\n— ${p.attribution || "?"}\n`;
          if (p.hero_number) pageText += `**${p.hero_number}** — ${p.hero_label || ""}\n`;
          if (p.visual_mood) pageText += `Mood: ${p.visual_mood}\n`;

          fields.push({
            name: `${(p.page_type || "?").toUpperCase()}${p.page_title ? ` — ${truncate(p.page_title, 50)}` : ""}`,
            value: truncate(pageText, 1020) || "Page content",
            inline: false,
          });
        }
      }
      fields.push({
        name: "Total Pages",
        value: `${result.page_count || "?"} pages`,
        inline: true,
      });
      break;
    }

    case "neutrality_check": {
      fields.push(
        { name: "Approved", value: result.approved ? "✅ Passed" : "Issues Found", inline: true },
        { name: "Tone Score", value: `**${result.tone_score || "?"}/10**`, inline: true },
        { name: "Revision Required", value: result.revision_required ? "Yes" : "No", inline: true }
      );
      if (result.issues?.length > 0) {
        let issueText = "";
        for (const iss of result.issues) {
          issueText += `• **${iss.page_type || "?"}** [${iss.severity || "?"}]: ${truncate(iss.issue, 200)}\n`;
          if (iss.fix) issueText += `  Fix: ${truncate(iss.fix, 150)}\n`;
        }
        fields.push({ name: "Issues Found", value: truncate(issueText, 1020), inline: false });
      }
      if (result.strengths?.length > 0) {
        fields.push({
          name: "✅ Strengths",
          value: result.strengths.slice(0, 4).map((s: string) => `• ${truncate(s, 120)}`).join("\n"),
          inline: false,
        });
      }
      if (result.verdict) {
        fields.push({ name: "Verdict", value: truncate(result.verdict, 500), inline: false });
      }
      break;
    }

    case "discussion_potential": {
      fields.push(
        { name: "Engagement Score", value: `**${result.engagement_score ?? "?"}/100**`, inline: true },
        { name: "Verdict", value: result.verdict || "?", inline: true }
      );
      if (result.controversy_score != null) {
        fields.push({ name: "Controversy", value: `${result.controversy_score}/100`, inline: true });
      }
      if (result.relevance_score != null) {
        fields.push({ name: "Relevance", value: `${result.relevance_score}/100`, inline: true });
      }
      if (result.shareability_score != null) {
        fields.push({ name: "Shareability", value: `${result.shareability_score}/100`, inline: true });
      }
      if (result.discussion_hooks?.length > 0) {
        const hooks = result.discussion_hooks
          .map((h: string, i: number) => `${i + 1}. ${truncate(h, 150)}`)
          .join("\n");
        fields.push({ name: "Discussion Hooks", value: truncate(hooks, 1020), inline: false });
      }
      if (result.reasoning) {
        fields.push({ name: "Reasoning", value: truncate(result.reasoning, 800), inline: false });
      }
      if (result.suggested_angle) {
        fields.push({ name: "Suggested Angle", value: truncate(result.suggested_angle, 300), inline: false });
      }
      break;
    }

    case "pre_validation": {
      fields.push(
        { name: "Score", value: `**${result.total_score ?? "?"}/100**`, inline: true },
        { name: "Approved", value: result.approved ? "✅ Yes" : "❌ No", inline: true }
      );
      if (result.verdict) {
        fields.push({ name: "Verdict", value: truncate(result.verdict, 500), inline: false });
      }
      if (result.explanation) {
        fields.push({ name: "Explanation", value: truncate(result.explanation, 800), inline: false });
      }
      if (result.critical_failures?.length > 0) {
        fields.push({
          name: "❌ Critical Issues",
          value: result.critical_failures.map((f: string) => `• ${truncate(f, 150)}`).join("\n"),
          inline: false,
        });
      }
      if (result.fix_instructions?.length > 0) {
        fields.push({
          name: "Fix Instructions",
          value: result.fix_instructions.map((f: string) => `• ${truncate(f, 150)}`).join("\n"),
          inline: false,
        });
      }
      if (result.rules_checked?.length > 0) {
        const rulesText = result.rules_checked
          .map((r: any) => `${r.passed ? "✅" : "❌"} **${r.id || "?"}**: ${truncate(r.reasoning || "", 100)}`)
          .join("\n");
        fields.push({ name: "Rules Checked", value: truncate(rulesText, 1020), inline: false });
      }
      break;
    }

    case "visuals": {
      fields.push({
        name: "Images Generated",
        value: `**${result.visual_count || "?"}** visual elements`,
        inline: true,
      });
      if (result.types?.length > 0) {
        fields.push({
          name: "Types",
          value: result.types.join(", "),
          inline: false,
        });
      }
      break;
    }

    case "pdf_generation": {
      fields.push(
        { name: "Status", value: result.pdf_exists ? "✅ Generated" : "❌ Failed", inline: true },
        { name: "Size", value: `${result.pdf_size_kb || "?"}KB`, inline: true }
      );
      break;
    }

    case "post_validation": {
      fields.push(
        { name: "Layout Score", value: `**${result.total_score ?? "?"}/100**`, inline: true },
        { name: "Combined Score", value: `**${result.combined_score ?? "?"}/100**`, inline: true },
        { name: "Pre-Visual", value: `${result.pre_visual_score ?? "?"}/100`, inline: true },
        { name: "Post-Visual", value: `${result.total_score ?? "?"}/100`, inline: true }
      );
      if (result.verdict) {
        fields.push({ name: "Verdict", value: truncate(result.verdict, 500), inline: false });
      }
      if (result.explanation) {
        fields.push({ name: "Explanation", value: truncate(result.explanation, 800), inline: false });
      }
      if (result.critical_failures?.length > 0) {
        fields.push({
          name: "Issues",
          value: result.critical_failures.map((f: string) => `• ${truncate(f, 150)}`).join("\n"),
          inline: false,
        });
      }
      if (result.fix_instructions?.length > 0) {
        fields.push({
          name: "Fix Suggestions",
          value: result.fix_instructions.map((f: string) => `• ${truncate(f, 150)}`).join("\n"),
          inline: false,
        });
      }
      if (result.rules_checked?.length > 0) {
        const rulesText = result.rules_checked
          .map((r: any) => `${r.passed ? "✅" : "❌"} **${r.id || "?"}**: ${truncate(r.reasoning || "", 100)}`)
          .join("\n");
        fields.push({ name: "Rules Checked", value: truncate(rulesText, 1020), inline: false });
      }
      fields.push({
        name: "Note",
        value: "*This is informational only — your PDF has already been delivered above.*",
        inline: false,
      });
      break;
    }

    default: {
      for (const [key, val] of Object.entries(result).slice(0, 8)) {
        if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
          fields.push({ name: key, value: truncate(String(val), 300), inline: true });
        }
      }
    }
  }

  return fields;
}

/**
 * Build a rich embed for a single debate — full conversation, no truncation.
 * Uses embed description (4096 char limit) instead of fields (1024 char limit).
 */
export function buildDebateTurnEmbed(debate: any): EmbedBuilder {
  const label = (debate.label || "?").toUpperCase();
  const scoreIcon = debate.final_approved ? "✅" : "❌";

  let desc = `**${debate.preparer_name}** (Analyst) vs **${debate.reviewer_name}** (Reviewer)\n`;
  desc += `Final Score: **${debate.final_score}/10** ${scoreIcon} — ${debate.total_rounds} round(s)\n`;
  desc += `───────────────────────────────\n`;

  for (const round of debate.rounds || []) {
    desc += `\n### Round ${round.round}\n`;

    // ── Preparer submission ──
    const prep = round.preparer_submission || {};
    desc += `**${debate.preparer_name}** submits:\n`;
    if (prep.perspective_title || prep.title) {
      desc += `> **"${prep.perspective_title || prep.title}"**\n`;
    }
    if (prep.key_insight) {
      desc += `> ${prep.key_insight}\n`;
    }
    if (prep.pull_quote) {
      desc += `> *"${prep.pull_quote}"*\n`;
    }
    if (prep.confidence) {
      desc += `> Confidence: ${prep.confidence}/10\n`;
    }

    // Key arguments
    const args = prep.key_arguments || prep.economic_impact || prep.historical_parallels || prep.social_impact || [];
    if (Array.isArray(args) && args.length > 0) {
      desc += `> Key arguments:\n`;
      for (const arg of args.slice(0, 5)) {
        if (typeof arg === "object") {
          const text = arg.connection || arg.event || arg.point || JSON.stringify(arg);
          desc += `>  • ${truncate(String(text), 200)}\n`;
        } else {
          desc += `>  • ${truncate(String(arg), 200)}\n`;
        }
      }
    }

    // Other analyst fields — extract readable text from nested objects
    for (const key of ["historical_parallels", "economic_impact", "social_impact",
                        "prediction_6mo", "prediction_2yr", "prediction_5yr",
                        "winners", "losers", "who_is_affected",
                        "opportunity", "risk", "wildcard", "market_signal"]) {
      const val = prep[key];
      if (!val) continue;
      const fieldLabel = key.replace(/_/g, " ");
      if (typeof val === "string") {
        desc += `> **${fieldLabel}**: ${truncate(val, 250)}\n`;
      } else if (Array.isArray(val) && val.length > 0) {
        desc += `> **${fieldLabel}**:\n`;
        for (const item of val.slice(0, 4)) {
          if (typeof item === "object" && item !== null) {
            // Extract readable text from known keys
            const text = item.connection || item.event || item.point || item.impact
              || item.trend || item.name || item.description || item.who || item.what
              || Object.values(item).filter(v => typeof v === "string").slice(0, 2).join(" — ")
              || JSON.stringify(item);
            desc += `>  • ${truncate(String(text), 200)}\n`;
          } else {
            desc += `>  • ${truncate(String(item), 200)}\n`;
          }
        }
      }
    }

    // ── Reviewer feedback ──
    const rev = round.reviewer_feedback || {};
    desc += `\n**${debate.reviewer_name}** reviews: Score **${round.score}/10** ${round.approved ? "✅ Approved" : "❌ Needs revision"}\n`;
    if (rev.verdict || round.verdict) {
      desc += `> **Verdict**: ${rev.verdict || round.verdict}\n`;
    }
    if (rev.strengths?.length > 0) {
      desc += `> ✅ **Strengths**: ${rev.strengths.map((s: string) => truncate(s, 150)).join("; ")}\n`;
    }
    if (rev.weaknesses?.length > 0) {
      desc += `> **Weaknesses**: ${rev.weaknesses.map((w: string) => truncate(w, 150)).join("; ")}\n`;
    }
    if (round.demands?.length > 0) {
      desc += `> **Demands**: ${round.demands.map((d: string) => truncate(d, 150)).join("; ")}\n`;
    }
    if (rev.feedback) {
      desc += `> ${truncate(rev.feedback, 300)}\n`;
    }

    // ── Preparer revision (if any) ──
    if (round.preparer_revision) {
      const rev2 = round.preparer_revision;
      desc += `\n**${debate.preparer_name}** revises:\n`;
      if (rev2.perspective_title || rev2.title) {
        desc += `> **"${rev2.perspective_title || rev2.title}"**\n`;
      }
      if (rev2.key_insight) {
        desc += `> ${truncate(rev2.key_insight, 200)}\n`;
      }
      if (rev2.key_arguments?.length > 0) {
        desc += `> Updated arguments: ${rev2.key_arguments.length} points\n`;
        for (const arg of rev2.key_arguments.slice(0, 3)) {
          desc += `>  • ${truncate(typeof arg === "object" ? JSON.stringify(arg) : String(arg), 150)}\n`;
        }
      }
    }
  }

  // Trim to Discord's 4096 char description limit
  if (desc.length > 4090) {
    desc = desc.slice(0, 4085) + "\n…";
  }

  return new EmbedBuilder()
    .setColor(debate.final_approved ? 0x2ecc71 : 0xe67e22)
    .setTitle(`${label} — Analyst Debate`)
    .setDescription(desc)
    .setTimestamp();
}

function truncate(s: string | undefined | null, max: number): string {
  if (!s) return "";
  return s.length > max ? s.slice(0, max) + "…" : s;
}

// ═════════════════════════════════════════════════════════════════
//  SETUP FORM  (input method + execution mode)
// ═════════════════════════════════════════════════════════════════

/**
 * Build the initial setup embed shown when /aibrief is invoked.
 * Displays current selections for input method and execution mode.
 */
export function buildSetupEmbed(
  step: "input" | "content_received" | "exec_mode",
  opts?: { inputMethod?: string; contentSummary?: string }
): EmbedBuilder {
  const embed = new EmbedBuilder()
    .setColor(0x5865f2)
    .setTitle("AI Brief — Setup")
    .setFooter({ text: "AI Brief • Multi-Agent AI System" })
    .setTimestamp();

  if (step === "input") {
    embed.setDescription(
      "Welcome to **AI Brief** — a multi-agent content pipeline.\n\n" +
      "**How do you want to provide your content?**"
    );
  } else if (step === "content_received") {
    embed.setDescription(
      `✅ **Content received!**\n` +
      (opts?.contentSummary ? `> ${opts.contentSummary}\n\n` : "\n") +
      "**How do you want to run the pipeline?**"
    );
  }

  return embed;
}

/**
 * Input method select menu: URL / Paste Text / Upload File
 */
export function buildInputMethodSelect(): ActionRowBuilder<StringSelectMenuBuilder> {
  const select = new StringSelectMenuBuilder()
    .setCustomId("setup_input_method")
    .setPlaceholder("How do you want to provide content?")
    .addOptions(
      new StringSelectMenuOptionBuilder()
        .setLabel("URL")
        .setDescription("Provide a link to an article or webpage")
        .setValue("url"),
      new StringSelectMenuOptionBuilder()
        .setLabel("Paste Text")
        .setDescription("Copy-paste raw text content directly")
        .setValue("text"),
      new StringSelectMenuOptionBuilder()
        .setLabel("Upload File")
        .setDescription("Attach a text or document file")
        .setValue("file")
    );

  return new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(select);
}

/**
 * Execution mode select menu: Autonomous / Human Control
 */
export function buildExecModeSelect(): ActionRowBuilder<StringSelectMenuBuilder> {
  const select = new StringSelectMenuBuilder()
    .setCustomId("setup_exec_mode")
    .setPlaceholder("How do you want to run the pipeline?")
    .addOptions(
      new StringSelectMenuOptionBuilder()
        .setLabel("Fully Autonomous")
        .setDescription("Trust all agents — pipeline runs to completion without stopping")
        .setValue("autonomous"),
      new StringSelectMenuOptionBuilder()
        .setLabel("Human Control")
        .setDescription("Review each stage, approve or reject with feedback")
        .setValue("human")
    );

  return new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(select);
}

/**
 * Modal for URL input + page count.
 */
export function buildUrlInputModal(): ModalBuilder {
  const urlField = new TextInputBuilder()
    .setCustomId("setup_url")
    .setLabel("Article URL")
    .setStyle(TextInputStyle.Short)
    .setPlaceholder("https://example.com/article")
    .setRequired(true);

  const pagesField = new TextInputBuilder()
    .setCustomId("setup_pages")
    .setLabel("Content pages (2–6, default 4)")
    .setStyle(TextInputStyle.Short)
    .setPlaceholder("4")
    .setRequired(false)
    .setMaxLength(1);

  return new ModalBuilder()
    .setCustomId("modal_setup_url")
    .setTitle("Enter Article URL")
    .addComponents(
      new ActionRowBuilder<TextInputBuilder>().addComponents(urlField),
      new ActionRowBuilder<TextInputBuilder>().addComponents(pagesField)
    );
}

/**
 * Modal for pasting raw text + page count.
 */
export function buildTextInputModal(): ModalBuilder {
  const textField = new TextInputBuilder()
    .setCustomId("setup_text")
    .setLabel("Paste your content")
    .setStyle(TextInputStyle.Paragraph)
    .setPlaceholder("Paste article text, research notes, or any content here...")
    .setRequired(true)
    .setMaxLength(4000);

  const pagesField = new TextInputBuilder()
    .setCustomId("setup_pages")
    .setLabel("Content pages (2–6, default 4)")
    .setStyle(TextInputStyle.Short)
    .setPlaceholder("4")
    .setRequired(false)
    .setMaxLength(1);

  return new ModalBuilder()
    .setCustomId("modal_setup_text")
    .setTitle("Paste Your Content")
    .addComponents(
      new ActionRowBuilder<TextInputBuilder>().addComponents(textField),
      new ActionRowBuilder<TextInputBuilder>().addComponents(pagesField)
    );
}

/**
 * Embed asking the user to upload a file.
 */
export function buildFileUploadEmbed(): EmbedBuilder {
  return new EmbedBuilder()
    .setColor(0x3498db)
    .setTitle("Upload Your File")
    .setDescription(
      "Please **upload a file** as your next message in this channel.\n\n" +
      "Supported: `.txt`, `.md`, `.csv`, `.json`, or any plain-text file.\n" +
      "The bot will read the file content and use it as input.\n\n" +
      "*Waiting for your upload...*"
    )
    .setFooter({ text: "Tip: You can also drag-and-drop a file into this chat" })
    .setTimestamp();
}

// ═════════════════════════════════════════════════════════════════
//  PRE-FLIGHT CATALOG
// ═════════════════════════════════════════════════════════════════

/**
 * Build the pre-flight catalog embed showing all stages, agents, and descriptions.
 */
export function buildCatalogEmbed(url: string, pages: number): EmbedBuilder {
  const stageList = STAGES.map((s) =>
    `**${s.phase_number}.** **${s.name}** — _${s.agent}_\n   ${s.description}`
  ).join("\n\n");

  return new EmbedBuilder()
    .setColor(0x5865f2)
    .setTitle("Pre-Flight Catalog — Review Your Pipeline")
    .setDescription(
      `Before we start, review every stage and agent below.\n` +
      `For each stage, choose **Trust Agent** (auto-approve) or **I want to Validate** (you approve manually).\n\n` +
      `**By default, all stages require your validation.**\n` +
      `Use the dropdown below to select stages you trust to run autonomously.\n\n` +
      `───────────────────────────────\n\n` +
      stageList
    )
    .addFields(
      { name: "Source", value: url || "(pasted text)", inline: true },
      { name: "Pages", value: `${pages} content pages`, inline: true },
      { name: "Total Stages", value: `${STAGES.length}`, inline: true }
    )
    .setFooter({ text: "Select trusted stages below, then click Start Pipeline" })
    .setTimestamp();
}

/**
 * Build the trust/validate select menu.
 * Users multi-select which stages they TRUST. Unselected = validate (manual).
 */
export function buildTrustSelectMenu(): ActionRowBuilder<StringSelectMenuBuilder> {
  const options = STAGES.map((s) =>
    new StringSelectMenuOptionBuilder()
      .setLabel(`${s.name} (${s.agent})`)
      .setDescription(s.description.slice(0, 100))
      .setValue(s.id)
  );

  const select = new StringSelectMenuBuilder()
    .setCustomId("trust_stages")
    .setPlaceholder("Select stages to Trust Agent (auto-approve)...")
    .setMinValues(0)
    .setMaxValues(STAGES.length)
    .addOptions(options);

  return new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(select);
}

/**
 * Build "Trust All" / "Validate All" / "Start Pipeline" buttons.
 */
export function buildCatalogButtons(): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId("catalog_trust_all")
      .setLabel("Trust All Agents")
      .setStyle(ButtonStyle.Secondary),
    new ButtonBuilder()
      .setCustomId("catalog_validate_all")
      .setLabel("Validate All (default)")
      .setStyle(ButtonStyle.Secondary),
    new ButtonBuilder()
      .setCustomId("catalog_start")
      .setLabel("Start Pipeline")
      .setStyle(ButtonStyle.Success)
  );
}

/**
 * Build an embed summarizing chosen trust/validate preferences.
 */
export function buildPreferenceSummaryEmbed(
  prefs: Record<string, "trust" | "validate">
): EmbedBuilder {
  const lines = STAGES.map((s) => {
    const pref = prefs[s.id] || "validate";
    const icon = pref === "trust" ? "✅ Trust" : "❌ Validate";
    return `**${s.name}** — ${icon}`;
  });

  return new EmbedBuilder()
    .setColor(0x3498db)
    .setTitle("Stage Preferences Set")
    .setDescription(lines.join("\n"))
    .setFooter({ text: "Pipeline starting..." })
    .setTimestamp();
}

// ═════════════════════════════════════════════════════════════════
//  STRUCTURED REJECT MODAL
// ═════════════════════════════════════════════════════════════════

/**
 * Build a multi-field reject/re-run modal for richer user feedback.
 */
export function buildRejectModal(stageId: string): ModalBuilder {
  const issueType = new TextInputBuilder()
    .setCustomId("reject_issue_type")
    .setLabel("Issue type")
    .setStyle(TextInputStyle.Short)
    .setPlaceholder("e.g., Tone, Accuracy, Missing info, Bias, Style")
    .setRequired(true)
    .setMaxLength(100);

  const whatIsWrong = new TextInputBuilder()
    .setCustomId("reject_what_wrong")
    .setLabel("What specifically is wrong?")
    .setStyle(TextInputStyle.Paragraph)
    .setPlaceholder("Describe the problem in detail...")
    .setRequired(true)
    .setMaxLength(1000);

  const whatToFocus = new TextInputBuilder()
    .setCustomId("reject_focus")
    .setLabel("What should the agent focus on?")
    .setStyle(TextInputStyle.Paragraph)
    .setPlaceholder("e.g., 'Focus more on economic impact' or 'Use a neutral tone'")
    .setRequired(false)
    .setMaxLength(1000);

  return new ModalBuilder()
    .setCustomId(`modal_reject_${stageId}`)
    .setTitle("Re-run Stage — Provide Feedback")
    .addComponents(
      new ActionRowBuilder<TextInputBuilder>().addComponents(issueType),
      new ActionRowBuilder<TextInputBuilder>().addComponents(whatIsWrong),
      new ActionRowBuilder<TextInputBuilder>().addComponents(whatToFocus)
    );
}

/**
 * Build completion actions:
 * - Optional: Open PDF in Google Drive (link button)
 * - Always: User approval to publish on LinkedIn (uses text from send_email stage; no Drive required)
 */
export function buildCompletionActions(googleDriveUrl?: string | null): ActionRowBuilder<ButtonBuilder> {
  const row = new ActionRowBuilder<ButtonBuilder>();
  const url = googleDriveUrl?.trim();
  if (url) {
    row.addComponents(
      new ButtonBuilder()
        .setLabel("Open PDF (Google Drive)")
        .setStyle(ButtonStyle.Link)
        .setURL(url)
    );
  }
  row.addComponents(
    new ButtonBuilder()
      .setCustomId("post_linkedin")
      .setLabel("Looks Good — Post to LinkedIn")
      .setStyle(ButtonStyle.Success)
  );
  return row;
}
