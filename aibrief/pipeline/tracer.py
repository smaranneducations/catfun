"""Run Tracer — complete provenance chain for every agent invocation.

For each agent call, records:
  - Fixed strings (from agent_config.json)
  - Variable strings with source attribution (which agent produced them)
  - The agent's output
  - Duration, model, tokens, cost

This creates a complete audit trail: for any agent, you can trace
exactly what came from config vs what came from which other agent.

Each run produces a separate JSON file in aibrief/traces/.
"""
import json
import time
from pathlib import Path
from datetime import datetime
from aibrief import config

TRACER_DIR = config.BASE_DIR / "traces"
TRACER_DIR.mkdir(exist_ok=True)


class RunTracer:
    """Tracks every agent invocation with full input/output provenance."""

    def __init__(self, run_id: str = None, mode: str = "autonomous"):
        self.run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = time.time()
        self.mode = mode
        self.entries: list[dict] = []
        self.agent_outputs: dict = {}   # agent_name -> latest output
        self._current: dict | None = None

    # ═══════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ═══════════════════════════════════════════════════════════════

    def begin_phase(self, phase: str, agent_name: str, agent_codename: str,
                    model: str, fixed_inputs: dict, variable_inputs: dict):
        """Start tracking an agent invocation.

        Args:
            phase: Phase name (e.g. "WorldPulse", "ContentStrategy")
            agent_name: Agent class name (e.g. "WorldPulseScanner")
            agent_codename: Agent persona name (e.g. "Aria")
            model: LLM model used (e.g. "gemini-2.0-flash", "gpt-4o")
            fixed_inputs: Dict of fixed strings from agent_config.json
                {key: value} — these come from the config file
            variable_inputs: Dict of variable inputs from other agents
                {key: {"value": ..., "source_agent": ..., "source_phase": ...}}
        """
        self._current = {
            "phase": phase,
            "agent_name": agent_name,
            "agent_codename": agent_codename,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "inputs": {
                "fixed": {
                    k: {
                        "value": self._truncate_value(v),
                        "source": f"agent_config.json → agents.{agent_name}.fixed_strings.{k}"
                    }
                    for k, v in fixed_inputs.items()
                },
                "variable": {
                    k: {
                        "value": self._truncate_value(v.get("value")),
                        "source_agent": v.get("source_agent", "unknown"),
                        "source_codename": v.get("source_codename", ""),
                        "source_phase": v.get("source_phase", "unknown"),
                    }
                    for k, v in variable_inputs.items()
                },
            },
            "output": None,
            "duration_seconds": None,
            "_t0": time.time(),
        }

    def end_phase(self, output: dict | str, tokens: int = 0, cost: float = 0.0):
        """Record the agent's output and close the phase."""
        if not self._current:
            return

        entry = self._current
        entry["output"] = self._truncate_value(output)
        entry["duration_seconds"] = round(time.time() - entry.pop("_t0"), 2)
        entry["tokens"] = tokens
        entry["cost_usd"] = round(cost, 6)

        # Store for downstream agents to reference
        self.agent_outputs[entry["agent_name"]] = output

        self.entries.append(entry)
        self._current = None

    def log_debate(self, pair_name: str, rounds: list[dict],
                   preparer_name: str = "", reviewer_name: str = "",
                   label: str = ""):
        """Log a preparer/reviewer debate with round-by-round results."""
        self.entries.append({
            "phase": "DEBATE",
            "pair": pair_name,
            "preparer_name": preparer_name,
            "reviewer_name": reviewer_name,
            "label": label,
            "total_rounds": len(rounds),
            "rounds": rounds,
            "timestamp": datetime.now().isoformat(),
        })

    def var_ref(self, source_agent: str, source_codename: str,
                source_phase: str, value) -> dict:
        """Create a variable input reference for tracing.

        Use this when wiring one agent's output as input to another.
        """
        return {
            "value": value,
            "source_agent": source_agent,
            "source_codename": source_codename,
            "source_phase": source_phase,
        }

    def save(self, final_output: dict = None) -> str:
        """Save the complete trace to a JSON file. Returns the file path."""
        trace = {
            "run_id": self.run_id,
            "mode": self.mode,
            "started": datetime.fromtimestamp(self.start_time).isoformat(),
            "completed": datetime.now().isoformat(),
            "total_duration_seconds": round(time.time() - self.start_time, 2),
            "total_agent_calls": len(
                [e for e in self.entries if e.get("phase") != "DEBATE"]),
            "total_debates": len(
                [e for e in self.entries if e.get("phase") == "DEBATE"]),
            "total_tokens": sum(e.get("tokens", 0) for e in self.entries),
            "total_cost_usd": round(
                sum(e.get("cost_usd", 0) for e in self.entries), 4),
            "agent_flow": self._build_flow_summary(),
            "phases": self.entries,
            "final_output": self._truncate_value(final_output) if final_output else {},
        }

        path = TRACER_DIR / f"{self.run_id}.json"
        path.write_text(
            json.dumps(trace, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")

        print(f"\n  [Tracer] Saved: {path}")
        print(f"  [Tracer] {trace['total_agent_calls']} agent calls, "
              f"{trace['total_debates']} debates, "
              f"{trace['total_duration_seconds']:.0f}s total, "
              f"${trace['total_cost_usd']:.4f}")
        return str(path)

    # ═══════════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════════

    def _build_flow_summary(self) -> list[str]:
        """Human-readable flow: agent ← [sources] → output."""
        flow = []
        for entry in self.entries:
            if entry.get("phase") == "DEBATE":
                flow.append(
                    f"  DEBATE: {entry['pair']} "
                    f"({entry['total_rounds']} rounds)")
                continue

            sources = []
            for k, v in entry.get("inputs", {}).get("variable", {}).items():
                src = v.get("source_agent", "config")
                sources.append(f"{src}.{k}")

            src_str = " + ".join(sources) if sources else "config only"
            flow.append(
                f"  {entry['agent_name']} ({entry['agent_codename']}) "
                f"← [{src_str}]")
        return flow

    def _truncate_value(self, obj, max_str=500):
        """Truncate large values for readable trace files."""
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj[:max_str] + "…" if len(obj) > max_str else obj
        if isinstance(obj, dict):
            return {k: self._truncate_value(v, max_str) for k, v in obj.items()}
        if isinstance(obj, list):
            if len(obj) > 15:
                return ([self._truncate_value(x, max_str) for x in obj[:15]]
                        + [f"… +{len(obj) - 15} more"])
            return [self._truncate_value(x, max_str) for x in obj]
        return obj

    def _truncate_value_full(self, obj, max_str=5000):
        """Like _truncate_value but with much higher limit for key outputs."""
        return self._truncate_value(obj, max_str=max_str)
