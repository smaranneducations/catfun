"""Base agent class for the FinanceCats multi-agent system."""
import json
from openai import OpenAI
import config


client = OpenAI(api_key=config.OPENAI_API_KEY)


class Agent:
    """Base class for all FinanceCats agents."""

    def __init__(self, name: str, role: str, system_prompt: str, model: str = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model or config.LLM_MODEL
        self.memory = []

    def think(self, task: str, context: dict = None, json_mode: bool = True,
              temperature: float = 0.5, max_tokens: int = 4000) -> dict | str:
        """Ask this agent to think about a task and return structured output."""
        messages = [{"role": "system", "content": self.system_prompt}]

        for mem in self.memory[-5:]:
            messages.append(mem)

        user_content = f"TASK: {task}"
        if context:
            user_content += f"\n\nCONTEXT:\n{json.dumps(context, indent=2, default=str)[:12000]}"

        messages.append({"role": "user", "content": user_content})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        result = response.choices[0].message.content

        self.memory.append({"role": "user", "content": user_content})
        self.memory.append({"role": "assistant", "content": result})

        usage = response.usage
        cost = self._estimate_cost(usage)
        print(f"    [{self.name}] Tokens: {usage.total_tokens} | Est. cost: ${cost:.4f}")

        if json_mode:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"raw": result}
        return result

    def _estimate_cost(self, usage) -> float:
        if "gpt-4o-mini" in self.model:
            return (usage.prompt_tokens * 0.15 + usage.completion_tokens * 0.6) / 1_000_000
        elif "gpt-4o" in self.model:
            return (usage.prompt_tokens * 2.5 + usage.completion_tokens * 10) / 1_000_000
        return 0.0

    def __repr__(self):
        return f"Agent({self.name}, model={self.model})"
