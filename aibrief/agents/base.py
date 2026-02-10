"""Base agent with OpenAI + Gemini support and multi-round discussion."""
import json
from openai import OpenAI
from aibrief import config

_openai = OpenAI(api_key=config.OPENAI_API_KEY)
_gemini = None


def _get_gemini():
    global _gemini
    if _gemini is None:
        from google import genai
        _gemini = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini


class Agent:
    def __init__(self, name: str, role: str, system_prompt: str, model: str = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model or "gpt-4o"
        self.memory: list[dict] = []

    @property
    def _is_gemini(self) -> bool:
        return self.model.startswith("gemini")

    # ── public interface ──────────────────────────────────────
    def think(self, task: str, context: dict = None, *,
              json_mode: bool = True, temperature: float = 0.5,
              max_tokens: int = 4096) -> dict | str:
        if self._is_gemini and config.GEMINI_API_KEY:
            return self._gemini(task, context, json_mode, temperature, max_tokens)
        return self._openai(task, context, json_mode, temperature, max_tokens)

    def critique(self, work: dict, author_name: str) -> dict:
        """Review another agent's work and provide structured feedback."""
        return self.think(
            f"Critically review {author_name}'s work. Be constructive but honest. "
            f"Identify strengths, weaknesses, missing angles, factual concerns, "
            f"and tone issues. Score 1-10.",
            context={"work_to_review": work},
        )

    def respond_to_feedback(self, original: dict, feedback: dict) -> dict:
        """Revise own work based on editorial feedback."""
        return self.think(
            "Revise your analysis based on this editorial feedback. "
            "Address every point raised. Improve depth and quality.",
            context={"your_original_work": original, "feedback": feedback},
        )

    # ── OpenAI ────────────────────────────────────────────────
    def _openai(self, task, context, json_mode, temperature, max_tokens):
        messages = [{"role": "system", "content": self.system_prompt}]
        for m in self.memory[-6:]:
            messages.append(m)
        user = f"TASK: {task}"
        if context:
            user += f"\n\nCONTEXT:\n{json.dumps(context, indent=2, default=str)[:15000]}"
        messages.append({"role": "user", "content": user})

        kw = dict(model=self.model if not self._is_gemini else "gpt-4o",
                  messages=messages, temperature=temperature, max_tokens=max_tokens)
        if json_mode:
            kw["response_format"] = {"type": "json_object"}

        resp = _openai.chat.completions.create(**kw)
        txt = resp.choices[0].message.content
        self.memory.append({"role": "user", "content": user})
        self.memory.append({"role": "assistant", "content": txt})
        u = resp.usage
        cost = (u.prompt_tokens * 2.5 + u.completion_tokens * 10) / 1e6
        print(f"    [{self.name}] GPT-4o | {u.total_tokens} tok | ${cost:.4f}")
        if json_mode:
            try:
                parsed = json.loads(txt)
                if isinstance(parsed, list):
                    parsed = parsed[0] if parsed else {}
                return parsed
            except json.JSONDecodeError:
                return {"raw": txt}
        return txt

    # ── Gemini ────────────────────────────────────────────────
    def _gemini(self, task, context, json_mode, temperature, max_tokens):
        from google.genai import types
        client = _get_gemini()

        user = f"TASK: {task}"
        if context:
            user += f"\n\nCONTEXT:\n{json.dumps(context, indent=2, default=str)[:15000]}"
        mem = ""
        for m in self.memory[-6:]:
            mem += f"\n{m['role'].upper()}: {m['content']}\n"
        if mem:
            user = f"PREVIOUS:{mem}\n\n{user}"
        if json_mode:
            user += "\n\nRespond with valid JSON only."

        cfg = types.GenerateContentConfig(
            temperature=temperature, max_output_tokens=max_tokens,
            system_instruction=self.system_prompt,
        )
        if json_mode:
            cfg.response_mime_type = "application/json"

        try:
            resp = client.models.generate_content(
                model=self.model, contents=user, config=cfg)
            txt = resp.text
            self.memory.append({"role": "user", "content": f"TASK: {task}"})
            self.memory.append({"role": "assistant", "content": txt})
            it = getattr(resp.usage_metadata, 'prompt_token_count', 0) or 0
            ot = getattr(resp.usage_metadata, 'candidates_token_count', 0) or 0
            cost = (it * 0.10 + ot * 0.40) / 1e6
            print(f"    [{self.name}] Gemini Flash | {it+ot} tok | ${cost:.6f}")
            if json_mode:
                try:
                    parsed = json.loads(txt)
                    if isinstance(parsed, list):
                        parsed = parsed[0] if parsed else {}
                    return parsed
                except json.JSONDecodeError:
                    c = txt.strip()
                    if c.startswith("```"):
                        c = "\n".join(l for l in c.split("\n")
                                      if not l.strip().startswith("```"))
                    try:
                        parsed = json.loads(c)
                        if isinstance(parsed, list):
                            parsed = parsed[0] if parsed else {}
                        return parsed
                    except json.JSONDecodeError:
                        print(f"    [{self.name}] Bad JSON → falling back to OpenAI")
                        return self._openai(task, context, json_mode, temperature, max_tokens)
            return txt
        except Exception as e:
            print(f"    [{self.name}] Gemini error: {e} → falling back to OpenAI")
            return self._openai(task, context, json_mode, temperature, max_tokens)
