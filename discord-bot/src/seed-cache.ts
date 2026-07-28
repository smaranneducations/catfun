/**
 * seed-cache.ts — Pre-populate the SQLite database with cached stage results
 * for a known URL so that the pipeline can run without ANY API calls.
 *
 * Usage: npx ts-node src/seed-cache.ts
 *    OR: node dist/seed-cache.js (after tsc build)
 */

import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";
dotenvConfig({ path: resolve(__dirname, "../../.env") });

import dbOps from "./services/database";

const TEST_URL = "https://chrishood.com/the-13-dimensions-a-complete-nomotic-architecture/";
const PDF_PATH = resolve(__dirname, "../../aibrief/output/The_13_Dimensions_of_AI_Governance_poster_run_20260213_003926.pdf");

// ═══════════════════════════════════════════════════════════════
//  MOCK STAGE RESULTS — Rich, realistic data for every stage
// ═══════════════════════════════════════════════════════════════

const STAGE_RESULTS: Record<string, any> = {
  content_extraction: {
    headline: "The 13 Dimensions: A Complete Nomotic Architecture for AI Governance",
    publisher: "Chris Hood",
    description: "An in-depth exploration of the Nomotic Architecture — a comprehensive 13-dimensional framework for governing AI systems. The framework addresses trust engineering, predictive governance, algorithmic accountability, and societal impact through a structured multi-layered approach.",
    content_length: 8500,
    status: "extracted",
    article_text_preview: "The Nomotic Architecture represents a paradigm shift in how we think about AI governance. Rather than reactive regulations, it proposes a proactive, multi-dimensional framework that anticipates challenges before they emerge...",
  },

  design_dna: {
    emotion: "awe",
    style_id: "tech_futurist",
    design_name: "Neural Horizon",
    palette_id: "deep_space",
    font_id: "geometric_modern",
    imagen_style: "cinematic digital art",
    emotion_reasoning: "The 13 Dimensions framework represents a groundbreaking intellectual achievement in AI governance. The sheer scope and ambition of creating a comprehensive multi-dimensional architecture evokes a sense of awe — the feeling of witnessing something that could reshape the future of technology governance. This isn't fear-based AI regulation; it's visionary engineering.",
    primary_color: "#0A1628",
    secondary_color: "#1E3A5F",
    accent_color: "#00D4FF",
    visual_motif: "Interconnected neural pathways forming a 13-pointed geometric structure, representing the dimensions converging into a unified governance framework",
  },

  analyst_pairs: {
    perspectives: {
      historical: {
        perspective_title: "Nomotic AI: Engineering Trust Through Predictive Governance",
        pull_quote: "For the first time, we see a governance framework that doesn't react to AI failures but anticipates them through dimensional analysis.",
        confidence: 8,
        key_arguments: [
          "Historical parallel to the International Telecommunications Union (ITU) standardization of 1865 — a multi-dimensional framework that unified chaotic telegraph networks",
          "The 13-dimension approach mirrors the evolution from Newtonian mechanics to quantum field theory — a dimensional expansion to capture previously invisible forces",
          "Colonial-era governance failures teach us that single-dimension control (economic exploitation) leads to systemic collapse — Nomotic's multi-dimensional approach avoids this trap",
        ],
      },
      economic: {
        perspective_title: "Economic Impact of the Nomotic Architecture: AI Governance as Market Infrastructure",
        pull_quote: "Nomotic governance could become the GAAP of AI — a standardized framework that makes AI systems auditable, comparable, and investable.",
        confidence: 7,
        key_arguments: [
          "Market signal: Companies adopting multi-dimensional AI governance see 23% lower regulatory compliance costs",
          "The framework creates a new economic category: 'Governance as a Service' (GaaS) — estimated $40B market by 2030",
          "Risk reduction: Dimensional analysis reduces AI incident liability exposure by an estimated 45%",
        ],
      },
      social: {
        perspective_title: "Algorithmic Governance and the New Feudalism: Nomotic AI's Democratic Promise",
        pull_quote: "Without frameworks like Nomotic, we risk creating a world where AI governance is dictated by a handful of tech corporations — a digital feudalism.",
        confidence: 8,
        key_arguments: [
          "The 13-dimension model democratizes AI oversight — each dimension represents a stakeholder voice that would otherwise be silenced",
          "Social impact: marginalized communities disproportionately affected by AI decisions finally get representation through dimensions 7-9",
          "The framework's transparency requirements could reduce algorithmic discrimination by up to 60% based on comparable regulatory implementations",
        ],
      },
      future: {
        perspective_title: "The Rise of 13-Dimensional AI Governance: A Futurist Perspective",
        pull_quote: "By 2030, organizations without multi-dimensional governance frameworks will be as unthinkable as companies without cybersecurity today.",
        confidence: 9,
        key_arguments: [
          "6-month prediction: At least 3 major tech companies will announce Nomotic-inspired governance frameworks",
          "2-year prediction: Regulatory bodies (EU AI Act, US NIST) will incorporate dimensional governance concepts",
          "5-year prediction: Nomotic becomes the ISO standard for AI governance — 13-dimensional auditing becomes mandatory for public AI systems",
        ],
      },
    },
    full_debates: [
      {
        label: "historical",
        preparer_name: "Clio",
        reviewer_name: "Chronos",
        total_rounds: 3,
        final_score: 8,
        final_approved: true,
        rounds: [
          {
            round: 1,
            score: 7,
            approved: false,
            demands_count: 2,
            preparer_submission: {
              perspective_title: "Nomotic AI: Engineering Trust Through Predictive Governance",
              confidence: 7,
              pull_quote: "For the first time, we see a governance framework that doesn't react to AI failures but anticipates them.",
              key_insight: "The parallel between Nomotic Architecture and the ITU standardization of 1865 is striking — both created multi-dimensional frameworks to govern chaotic, rapidly evolving technologies.",
              historical_parallels: [
                { event: "ITU Standardization 1865", connection: "Multi-dimensional framework that unified chaotic telegraph networks across 20 nations — Nomotic does the same for AI systems" },
                { event: "Bretton Woods System 1944", connection: "Created governance dimensions (exchange rates, trade rules, development aid) that parallel Nomotic's multi-layered approach" },
                { event: "Nuclear Non-Proliferation Treaty 1968", connection: "Dimensional governance of a dangerous technology — inspection, limitation, cooperation dimensions mirror Nomotic's trust engineering" },
              ],
            },
            reviewer_feedback: {
              verdict: "Strong historical analysis but lacks specificity on implementation timeline. The parallels are apt but need quantification.",
              strengths: ["Excellent use of ITU parallel — highly relevant", "Good range of historical examples spanning different governance domains", "Clear connection between historical precedent and current AI governance needs"],
              weaknesses: ["No quantification of how long these historical frameworks took to gain adoption", "Missing analysis of governance failures — what happens when dimensional frameworks collapse?"],
            },
            demands: ["Add adoption timeline analysis — how long did ITU take vs expected Nomotic adoption?", "Include at least one counter-example of dimensional governance failure"],
            verdict: "Revision needed — strengthen with timeline data and failure analysis",
            preparer_revision: {
              perspective_title: "Nomotic AI: Engineering Trust Through Predictive Governance",
              confidence: 8,
              key_insight: "Historical dimensional governance frameworks took 5-15 years for full adoption. Nomotic's digital-native design could accelerate this to 3-5 years.",
              key_arguments: [
                "ITU took 12 years for full adoption (1865-1877) but unified 20+ nations' telegraph systems",
                "Counter-example: League of Nations failed because its dimensional framework lacked enforcement mechanisms — Nomotic addresses this through automated compliance checking",
                "Adoption accelerator: Unlike physical governance, Nomotic can be deployed as software — reducing adoption friction by orders of magnitude",
              ],
            },
          },
          {
            round: 2,
            score: 8,
            approved: true,
            demands_count: 0,
            preparer_submission: {
              perspective_title: "Nomotic AI: Engineering Trust Through Predictive Governance (Revised)",
              confidence: 8,
              key_insight: "The historical record shows that multi-dimensional governance frameworks succeed when they have enforcement mechanisms and low adoption friction — Nomotic scores well on both.",
            },
            reviewer_feedback: {
              verdict: "Significantly improved. The timeline analysis and failure counter-example add substantial depth. The adoption acceleration argument is compelling.",
              strengths: ["Timeline data adds credibility", "League of Nations counter-example demonstrates understanding of failure modes", "Digital-native adoption argument is novel and persuasive"],
              weaknesses: [],
            },
            demands: [],
            verdict: "Approved — strong, well-evidenced historical analysis",
          },
          {
            round: 3,
            score: 8,
            approved: true,
            demands_count: 0,
            preparer_submission: {
              perspective_title: "Nomotic AI: Engineering Trust Through Predictive Governance (Final)",
              confidence: 8,
              pull_quote: "For the first time, we see a governance framework that doesn't react to AI failures but anticipates them through dimensional analysis.",
              key_insight: "The 13-dimension approach mirrors the evolution from Newtonian mechanics to quantum field theory — a dimensional expansion to capture previously invisible forces in technology governance.",
            },
            reviewer_feedback: {
              verdict: "Final version is publication-ready. Strong historical grounding with practical implications.",
              strengths: ["Comprehensive historical analysis", "Balanced perspective with counter-examples", "Clear implications for Nomotic adoption"],
              weaknesses: [],
            },
            demands: [],
            verdict: "Approved — ready for publication",
          },
        ],
      },
      {
        label: "economic",
        preparer_name: "Aurelia",
        reviewer_name: "Nexus",
        total_rounds: 3,
        final_score: 7,
        final_approved: true,
        rounds: [
          {
            round: 1,
            score: 6,
            approved: false,
            demands_count: 3,
            preparer_submission: {
              perspective_title: "Economic Impact of the Nomotic Architecture",
              confidence: 6,
              key_insight: "The Nomotic framework creates a new economic category: Governance as a Service (GaaS), estimated at $40B by 2030.",
              economic_impact: [
                { point: "Compliance cost reduction", detail: "Companies adopting dimensional governance see 23% lower regulatory compliance costs" },
                { point: "New market creation", detail: "GaaS market could reach $40B by 2030, rivaling the cybersecurity industry's early growth" },
                { point: "Liability reduction", detail: "Dimensional analysis reduces AI incident liability exposure by an estimated 45%" },
              ],
              market_signal: "Investment in AI governance startups increased 340% in 2025, signaling strong market demand for structured frameworks",
              winners: ["Governance technology providers", "AI auditing firms", "Compliance consultancies"],
              losers: ["Companies with opaque AI systems", "Regulatory arbitrage players"],
            },
            reviewer_feedback: {
              verdict: "Good foundation but numbers lack sourcing. The $40B GaaS estimate needs justification. Winner/loser analysis is too simplistic.",
              strengths: ["Novel GaaS concept is interesting", "Good identification of compliance cost savings"],
              weaknesses: ["$40B estimate is unsourced", "Winner/loser analysis needs nuance — what about mid-size companies?", "No analysis of implementation costs"],
            },
            demands: ["Source the $40B GaaS market estimate or revise", "Add implementation cost analysis", "Expand winner/loser to include mid-market companies"],
            verdict: "Revision needed — strengthen economic data",
          },
          {
            round: 2,
            score: 7,
            approved: true,
            demands_count: 0,
            preparer_submission: {
              perspective_title: "Economic Impact of the Nomotic Architecture (Revised)",
              confidence: 7,
              key_insight: "Based on cybersecurity market parallels (CAGR 12.4% 2015-2025), AI governance could grow from $4.2B to $38B by 2030.",
              economic_impact: [
                { point: "Market sizing methodology", detail: "Using cybersecurity market parallel: $4.2B (2025) → $38B (2030) at 55% CAGR during adoption surge" },
                { point: "Implementation costs", detail: "Average enterprise implementation: $2-5M initial, $500K-1M annual. ROI positive within 18 months via compliance savings" },
              ],
            },
            reviewer_feedback: {
              verdict: "Much improved. The cybersecurity parallel gives the market estimate credibility. Implementation cost analysis adds practical value.",
              strengths: ["Cybersecurity parallel methodology is sound", "Implementation cost analysis adds practical value", "ROI timeline is reasonable"],
              weaknesses: [],
            },
            demands: [],
            verdict: "Approved — solid economic analysis",
          },
          {
            round: 3,
            score: 7,
            approved: true,
            demands_count: 0,
            preparer_submission: { perspective_title: "Economic Impact — Final" },
            reviewer_feedback: { verdict: "Publication ready", strengths: ["Well-researched", "Practical"], weaknesses: [] },
            demands: [],
            verdict: "Approved",
          },
        ],
      },
      {
        label: "social",
        preparer_name: "Sage",
        reviewer_name: "Praxis",
        total_rounds: 3,
        final_score: 8,
        final_approved: true,
        rounds: [
          {
            round: 1, score: 7, approved: false, demands_count: 1,
            preparer_submission: {
              perspective_title: "Algorithmic Governance and the New Feudalism",
              confidence: 7,
              key_insight: "Without frameworks like Nomotic, we risk digital feudalism — where AI governance is dictated by a handful of tech corporations.",
              social_impact: [
                { who: "Marginalized communities", what: "Dimensions 7-9 specifically address representation gaps in AI decision-making" },
                { who: "Small nations", what: "Multi-dimensional framework prevents governance capture by large tech-exporting nations" },
                { who: "Workers", what: "Algorithmic management dimensions require transparency in automated decision-making affecting employment" },
              ],
            },
            reviewer_feedback: {
              verdict: "Compelling social analysis. The digital feudalism metaphor is powerful. Needs more concrete implementation examples.",
              strengths: ["Digital feudalism metaphor is powerful and apt", "Good identification of affected populations"],
              weaknesses: ["Needs concrete examples of how dimensions 7-9 would work in practice"],
            },
            demands: ["Add specific implementation example for at least one affected population"],
            verdict: "Minor revision needed",
          },
          {
            round: 2, score: 8, approved: true, demands_count: 0,
            preparer_submission: { perspective_title: "Algorithmic Governance and the New Feudalism (Revised)", confidence: 8 },
            reviewer_feedback: { verdict: "Approved — compelling social analysis with practical grounding", strengths: ["Strong", "Well-evidenced"], weaknesses: [] },
            demands: [], verdict: "Approved",
          },
          {
            round: 3, score: 8, approved: true, demands_count: 0,
            preparer_submission: { perspective_title: "Algorithmic Governance — Final" },
            reviewer_feedback: { verdict: "Publication ready", strengths: ["Excellent social analysis"], weaknesses: [] },
            demands: [], verdict: "Approved",
          },
        ],
      },
      {
        label: "future",
        preparer_name: "Nova",
        reviewer_name: "Oracle",
        total_rounds: 3,
        final_score: 9,
        final_approved: true,
        rounds: [
          {
            round: 1, score: 8, approved: false, demands_count: 1,
            preparer_submission: {
              perspective_title: "The Rise of 13-Dimensional AI Governance",
              confidence: 9,
              key_insight: "By 2030, organizations without multi-dimensional governance will be as unthinkable as companies without cybersecurity today.",
              prediction_6mo: "At least 3 major tech companies will announce Nomotic-inspired governance frameworks",
              prediction_2yr: "EU AI Act and US NIST will incorporate dimensional governance concepts into their standards",
              prediction_5yr: "Nomotic becomes the ISO standard for AI governance — 13-dimensional auditing becomes mandatory for public AI systems",
              opportunity: "Early adopters of dimensional governance gain 3-5 year competitive moat in regulated industries",
              risk: "Framework fragmentation — competing dimensional standards could create 'governance babel' that delays adoption",
              wildcard: "A major AI incident in 2026 could accelerate Nomotic adoption from 5 years to 18 months, similar to how Sarbanes-Oxley followed Enron",
            },
            reviewer_feedback: {
              verdict: "Bold predictions with strong reasoning. The wildcard scenario is particularly insightful. One minor addition needed.",
              strengths: ["Timeline predictions are specific and testable", "Wildcard scenario shows deep thinking", "Opportunity/risk balance is good"],
              weaknesses: ["Should address what happens if a competing framework emerges from China or EU"],
            },
            demands: ["Address the scenario of competing non-Western governance frameworks"],
            verdict: "Minor revision — address competing frameworks",
          },
          {
            round: 2, score: 9, approved: true, demands_count: 0,
            preparer_submission: { perspective_title: "Rise of 13-Dimensional Governance (Revised)", confidence: 9 },
            reviewer_feedback: { verdict: "Excellent — comprehensive future analysis", strengths: ["Outstanding futurist analysis", "Specific testable predictions", "Good geopolitical awareness"], weaknesses: [] },
            demands: [], verdict: "Approved — exceptional quality",
          },
          {
            round: 3, score: 9, approved: true, demands_count: 0,
            preparer_submission: { perspective_title: "Rise of 13-Dimensional Governance — Final" },
            reviewer_feedback: { verdict: "Publication ready — best in class", strengths: ["Exceptional"], weaknesses: [] },
            demands: [], verdict: "Approved",
          },
        ],
      },
    ],
    analyst_count: 4,
    total_debate_rounds: 12,
  },

  round_table: {
    status: "complete",
    perspectives_updated: 4,
    cross_challenges: 4,
    challenge_highlights: [
      { pair: "Economist→Historian", summary: "The historian's ITU parallel underestimates the speed of digital governance adoption — software-based frameworks scale exponentially faster than treaty-based ones", impact: "Historian revised adoption timeline from 5-15 years to 3-5 years" },
      { pair: "Historian→Futurist", summary: "The futurist's 2030 ISO standard prediction is ambitious but historically, standards bodies move slower than predicted — the ITU took 12 years", impact: "Futurist added a 'delayed adoption' scenario to risk analysis" },
      { pair: "Futurist→Sociologist", summary: "The social analysis correctly identifies digital feudalism risk but underestimates how quickly grassroots governance movements can emerge in the digital age", impact: "Sociologist added digital commons governance as a countervailing force" },
      { pair: "Sociologist→Economist", summary: "The economic analysis of GaaS market needs to account for the social cost of governance — not all dimensions can be monetized without creating perverse incentives", impact: "Economist added non-monetary value dimensions to the market analysis" },
    ],
    perspectives_after: {
      historical: { perspective_title: "Nomotic AI: Engineering Trust Through Predictive Governance", confidence: 8 },
      economic: { perspective_title: "Economic Impact of the Nomotic Architecture", confidence: 7 },
      social: { perspective_title: "Algorithmic Governance and the New Feudalism", confidence: 8 },
      future: { perspective_title: "The Rise of 13-Dimensional AI Governance", confidence: 9 },
    },
  },

  editorial: {
    quality_score: 8,
    ready_for_synthesis: true,
    feedback_per_agent: {
      Historian: {
        score: 8,
        feedback: "Strong historical grounding with excellent use of parallel governance frameworks. The ITU comparison is particularly effective. The inclusion of the League of Nations failure case strengthens the analysis significantly.",
        verdict: "Publication-ready historical perspective",
        strengths: ["Excellent use of ITU parallel", "Counter-example adds credibility", "Timeline analysis is practical"],
        improvements: ["Could explore non-Western governance parallels"],
      },
      Economist: {
        score: 7,
        feedback: "Solid economic analysis with credible market sizing methodology. The cybersecurity market parallel is well-chosen. Implementation cost analysis adds practical value for decision-makers.",
        verdict: "Strong economic perspective — minor improvements possible",
        strengths: ["Market sizing methodology is sound", "ROI analysis is practical"],
        improvements: ["Could add sensitivity analysis on GaaS market projections", "Consider disruption risks to the estimate"],
      },
      Sociologist: {
        score: 8,
        feedback: "Compelling social analysis. The digital feudalism metaphor effectively communicates the stakes. The identification of affected populations (marginalized communities, small nations, workers) provides concrete grounding.",
        verdict: "Excellent social perspective",
        strengths: ["Powerful digital feudalism metaphor", "Good identification of affected populations", "Practical implementation examples"],
        improvements: [],
      },
      Futurist: {
        score: 9,
        feedback: "Exceptional futurist analysis with specific, testable predictions. The wildcard scenario (major AI incident accelerating adoption) shows deep strategic thinking. The competing frameworks addition addresses a critical gap.",
        verdict: "Best-in-class futurist perspective",
        strengths: ["Specific testable predictions", "Wildcard scenario is insightful", "Geopolitical awareness"],
        improvements: [],
      },
    },
    overall_assessment: "The four perspectives together create a comprehensive, multi-dimensional analysis of the Nomotic Architecture. Each perspective brings a unique lens — historical precedent, economic viability, social impact, and future trajectory. The cross-challenges from the round table have strengthened all perspectives. The brief is ready for synthesis.",
    missing_angles: [],
    verdict: "All perspectives approved for synthesis. Overall quality is high with strong interdisciplinary coherence.",
  },

  content_synthesis: {
    brief_title: "The 13 Dimensions: Navigating the New AI Governance Paradigm",
    subtitle: "How the Nomotic Architecture Could Reshape Technology Governance",
    page_count: 6,
    pages: [
      {
        page_type: "cover",
        page_title: "The 13 Dimensions",
        hero_statement: "A New Era of AI Governance",
        supporting_line: "The Nomotic Architecture: 13 dimensions that could define the future of technology oversight",
        visual_mood: "Expansive, futuristic, awe-inspiring",
      },
      {
        page_type: "insight",
        page_title: "The Governance Gap",
        hero_statement: "Without multi-dimensional oversight, we risk digital feudalism",
        supporting_line: "Current AI governance is one-dimensional. The Nomotic Architecture proposes 13.",
        points: [
          { point: "Single-dimension control fails", detail: "Historical precedent: colonial governance, League of Nations" },
          { point: "AI decisions affect millions", detail: "Algorithmic management, credit scoring, healthcare triage" },
          { point: "13 dimensions capture invisible forces", detail: "Trust, accountability, transparency, fairness — each gets a dimension" },
        ],
        quote: "By 2030, organizations without multi-dimensional governance will be as unthinkable as companies without cybersecurity today.",
        attribution: "Nova, Futurist Analyst",
        visual_mood: "Dark, urgent, thought-provoking",
      },
      {
        page_type: "data",
        page_title: "The Economic Case",
        hero_statement: "Governance as a Service: A $38B Market by 2030",
        supporting_line: "Following the cybersecurity growth trajectory, AI governance is the next trillion-dollar infrastructure",
        hero_number: "$38B",
        hero_label: "Projected GaaS Market by 2030",
        points: [
          { point: "23% compliance cost reduction", detail: "For companies adopting dimensional governance" },
          { point: "45% liability reduction", detail: "Through systematic dimensional risk analysis" },
          { point: "18-month ROI", detail: "Average enterprise implementation pays for itself" },
        ],
        visual_mood: "Clean, data-driven, optimistic",
      },
      {
        page_type: "perspective",
        page_title: "Historical Parallels",
        hero_statement: "From Telegraph to AI: Governance Evolves",
        supporting_line: "The ITU unified chaotic telegraph networks in 1865. Nomotic could do the same for AI.",
        points: [
          { point: "ITU Standardization 1865", detail: "Multi-dimensional framework unified 20+ nations" },
          { point: "Bretton Woods 1944", detail: "Created governance dimensions for global economics" },
          { point: "Digital-native advantage", detail: "Software-based governance scales faster — 3-5 year adoption vs historical 12+ years" },
        ],
        quote: "For the first time, we see a governance framework that doesn't react to AI failures but anticipates them through dimensional analysis.",
        attribution: "Clio, Historical Analyst",
        visual_mood: "Scholarly, authoritative, timeless",
      },
      {
        page_type: "action",
        page_title: "What Comes Next",
        hero_statement: "The 5-Year Countdown",
        supporting_line: "Three predictions that will define the AI governance landscape",
        summary_points: [
          "6 months: Major tech companies announce Nomotic-inspired frameworks",
          "2 years: Regulators incorporate dimensional governance into standards",
          "5 years: ISO standard for 13-dimensional AI auditing",
          "Wildcard: A major AI incident could compress this timeline to 18 months",
        ],
        visual_mood: "Forward-looking, energetic, call-to-action",
      },
      {
        page_type: "credits",
        page_title: "Agent Credits",
        hero_statement: "Built by AI Agents, Guided by Human Judgment",
        visual_mood: "Clean, professional",
      },
    ],
  },

  neutrality_check: {
    approved: true,
    tone_score: 9,
    revision_required: false,
    issues: [],
    strengths: [
      "Content maintains balanced perspective across all dimensions",
      "Economic claims are well-sourced with methodology",
      "Social analysis avoids vilifying any specific group",
      "Future predictions are framed as scenarios, not certainties",
      "The digital feudalism metaphor critiques systems, not people",
    ],
    verdict: "Content passes neutrality check with high marks. The analysis is balanced, constructive, and avoids personal attacks while maintaining strong analytical positions.",
  },

  discussion_potential: {
    engagement_score: 85,
    verdict: "High",
    controversy_score: 72,
    relevance_score: 91,
    shareability_score: 88,
    discussion_hooks: [
      "Is a 13-dimensional framework practical, or is it too complex for real-world implementation?",
      "Can governance frameworks truly prevent AI-driven digital feudalism, or is this inevitable?",
      "Should AI governance be standardized globally, or should different cultures have different frameworks?",
      "The $38B GaaS market prediction — is this a genuine opportunity or governance-industrial complex?",
      "Will a major AI incident be needed to force adoption, similar to Sarbanes-Oxley after Enron?",
    ],
    reasoning: "This topic sits at the intersection of technology, governance, economics, and social impact — four domains that generate passionate debate. The Nomotic Architecture is novel enough to provoke 'is this real?' discussions while being grounded enough in historical parallels to sustain serious analysis. The economic angle ($38B market) adds a business incentive that expands the audience beyond academics. The digital feudalism metaphor is shareable and provocative without being divisive.",
    suggested_angle: "Frame as a 'What does YOUR company need to do?' call-to-action for business leaders",
  },

  pre_validation: {
    total_score: 82,
    approved: true,
    explanation: "Content passes pre-visual validation with a strong score. The brief demonstrates genuine creative excellence with well-structured arguments from multiple perspectives. The editorial process shows real debate and refinement. Minor improvements possible in format density but overall quality is high.",
    critical_failures: [],
    fix_instructions: [],
    verdict: "Approved for visual generation. Content quality, neutrality, and structure all meet the threshold.",
    rules_checked: [
      { id: 5, passed: true, reasoning: "Author correctly attributed to Bhasker Kumar" },
      { id: 6, passed: true, reasoning: "Assistant name Orion Cael is properly used" },
      { id: 7, passed: true, reasoning: "Credits section lists the multi-agent system with model details" },
      { id: 8, passed: true, reasoning: "Agents genuinely debated — 12 rounds of argumentation with demands and revisions" },
      { id: 10, passed: true, reasoning: "Copy is polished, clear, and professional throughout" },
      { id: 17, passed: true, reasoning: "Preparer/Reviewer pairs argued in 3 rounds each across all 4 perspectives" },
      { id: 18, passed: true, reasoning: "Quality reflects genuine creative process — not just template filling" },
      { id: 21, passed: true, reasoning: "Bullet points used consistently, no long paragraphs" },
      { id: 27, passed: true, reasoning: "Guardrail text present in Director and Reviewer prompts" },
      { id: 28, passed: true, reasoning: "No instructions bypassed — full pipeline executed" },
      { id: 29, passed: true, reasoning: "Content is neutral — critiques systems not individuals" },
      { id: 30, passed: true, reasoning: "Each page has one clear idea with supporting evidence" },
      { id: 33, passed: true, reasoning: "Design agent selected 'awe' emotion with tech_futurist style" },
      { id: 34, passed: true, reasoning: "Four perspectives covered: historical, economic, social, future" },
      { id: 35, passed: true, reasoning: "Written from AI thought leader perspective" },
      { id: 37, passed: false, reasoning: "Page 2 has 3 bullet points — could be reduced to 1 powerful statement" },
    ],
  },

  visuals: {
    visual_count: 12,
    types: ["cover", "bg_0", "fg_0", "bg_1", "fg_1", "bg_2", "fg_2", "bg_3", "infographic_0", "infographic_1", "infographic_2", "bg_4"],
    paths: { cover: "output/visuals/covers/cover_cached.png" },
  },

  pdf_generation: {
    pdf_path: PDF_PATH,
    pdf_exists: true,
    pdf_size_kb: 96143,
    pdf_ready: true,
  },

  post_validation: {
    total_score: 78,
    combined_score: 80,
    pre_visual_score: 82,
    post_visual_score: 78,
    approved: true,
    explanation: "The PDF layout is visually striking with good use of the tech_futurist design. Image quality is high. Minor layout density issues on the data page. Overall, a strong visual execution that complements the content quality.",
    critical_failures: [],
    fix_instructions: [],
    verdict: "Layout review passed. The brief is ready for delivery.",
    rules_checked: [
      { id: 1, passed: true, reasoning: "Every page has at least one visual element" },
      { id: 2, passed: true, reasoning: "Layout is balanced and professional" },
      { id: 3, passed: true, reasoning: "Design is unique — tech_futurist with deep space palette" },
      { id: 4, passed: true, reasoning: "Uses DALL-E images and Pillow infographics" },
      { id: 9, passed: true, reasoning: "Design quality is clean, modern, and visually striking" },
      { id: 11, passed: true, reasoning: "No dead space on any page" },
      { id: 12, passed: true, reasoning: "Author and assistant text is prominent" },
      { id: 19, passed: true, reasoning: "PDF looks like presentation slides" },
      { id: 20, passed: true, reasoning: "Big commanding headers on every page" },
    ],
    informational_only: true,
    duration_seconds: 285,
    headline: "The 13 Dimensions: A Complete Nomotic Architecture for AI Governance",
  },
};

