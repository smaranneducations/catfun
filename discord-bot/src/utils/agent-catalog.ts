/**
 * Agent Action Catalog — the single source of truth for every agent action in the pipeline.
 *
 * Each entry defines:
 *   - Who the agent is (name, codename)
 *   - What action they perform
 *   - At which stage
 *   - What their fixed prompt instruction looks like
 *   - What variable data they need and WHERE it comes from (mapped to other agents' outputs)
 *
 * For stages with debates (analyst_pairs, content_synthesis), the catalog defines
 * template actions per round. The actual number of rounds is dynamic (up to MAX_ROUNDS=3).
 *
 * The "execution_order" is a global sequence number across the entire session.
 * For analyst_pairs, the sub-ordering is: perspective_index * actions_per_perspective + action_index
 */

// ── Input variable mapping: where does an agent's input come from? ──
export interface VariableMapping {
  from_stage: string;          // which stage produced this data
  from_agent: string;          // which agent produced it
  from_action: string;         // which action produced it
  field?: string;              // specific field in the output JSON (optional)
  description: string;         // human-readable description
}

// ── A single agent action definition ──
export interface AgentActionDef {
  id: string;                  // unique key, e.g. "content_extraction__system__extract"
  agent_name: string;          // e.g. "System", "Clio"
  agent_codename: string;      // e.g. "System", "Clio"
  action: string;              // e.g. "extract", "prepare", "review", "revise"
  action_label: string;        // human-readable, e.g. "Extract Content from URL"
  stage: string;               // pipeline stage id
  perspective?: string;        // e.g. "historical" (only for analyst stages)
  round_number: number;        // 1 for non-debate actions, 1-3 for debate rounds
  prompt_fixed: string;        // the constant instruction portion of the prompt
  prompt_variables: Record<string, VariableMapping>;  // variable inputs mapped to sources
  is_debate_template: boolean; // if true, this action repeats per round
}

// ── Perspectives for analyst_pairs ──
export const PERSPECTIVES = ["historical", "economic", "social", "future"] as const;
export type Perspective = typeof PERSPECTIVES[number];

export const PERSPECTIVE_AGENTS: Record<Perspective, { preparer: string; reviewer: string; prep_code: string; rev_code: string }> = {
  historical: { preparer: "Historian", reviewer: "Historical Reviewer", prep_code: "Clio", rev_code: "Theron" },
  economic:   { preparer: "Economist", reviewer: "Economic Reviewer", prep_code: "Aurelia", rev_code: "Callisto" },
  social:     { preparer: "Sociologist", reviewer: "Social Reviewer", prep_code: "Sage", rev_code: "Liora" },
  future:     { preparer: "Futurist", reviewer: "Future Reviewer", prep_code: "Nova", rev_code: "Orion" },
};

// ── Helper to build a unique action ID ──
function actionId(stage: string, agent: string, action: string, perspective?: string, round?: number): string {
  const parts = [stage, agent.toLowerCase().replace(/\s+/g, "_"), action];
  if (perspective) parts.push(perspective);
  if (round && round > 1) parts.push(`r${round}`);
  return parts.join("__");
}

