"""Base agent class for the FinanceCats multi-agent system.

V3: Supports both OpenAI (GPT-4o) and Google Gemini (Flash/Pro) models.
  - Model is selected per-agent in config.py
  - Agents using "gemini-*" models go through Google's genai SDK
  - Agents using "gpt-*" models go through OpenAI's API
  - Both return structured JSON output
  - Gemini falls back to OpenAI on error
"""
import json
from openai import OpenAI
import config

# OpenAI client (always available)
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

# Gemini client (created lazily)
_gemini_client = None


def _get_gemini_client():
    """Get or create the Gemini client (lazy init)."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini_client


class Agent:
    """Base class for all FinanceCats agents.

    Supports both OpenAI and Gemini models transparently.
    """

    def __init__(self, name: str, role: str, system_prompt: str, model: str = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model or config.LLM_MODEL
        self.memory = []

    @property
    def is_gemini(self) -> bool:
        """Check if this agent uses a Gemini model."""
        return self.model.startswith("gemini")

    def think(self, task: str, context: dict = None, json_mode: bool = True,
              temperature: float = 0.5, max_tokens: int = 4000) -> dict | str:
        """Ask this agent to think about a task and return structured output.

        Automatically routes to OpenAI or Gemini based on the model name.
        """
        if self.is_gemini and config.GEMINI_API_KEY:
            return self._think_gemini(task, context, json_mode, temperature, max_tokens)
        else:
            return self._think_openai(task, context, json_mode, temperature, max_tokens)

    def _think_openai(self, task: str, context: dict = None, json_mode: bool = True,
                      temperature: float = 0.5, max_tokens: int = 4000) -> dict | str:
        """Think using OpenAI GPT models."""
        # Use GPT-4o as fallback if Gemini was requested but no key
        model = self.model if not self.is_gemini else config.LLM_MODEL

        messages = [{"role": "system", "content": self.system_prompt}]

        for mem in self.memory[-5:]:
            messages.append(mem)

        user_content = f"TASK: {task}"
        if context:
            user_content += f"\n\nCONTEXT:\n{json.dumps(context, indent=2, default=str)[:12000]}"

        messages.append({"role": "user", "content": user_content})

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = openai_client.chat.completions.create(**kwargs)
        result = response.choices[0].message.content

        self.memory.append({"role": "user", "content": user_content})
        self.memory.append({"role": "assistant", "content": result})

        usage = response.usage
        cost = self._estimate_cost_openai(usage, model)
        print(f"    [{self.name}] OpenAI {model} | Tokens: {usage.total_tokens} | ${cost:.4f}")

        if json_mode:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"raw": result}
        return result

    def _think_gemini(self, task: str, context: dict = None, json_mode: bool = True,
                      temperature: float = 0.5, max_tokens: int = 4000) -> dict | str:
        """Think using Google Gemini models (new google.genai SDK)."""
        from google.genai import types

        client = _get_gemini_client()

        # Build prompt (Gemini uses contents, system_instruction is separate)
        user_content = f"TASK: {task}"
        if context:
            user_content += f"\n\nCONTEXT:\n{json.dumps(context, indent=2, default=str)[:12000]}"

        # Add memory context
        memory_text = ""
        for mem in self.memory[-5:]:
            role = mem.get("role", "user")
            content = mem.get("content", "")
            memory_text += f"\n{role.upper()}: {content}\n"

        if memory_text:
            user_content = f"PREVIOUS CONVERSATION:{memory_text}\n\n{user_content}"

        if json_mode:
            user_content += "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no code fences."

        # Generation config
        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=self.system_prompt,
        )
        if json_mode:
            gen_config.response_mime_type = "application/json"

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_content,
                config=gen_config,
            )
            result = response.text

            # Track memory
            self.memory.append({"role": "user", "content": f"TASK: {task}"})
            self.memory.append({"role": "assistant", "content": result})

            # Estimate cost
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            total_tokens = input_tokens + output_tokens
            cost = self._estimate_cost_gemini(input_tokens, output_tokens)
            print(f"    [{self.name}] Gemini {self.model} | Tokens: {total_tokens} | ${cost:.4f}")

            if json_mode:
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    # Try to extract JSON from the response
                    cleaned = result.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.split("\n")
                        lines = [l for l in lines if not l.strip().startswith("```")]
                        cleaned = "\n".join(lines)
                    try:
                        return json.loads(cleaned)
                    except json.JSONDecodeError:
                        print(f"    [{self.name}] WARNING: Gemini returned invalid JSON, "
                              f"falling back to OpenAI")
                        return self._think_openai(task, context, json_mode, temperature, max_tokens)
            return result

        except Exception as e:
            print(f"    [{self.name}] Gemini error: {e}")
            print(f"    [{self.name}] Falling back to OpenAI...")
            return self._think_openai(task, context, json_mode, temperature, max_tokens)

    def _estimate_cost_openai(self, usage, model: str) -> float:
        """Estimate OpenAI API cost."""
        if "gpt-4o-mini" in model:
            return (usage.prompt_tokens * 0.15 + usage.completion_tokens * 0.6) / 1_000_000
        elif "gpt-4o" in model:
            return (usage.prompt_tokens * 2.5 + usage.completion_tokens * 10) / 1_000_000
        return 0.0

    def _estimate_cost_gemini(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate Gemini API cost."""
        if "flash" in self.model:
            # Gemini 2.0 Flash: $0.10/1M input, $0.40/1M output
            return (input_tokens * 0.10 + output_tokens * 0.40) / 1_000_000
        elif "pro" in self.model:
            # Gemini Pro: $1.25/1M input, $5.00/1M output
            return (input_tokens * 1.25 + output_tokens * 5.00) / 1_000_000
        return 0.0

    def __repr__(self):
        return f"Agent({self.name}, model={self.model})"
