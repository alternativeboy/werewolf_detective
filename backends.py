"""Ways to call a model. Every backend exposes: call(role, system, prompt) -> str.

- cli:  `claude -p` signed in with your Claude plan (Pro/Max). Uses plan usage limits.
- api:  Anthropic Messages API with ANTHROPIC_API_KEY (Console credits).
- mock: no model at all; fake answers for testing the pipeline for free.
"""

import json
import os
import random
import re
import shlex
import subprocess
import time

# Role -> model. Detective and both speaking suspects share a model so the debate is even;
# the default judge is the weaker model (the "weak overseer"). rejudge.py adds other judges.
# Every call() also takes model=... to override the role's default.
MODELS = {
    "cli": {"detective": "sonnet", "wolf": "sonnet", "innocent": "sonnet", "judge": "haiku",
            "lie_judge": "sonnet"},
    "api": {"detective": "claude-sonnet-5-5", "wolf": "claude-sonnet-5-5",
            "innocent": "claude-sonnet-5-5", "judge": "claude-haiku-5-5",
            "lie_judge": "claude-sonnet-5-5"},
    "mock": {"detective": "mock", "wolf": "mock", "innocent": "mock", "judge": "mock",
             "lie_judge": "mock"},
}
# Short names for --judges on the API backend.
API_ALIASES = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}


class CLIBackend:
    """Calls `claude -p`. Unset ANTHROPIC_API_KEY so it bills your plan, not the API."""

    def __init__(self, models=None, extra_args=None, retries=3):
        self.models = models or MODELS["cli"]
        self.extra = extra_args if extra_args is not None else shlex.split(
            os.environ.get("CLAUDE_EXTRA_ARGS", ""))
        self.retries = retries
        if os.environ.get("ANTHROPIC_API_KEY"):
            print("WARNING: ANTHROPIC_API_KEY is set; `claude -p` will bill the API, not your plan.")

    def call(self, role, system, prompt, model=None):
        cmd = ["claude", "-p", "--model", model or self.models[role], "--output-format", "json",
               "--system-prompt", system, *self.extra]
        for attempt in range(self.retries):
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=300)
            if proc.returncode == 0:
                try:
                    return json.loads(proc.stdout)["result"]
                except (json.JSONDecodeError, KeyError):
                    return proc.stdout
            err = (proc.stderr or proc.stdout)[-500:]
            if "limit" in err.lower():
                raise RuntimeError(f"Usage limit reached. Wait for the reset, then rerun "
                                   f"(finished games are kept).\n{err}")
            time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"claude -p failed after {self.retries} tries:\n{err}")


class APIBackend:
    def __init__(self, models=None, temperature=1.0, max_tokens=800):
        import anthropic  # pip install anthropic
        self.client = anthropic.Anthropic()
        self.models = models or MODELS["api"]
        self.temperature, self.max_tokens = temperature, max_tokens

    def call(self, role, system, prompt, model=None):
        model = API_ALIASES.get(model, model) or self.models[role]
        msg = self.client.messages.create(
            model=model, system=system, max_tokens=self.max_tokens,
            temperature=self.temperature, messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if b.type == "text")


class MockBackend:
    """Deterministic fake players, only for testing the plumbing."""

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.models = MODELS["mock"]

    def _suspects(self, prompt):
        m = re.search(r"Suspects: (.+)", prompt)
        return [s.strip() for s in m.group(1).split(",")] if m else ["A", "B", "C", "D"]

    def _evidence(self, prompt):
        return re.findall(r"\[(E\d+)\] (.+)", prompt)

    def call(self, role, system, prompt, model=None):
        sus, ev = self._suspects(prompt), self._evidence(prompt)
        pick = self.rng.choice(sus)
        if '"labels"' in prompt:
            ids = re.findall(r"^(S\d+\.\d+) ", prompt, re.M)
            return json.dumps({"labels": {i: self.rng.choice(["true", "false", "opinion"]) for i in ids}})
        if '"false_statement_ids"' in prompt:
            ids = re.findall(r"^(S\d+\.\d+) ", prompt, re.M)
            return json.dumps({"suspect": pick, "confidence": 60,
                               "false_statement_ids": self.rng.sample(ids, min(1, len(ids)))})
        if '"vote"' in prompt:
            return json.dumps({"vote": pick, "reason": "mock"})
        if '"suspect"' in prompt:
            return json.dumps({"suspect": pick, "confidence": 50, "reasoning": "mock"})
        eid, text = self.rng.choice(ev)
        if role == "wolf" and self.rng.random() < 0.5:
            return f"I am innocent. [E99: someone saw {pick} with a knife]. Look elsewhere."
        return f"I accuse {pick}. Consider [{eid}: {text[:40]}]. That points to {pick}."


def make_backend(name):
    return {"cli": CLIBackend, "api": APIBackend, "mock": MockBackend}[name]()
