"""LIBERO scenes for the bridge, built through LeRobot 0.6.1 exactly as live_view_xvla.py does.

MuJoCo's offscreen GL context belongs to the thread that created it, so every call into a scene
(build, reset, step) must run on the bridge's single sim thread.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .goals import GOAL_SUITE, suggestions

SUITES = (
    ("libero_spatial", "Spatial"),
    ("libero_object", "Object"),
    ("libero_goal", "Goal"),
    ("libero_10", "Long"),
)
# The demo scene first: Goal task 8, where free prompts are followed and scored (see goals.py).
RECOMMENDED = (("libero_goal", 8), ("libero_spatial", 0))


def load_scenes(max_steps: int) -> list[dict]:
    from libero.libero import benchmark

    bench = benchmark.get_benchmark_dict()
    rec = set(RECOMMENDED)
    scenes = []
    for suite, label in SUITES:
        b = bench[suite]()
        for task_id in range(b.n_tasks):
            scenes.append({
                "suite": suite,
                "suite_label": label,
                "task_id": task_id,
                "instruction": b.get_task(task_id).language,
                "max_steps": max_steps,
                "recommended": (suite, task_id) in rec,
                "free_prompts": suite == GOAL_SUITE,
                "prompt_suggestions": suggestions(suite),
            })
    first = [s for key in RECOMMENDED for s in scenes if (s["suite"], s["task_id"]) == key]
    return first + [s for s in scenes if not s["recommended"]]


@dataclass
class Observation:
    agentview: np.ndarray  # raw H x W x 3 uint8, upside down as LIBERO renders it
    wrist: np.ndarray
    eef_pos: np.ndarray  # (3,) metres
    eef_mat: np.ndarray  # (3, 3)
    joint_pos: np.ndarray  # (7,) rad


def _unbatch(x, ndim: int) -> np.ndarray:
    if hasattr(x, "detach"):
        x = x.detach().cpu().numpy()
    x = np.asarray(x)
    return x[0] if x.ndim == ndim + 1 else x


class LiberoScene:
    def __init__(self, suite: str, task_id: int, max_steps: int):
        from lerobot.envs.configs import LiberoEnv as LiberoEnvConfig
        from lerobot.envs.factory import make_env

        cfg = LiberoEnvConfig(task=suite, task_ids=[task_id], control_mode="absolute", episode_length=max_steps)
        envs = make_env(cfg, n_envs=1, use_async_envs=False)
        self._vec = next(iter(next(iter(envs.values())).values()))
        # Step the single env directly: the vector wrapper auto-resets once the scene's own goal is met,
        # which would cut short an episode that is scored against a different goal.
        self.env = self._vec.envs[0]
        self.suite = suite
        self.task_id = task_id

    @staticmethod
    def _obs(raw) -> Observation:
        pix = raw["pixels"]
        rs = raw["robot_state"]
        return Observation(
            agentview=np.ascontiguousarray(_unbatch(pix["image"], 3), dtype=np.uint8),
            wrist=np.ascontiguousarray(_unbatch(pix["image2"], 3), dtype=np.uint8),
            eef_pos=_unbatch(rs["eef"]["pos"], 1).astype(np.float32),
            eef_mat=_unbatch(rs["eef"]["mat"], 2).astype(np.float32),
            joint_pos=_unbatch(rs["joints"]["pos"], 1).astype(np.float32),
        )

    def reset(self, seed: int) -> Observation:
        raw, _ = self.env.reset(seed=seed)
        return self._obs(raw)

    def step(self, action: np.ndarray) -> tuple[Observation, float, bool, bool]:
        """Returns (observation, reward, scene_goal_met, horizon_reached)."""
        raw, reward, _terminated, truncated, info = self.env.step(np.asarray(action, dtype=np.float32))
        scene_goal_met = bool(info.get("is_success", False))
        horizon = bool(info.get("done", False)) or bool(truncated)
        return self._obs(raw), float(reward), scene_goal_met, horizon

    def _problem(self):
        env = self.env
        while not hasattr(env, "_env"):
            env = env.env
        inner = env._env
        return inner.env if hasattr(inner, "env") else inner

    def has_states(self, names) -> bool:
        states = self._problem().object_states_dict
        return all(n in states for n in names)

    def check(self, conditions) -> bool:
        """True when every goal predicate holds, using LIBERO's own predicate functions."""
        problem = self._problem()
        return all(bool(problem._eval_predicate(list(c))) for c in conditions)

    def close(self) -> None:
        try:
            self._vec.close()
        except Exception:
            pass


class SceneCache:
    """Builds each scene once and keeps it. Call only from the sim thread.

    LIBERO builds the MuJoCo scene on the first reset (21-39 s measured) and every later reset takes
    about 10 s, so the bridge resets ahead of time (`prepare`) and an episode takes that observation.
    """

    def __init__(self, max_steps: int, factory=LiberoScene):
        self.max_steps = max_steps
        self._factory = factory
        self._scenes: dict[tuple[str, int], object] = {}
        self._prepared: dict[tuple[str, int], tuple[int, Observation]] = {}
        # The scene whose renderer was used last. Building or resetting another scene takes over the
        # offscreen GL context, and a scene stepped without its own reset afterwards renders blank white
        # frames (seen 26 Nov), so a prepared observation is only reused if no other scene ran since.
        self._current: tuple[str, int] | None = None

    def prepare(self, suite: str, task_id: int, seed: int) -> None:
        """Reset the scene now so the next episode with this seed starts at once."""
        obs = self.get(suite, task_id).reset(seed)
        self._current = (suite, task_id)
        self._prepared[(suite, task_id)] = (seed, obs)

    def prepared_observation(self, suite: str, task_id: int, seed: int) -> Observation | None:
        """The starting view of a prepared scene, or None. Read-only: safe from another thread."""
        entry = self._prepared.get((suite, task_id))
        if entry is None or entry[0] != seed or self._current != (suite, task_id):
            return None
        return entry[1]

    def is_prepared(self, suite: str, task_id: int, seed: int) -> bool:
        entry = self._prepared.get((suite, task_id))
        return entry is not None and entry[0] == seed and self._current == (suite, task_id)

    def reset(self, suite: str, task_id: int, seed: int) -> Observation:
        """The prepared observation when it is still valid, otherwise a fresh reset."""
        key = (suite, task_id)
        entry = self._prepared.pop(key, None)
        if entry is not None and entry[0] == seed and self._current == key:
            return entry[1]
        obs = self.get(suite, task_id).reset(seed)
        self._current = key
        return obs

    def is_loaded(self, suite: str, task_id: int) -> bool:
        return (suite, task_id) in self._scenes

    def get(self, suite: str, task_id: int):
        key = (suite, task_id)
        if key not in self._scenes:
            self._scenes[key] = self._factory(suite, task_id, self.max_steps)
            self._current = key
        return self._scenes[key]

    def close(self) -> None:
        for scene in self._scenes.values():
            scene.close()
        self._scenes.clear()
        self._prepared.clear()