// ── Build the full static catalog ──
function buildCatalog(): AgentActionDef[] {
  const catalog: AgentActionDef[] = [];
  let order = 1;

  // ──────────────────────────────────────────────
  // STAGE 1: Content Extraction
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("content_extraction", "System", "extract"),
    agent_name: "System",
    agent_codename: "System",
    action: "extract",
    action_label: "Extract Content from URL",
    stage: "content_extraction",
    round_number: 1,
    prompt_fixed: "Fetch article from URL, extract full text, identify headline, publisher, topic, and key facts.",
    prompt_variables: {
      url: {
        from_stage: "user_input",
        from_agent: "User",
        from_action: "provide_url",
        description: "The article URL provided by the user",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 2: Design DNA
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("design_dna", "Vesper", "create_identity"),
    agent_name: "DesignDNA",
    agent_codename: "Vesper",
    action: "create_identity",
    action_label: "Detect Emotion and Design Identity",
    stage: "design_dna",
    round_number: 1,
    prompt_fixed: "Analyze the article's emotional tone. Select matching visual style, color palette, typography, and imagery direction from the design catalog.",
    prompt_variables: {
      story: {
        from_stage: "content_extraction",
        from_agent: "System",
        from_action: "extract",
        description: "Extracted article content (headline, text, topic, facts)",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 3: Analyst Pairs (4 perspectives x debate rounds)
  // ──────────────────────────────────────────────
  for (const perspective of PERSPECTIVES) {
    const agents = PERSPECTIVE_AGENTS[perspective];
    const MAX_ROUNDS = 3;

    // Initial analysis
    catalog.push({
      id: actionId("analyst_pairs", agents.prep_code, "prepare", perspective),
      agent_name: agents.preparer,
      agent_codename: agents.prep_code,
      action: "prepare",
      action_label: `${agents.prep_code} — Initial ${perspective.charAt(0).toUpperCase() + perspective.slice(1)} Analysis`,
      stage: "analyst_pairs",
      perspective,
      round_number: 1,
      prompt_fixed: `Analyze this article from a ${perspective} perspective. Provide thesis, key arguments, evidence, and a confidence score.`,
      prompt_variables: {
        story: {
          from_stage: "content_extraction",
          from_agent: "System",
          from_action: "extract",
          description: "Extracted article content",
        },
      },
      is_debate_template: false,
    });

    // Debate rounds (review + revise)
    for (let round = 1; round <= MAX_ROUNDS; round++) {
      // Reviewer reviews
      catalog.push({
        id: actionId("analyst_pairs", agents.rev_code, "review", perspective, round),
        agent_name: agents.reviewer,
        agent_codename: agents.rev_code,
        action: "review",
        action_label: `${agents.rev_code} — Review Round ${round} (${perspective})`,
        stage: "analyst_pairs",
        perspective,
        round_number: round,
        prompt_fixed: `Critically review the ${perspective} analysis. Score it, identify weaknesses, issue demands for improvement, and decide whether to approve or require revision.`,
        prompt_variables: {
          work: {
            from_stage: "analyst_pairs",
            from_agent: agents.preparer,
            from_action: round === 1 ? "prepare" : "revise",
            field: "current_submission",
            description: `${agents.prep_code}'s ${round === 1 ? "initial analysis" : `revision round ${round - 1}`}`,
          },
          story_context: {
            from_stage: "content_extraction",
            from_agent: "System",
            from_action: "extract",
            description: "Original article for reference",
          },
        },
        is_debate_template: true,
      });

      // Preparer revises (only if not the last potential round — actual continuation depends on approval)
      catalog.push({
        id: actionId("analyst_pairs", agents.prep_code, "revise", perspective, round),
        agent_name: agents.preparer,
        agent_codename: agents.prep_code,
        action: "revise",
        action_label: `${agents.prep_code} — Revision Round ${round} (${perspective})`,
        stage: "analyst_pairs",
        perspective,
        round_number: round,
        prompt_fixed: `Address the reviewer's demands and improve your ${perspective} analysis. Incorporate feedback while maintaining your core thesis.`,
        prompt_variables: {
          original_work: {
            from_stage: "analyst_pairs",
            from_agent: agents.preparer,
            from_action: round === 1 ? "prepare" : "revise",
            description: `Your previous ${round === 1 ? "initial analysis" : `revision round ${round - 1}`}`,
          },
          feedback: {
            from_stage: "analyst_pairs",
            from_agent: agents.reviewer,
            from_action: "review",
            description: `${agents.rev_code}'s review demands and feedback`,
          },
        },
        is_debate_template: true,
      });
    }
  }

  // ──────────────────────────────────────────────
  // STAGE 4: Round Table
  // ──────────────────────────────────────────────
  const roundTableAgents = [
    { name: "Economist", code: "Aurelia" },
    { name: "Historian", code: "Clio" },
    { name: "Futurist", code: "Nova" },
    { name: "Sociologist", code: "Sage" },
  ];
  for (const agent of roundTableAgents) {
    catalog.push({
      id: actionId("round_table", agent.code, "challenge"),
      agent_name: agent.name,
      agent_codename: agent.code,
      action: "challenge",
      action_label: `${agent.code} — Cross-Discipline Challenge`,
      stage: "round_table",
      round_number: 1,
      prompt_fixed: "Challenge the other analysts' perspectives from your discipline. Identify blind spots, contradictions, and overlooked implications.",
      prompt_variables: {
        perspectives: {
          from_stage: "analyst_pairs",
          from_agent: "All Analysts",
          from_action: "final_output",
          description: "All 4 analyst perspectives (final approved versions)",
        },
        story: {
          from_stage: "content_extraction",
          from_agent: "System",
          from_action: "extract",
          description: "Original article context",
        },
      },
      is_debate_template: false,
    });

    catalog.push({
      id: actionId("round_table", agent.code, "respond"),
      agent_name: agent.name,
      agent_codename: agent.code,
      action: "respond",
      action_label: `${agent.code} — Respond to Challenges`,
      stage: "round_table",
      round_number: 1,
      prompt_fixed: "Respond to challenges raised by other analysts. Defend, concede, or refine your position.",
      prompt_variables: {
        own_perspective: {
          from_stage: "analyst_pairs",
          from_agent: agent.name,
          from_action: "final_output",
          description: `${agent.code}'s approved analysis`,
        },
        challenges: {
          from_stage: "round_table",
          from_agent: "Other Analysts",
          from_action: "challenge",
          description: "Challenges from other disciplines",
        },
      },
      is_debate_template: false,
    });
  }

  // ──────────────────────────────────────────────
  // STAGE 5: Editorial Oversight
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("editorial", "Paramount", "review_perspectives"),
    agent_name: "Editor-in-Chief",
    agent_codename: "Paramount",
    action: "review_perspectives",
    action_label: "Paramount — Editorial Review",
    stage: "editorial",
    round_number: 1,
    prompt_fixed: "Review all analyst perspectives for quality, coherence, balance, and editorial standards. Provide overall assessment, verdicts, and per-agent feedback.",
    prompt_variables: {
      story: {
        from_stage: "content_extraction",
        from_agent: "System",
        from_action: "extract",
        description: "Original article",
      },
      perspectives: {
        from_stage: "analyst_pairs",
        from_agent: "All Analysts",
        from_action: "final_output",
        description: "All 4 analyst perspectives",
      },
      round_table_results: {
        from_stage: "round_table",
        from_agent: "All Analysts",
        from_action: "respond",
        description: "Round table discussion outcomes",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 6: Content Synthesis (Quill + Sterling debate)
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("content_synthesis", "Quill", "synthesise"),
    agent_name: "Content Writer",
    agent_codename: "Quill",
    action: "synthesise",
    action_label: "Quill — Synthesise Poster Pages",
    stage: "content_synthesis",
    round_number: 1,
    prompt_fixed: "Synthesise all analyst perspectives, editorial feedback, and design identity into structured poster page content.",
    prompt_variables: {
      story: {
        from_stage: "content_extraction",
        from_agent: "System",
        from_action: "extract",
        description: "Original article",
      },
      perspectives: {
        from_stage: "analyst_pairs",
        from_agent: "All Analysts",
        from_action: "final_output",
        description: "All 4 analyst perspectives",
      },
      editor_notes: {
        from_stage: "editorial",
        from_agent: "Paramount",
        from_action: "review_perspectives",
        description: "Editor-in-chief feedback and directions",
      },
      design: {
        from_stage: "design_dna",
        from_agent: "Vesper",
        from_action: "create_identity",
        description: "Design identity (emotion, style, palette, fonts)",
      },
    },
    is_debate_template: false,
  });

  // Sterling reviews Quill's work (debate)
  const MAX_SYNTH_ROUNDS = 3;
  for (let round = 1; round <= MAX_SYNTH_ROUNDS; round++) {
    catalog.push({
      id: actionId("content_synthesis", "Sterling", "review", undefined, round),
      agent_name: "Copy Reviewer",
      agent_codename: "Sterling",
      action: "review",
      action_label: `Sterling — Copy Review Round ${round}`,
      stage: "content_synthesis",
      round_number: round,
      prompt_fixed: "Review the poster content for writing quality, tone, clarity, and professional standard. Score, approve or demand revisions.",
      prompt_variables: {
        work: {
          from_stage: "content_synthesis",
          from_agent: "Quill",
          from_action: round === 1 ? "synthesise" : "revise",
          description: `Quill's ${round === 1 ? "initial synthesis" : `revision round ${round - 1}`}`,
        },
        story_context: {
          from_stage: "content_extraction",
          from_agent: "System",
          from_action: "extract",
          description: "Original article for reference",
        },
      },
      is_debate_template: true,
    });

    catalog.push({
      id: actionId("content_synthesis", "Quill", "revise", undefined, round),
      agent_name: "Content Writer",
      agent_codename: "Quill",
      action: "revise",
      action_label: `Quill — Content Revision Round ${round}`,
      stage: "content_synthesis",
      round_number: round,
      prompt_fixed: "Revise your poster content based on copy reviewer's feedback. Improve writing quality while maintaining accuracy.",
      prompt_variables: {
        original_work: {
          from_stage: "content_synthesis",
          from_agent: "Quill",
          from_action: round === 1 ? "synthesise" : "revise",
          description: `Your previous ${round === 1 ? "synthesis" : `revision round ${round - 1}`}`,
        },
        feedback: {
          from_stage: "content_synthesis",
          from_agent: "Sterling",
          from_action: "review",
          description: "Sterling's copy review feedback",
        },
      },
      is_debate_template: true,
    });
  }

  // ──────────────────────────────────────────────
  // STAGE 7: Neutrality Check
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("neutrality_check", "Justice", "review"),
    agent_name: "Content Reviewer",
    agent_codename: "Justice",
    action: "review",
    action_label: "Justice — Neutrality and Bias Review",
    stage: "neutrality_check",
    round_number: 1,
    prompt_fixed: "Review the synthesised content for bias, neutrality, and ethical tone. Flag any issues.",
    prompt_variables: {
      brief: {
        from_stage: "content_synthesis",
        from_agent: "Quill",
        from_action: "final_output",
        description: "Final synthesised poster content",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 8: Discussion Potential
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("discussion_potential", "Spark", "evaluate"),
    agent_name: "Discussion Potential Analyst",
    agent_codename: "Spark",
    action: "evaluate",
    action_label: "Spark — Engagement Potential Scoring",
    stage: "discussion_potential",
    round_number: 1,
    prompt_fixed: "Score the engagement and discussion potential. Generate hooks, questions, and debate starters.",
    prompt_variables: {
      story: {
        from_stage: "content_extraction",
        from_agent: "System",
        from_action: "extract",
        description: "Original article",
      },
      brief: {
        from_stage: "content_synthesis",
        from_agent: "Quill",
        from_action: "final_output",
        description: "Final synthesised poster content",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 9: Pre-Validation (Quality Gate)
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("pre_validation", "Sentinel-A", "validate"),
    agent_name: "PreVisualValidator",
    agent_codename: "Sentinel-A",
    action: "validate",
    action_label: "Sentinel-A — Quality Gate (17 Rules)",
    stage: "pre_validation",
    round_number: 1,
    prompt_fixed: "Validate the content against 17 quality rules covering structure, depth, accuracy, tone, and completeness.",
    prompt_variables: {
      brief: {
        from_stage: "content_synthesis",
        from_agent: "Quill",
        from_action: "final_output",
        description: "Final poster content",
      },
      design: {
        from_stage: "design_dna",
        from_agent: "Vesper",
        from_action: "create_identity",
        description: "Design identity",
      },
      story: {
        from_stage: "content_extraction",
        from_agent: "System",
        from_action: "extract",
        description: "Original article",
      },
      agent_rounds: {
        from_stage: "analyst_pairs",
        from_agent: "All Analysts",
        from_action: "debate_summary",
        description: "Summary of all debate rounds and scores",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 10: Visual Generation
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("visuals", "Prism", "generate"),
    agent_name: "VisualGenerator",
    agent_codename: "Prism",
    action: "generate",
    action_label: "Prism — Generate All Visuals",
    stage: "visuals",
    round_number: 1,
    prompt_fixed: "Generate all images for the poster: backgrounds, foregrounds, cover art, infographics, and persona images.",
    prompt_variables: {
      design: {
        from_stage: "design_dna",
        from_agent: "Vesper",
        from_action: "create_identity",
        description: "Design identity (style, palette, imagery direction)",
      },
      brief: {
        from_stage: "content_synthesis",
        from_agent: "Quill",
        from_action: "final_output",
        description: "Poster content for image context",
      },
      story: {
        from_stage: "content_extraction",
        from_agent: "System",
        from_action: "extract",
        description: "Original article for thematic imagery",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 11: PDF Generation
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("pdf_generation", "System", "generate_pdf"),
    agent_name: "System",
    agent_codename: "System",
    action: "generate_pdf",
    action_label: "System — Build PDF Poster",
    stage: "pdf_generation",
    round_number: 1,
    prompt_fixed: "Assemble the final PDF poster from all content, visuals, and design specifications.",
    prompt_variables: {
      brief: {
        from_stage: "content_synthesis",
        from_agent: "Quill",
        from_action: "final_output",
        description: "Poster page content",
      },
      design: {
        from_stage: "design_dna",
        from_agent: "Vesper",
        from_action: "create_identity",
        description: "Design identity",
      },
      visuals: {
        from_stage: "visuals",
        from_agent: "Prism",
        from_action: "generate",
        description: "Generated images and paths",
      },
    },
    is_debate_template: false,
  });

  // ──────────────────────────────────────────────
  // STAGE 12: Post-Validation (Layout Review — Info Only)
  // ──────────────────────────────────────────────
  catalog.push({
    id: actionId("post_validation", "Sentinel-B", "validate"),
    agent_name: "PostVisualValidator",
    agent_codename: "Sentinel-B",
    action: "validate",
    action_label: "Sentinel-B — Layout Review (18 Rules)",
    stage: "post_validation",
    round_number: 1,
    prompt_fixed: "Validate the final PDF against 18 layout and visual quality rules. Informational only — does not block delivery.",
    prompt_variables: {
      brief: {
        from_stage: "content_synthesis",
        from_agent: "Quill",
        from_action: "final_output",
        description: "Poster content",
      },
      design: {
        from_stage: "design_dna",
        from_agent: "Vesper",
        from_action: "create_identity",
        description: "Design identity",
      },
      story: {
        from_stage: "content_extraction",
        from_agent: "System",
        from_action: "extract",
        description: "Original article",
      },
      visuals_count: {
        from_stage: "visuals",
        from_agent: "Prism",
        from_action: "generate",
        field: "image_count",
        description: "Number of generated images",
      },
    },
    is_debate_template: false,
  });

  return catalog;
}

// ── Singleton catalog instance ──
export const AGENT_CATALOG = buildCatalog();