// ═══════════════════════════════════════════════════════════════
//  SEED THE DATABASE
// ═══════════════════════════════════════════════════════════════

function seed() {
  console.log("🌱 Seeding cache for URL:", TEST_URL);
  console.log("   Stages:", Object.keys(STAGE_RESULTS).length);

  // Create a dummy session first (url_cache has foreign key to sessions)
  try {
    dbOps.createSession({
      id: "seed_0001",
      api_session_id: "seed_api",
      thread_id: "seed_thread_001",
      channel_id: "seed_channel",
      user_id: "seed_user",
      source_url: TEST_URL,
      source_text: "",
      pages: 4,
    });
    dbOps.updateSession("seed_0001", {
      status: "complete",
      headline: STAGE_RESULTS.content_extraction.headline,
      publisher: STAGE_RESULTS.content_extraction.publisher,
      combined_score: STAGE_RESULTS.post_validation.combined_score,
      duration_seconds: STAGE_RESULTS.post_validation.duration_seconds,
      pdf_path: PDF_PATH,
    });
    console.log("   Created seed session: seed_0001");
  } catch (e: any) {
    if (e.code === "SQLITE_CONSTRAINT_PRIMARYKEY" || e.message?.includes("UNIQUE")) {
      console.log("   Seed session already exists — updating cache");
    } else {
      throw e;
    }
  }

  // Save to url_cache table
  dbOps.saveUrlCache({
    url: TEST_URL,
    session_id: "seed_0001",
    cached_run_id: "seed_run",
    headline: STAGE_RESULTS.content_extraction.headline,
    publisher: STAGE_RESULTS.content_extraction.publisher,
    stage_results_json: JSON.stringify(STAGE_RESULTS),
    pdf_path: PDF_PATH,
    combined_score: STAGE_RESULTS.post_validation.combined_score,
  });

  // ── Also populate the agent_actions execution ledger ──
  const { populateAgentActionsFromStageResult } = require("./services/agent-wrapper");
  let actionCount = 0;
  for (const [stageKey, stageResult] of Object.entries(STAGE_RESULTS)) {
    try {
      const before = dbOps.getAgentActions("seed_0001").length;
      populateAgentActionsFromStageResult("seed_0001", stageKey, stageResult, "trust");
      const after = dbOps.getAgentActions("seed_0001").length;
      actionCount += (after - before);
    } catch (e) {
      console.warn(`   Could not populate agent_actions for ${stageKey}:`, e);
    }
  }
  console.log(`   Agent actions seeded: ${actionCount} rows in agent_actions table`);

  console.log("✅ Cache seeded successfully!");
  console.log("   URL:", TEST_URL);
  console.log("   PDF:", PDF_PATH);
  console.log("   Score:", STAGE_RESULTS.post_validation.combined_score);
  console.log("\n   You can now run /aibrief with this URL — ZERO API calls will be made.");
}

seed();
