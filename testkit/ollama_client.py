"""Two ways to get a model response:

- OllamaClient calls a model running locally through Ollama's REST API
  (POST http://localhost:11434/api/chat). Nothing leaves the machine.
- ReplayClient reads saved responses from disk, so the scoring can be
  demonstrated (and tested) without Ollama installed.

Both return the same thing: Ollama's non-streaming /api/chat response as a dict.
"""

import json
import urllib.request
from pathlib import Path

DEFAULT_HOST = "http://localhost:11434"


class OllamaClient:
    def __init__(self, model, host=DEFAULT_HOST, timeout=600, seed=42):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.seed = seed

    def build_payload(self, messages, schema):
        return {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema,
            # Temperature 0 and a fixed seed make reruns as repeatable as the
            # model allows -- the same idea as a validated workbook.
            "options": {"temperature": 0, "seed": self.seed},
        }

    def chat(self, engagement_id, messages, schema):
        body = json.dumps(self.build_payload(messages, schema)).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


class ReplayClient:
    """Serves <replay_dir>/<engagement_id>.json instead of calling a model."""

    def __init__(self, replay_dir):
        self.replay_dir = Path(replay_dir)
        self.model = self.replay_dir.name

    def chat(self, engagement_id, messages, schema):
        path = self.replay_dir / f"{engagement_id}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"No recorded response for {engagement_id} in {self.replay_dir}")
        return json.loads(path.read_text(encoding="utf-8"))
