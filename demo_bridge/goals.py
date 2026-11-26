"""Turn a prompt into the goal conditions LIBERO can check, for the Goal scene.

All 10 libero_goal tasks share one table (bowl, plate, cream cheese, wine bottle, stove, cabinet with
three drawers, wine rack), and each task's success is a BDDL goal made of predicates such as
On(bowl, plate). Every object and region those goals name exists in every Goal scene (checked in
Goal task 8 on 26 Nov 2026), so any of them can be evaluated whatever the prompt asked for.

resolve() returns one of three modes:
  scene       the prompt is the scene's own instruction: LIBERO's own success check.
  conditions  the prompt maps to predicates: one of the 10 Goal tasks, or a simple parsed request.
  none        not scored: the user stops the episode or it runs to the step cap.
"""
from __future__ import annotations

import re

GOAL_SUITE = "libero_goal"

# libero_goal BDDL goals, copied from LIBERO's task files (26 Nov 2026).
GOAL_TASKS: dict[str, tuple[int, list[list[str]]]] = {
    "open the middle drawer of the cabinet": (0, [["open", "wooden_cabinet_1_middle_region"]]),
    "put the bowl on the stove": (1, [["on", "akita_black_bowl_1", "flat_stove_1_cook_region"]]),
    "put the wine bottle on top of the cabinet": (2, [["on", "wine_bottle_1", "wooden_cabinet_1_top_side"]]),
    "open the top drawer and put the bowl inside": (3, [["in", "akita_black_bowl_1", "wooden_cabinet_1_top_region"]]),
    "put the bowl on top of the cabinet": (4, [["on", "akita_black_bowl_1", "wooden_cabinet_1_top_side"]]),
    "push the plate to the front of the stove": (5, [["on", "plate_1", "main_table_stove_front_region"]]),
    "put the cream cheese in the bowl": (6, [["on", "cream_cheese_1", "akita_black_bowl_1"]]),
    "turn on the stove": (7, [["turnon", "flat_stove_1"]]),
    "put the bowl on the plate": (8, [["on", "akita_black_bowl_1", "plate_1"]]),
    "put the wine bottle on the rack": (9, [["on", "wine_bottle_1", "wine_rack_1_top_region"]]),
}

# Movable objects: aliases (longest first), state name, words for labels.
OBJECTS = (
    (("cream cheese box", "cream cheese", "cheese"), "cream_cheese_1", "the cream cheese"),
    (("wine bottle", "bottle", "wine"), "wine_bottle_1", "the wine bottle"),
    (("black bowl", "bowl"), "akita_black_bowl_1", "the bowl"),
    (("plate",), "plate_1", "the plate"),
)
DRAWERS = {"top": "wooden_cabinet_1_top_region", "middle": "wooden_cabinet_1_middle_region",
           "bottom": "wooden_cabinet_1_bottom_region"}
# Places you can put something on: aliases, state name, label words.
PLACES = (
    (("front of stove", "front of cooktop"), "main_table_stove_front_region", "in front of the stove"),
    (("top of cabinet", "cabinet top", "cabinet"), "wooden_cabinet_1_top_side", "on top of the cabinet"),
    (("wine rack", "rack"), "wine_rack_1_top_region", "on the rack"),
    (("stove", "cooktop", "burner"), "flat_stove_1_cook_region", "on the stove"),
    (("plate",), "plate_1", "on the plate"),
    (("black bowl", "bowl"), "akita_black_bowl_1", "in the bowl"),
)
PUT_VERBS = ("put", "place", "move", "set", "drop", "bring", "push", "slide", "stack", "transfer")
PICK_VERBS = ("pick up", "pick", "grab", "take", "lift")
FILLER = re.compile(r"\b(the|a|an|please|robot|can you|could you|then|carefully|gently|up)\b")
SUGGESTIONS_EXTRA = (
    "put the cream cheese on the plate",
    "put the wine bottle on the plate",
    "put the cream cheese on the stove",
    "close the middle drawer",
)


def normalize(text: str) -> str:
    text = re.sub(r"[^a-z ]", " ", text.lower())
    return " ".join(text.split())


def _strip(text: str) -> str:
    return " ".join(FILLER.sub(" ", text).split())


def _find(aliases_table, text: str):
    """First alias (by position, then length) in text: (start, end, entry)."""
    best = None
    for entry in aliases_table:
        for alias in entry[0]:
            m = re.search(rf"\b{alias}\b", text)
            if m and (best is None or m.start() < best[0] or (m.start() == best[0] and m.end() > best[1])):
                best = (m.start(), m.end(), entry)
    return best


def _clause(c: str, ctx: dict) -> tuple[list[list[str]], list[str]] | None:
    """One clause -> (conditions, labels); None if it can't be understood. Updates ctx (it / inside)."""
    m = re.fullmatch(r"(?:turn|switch) (on|off) stove|(?:turn|switch) stove (on|off)", c)
    if m:
        on = (m.group(1) or m.group(2)) == "on"
        return [["turnon" if on else "turnoff", "flat_stove_1"]], ["the stove turned " + ("on" if on else "off")]
    m = re.fullmatch(r"(open|close|shut) (top|middle|bottom) drawer(?: of cabinet)?", c)
    if m:
        ctx["drawer"] = DRAWERS[m.group(2)]
        is_open = m.group(1) == "open"
        return ([["open" if is_open else "close", DRAWERS[m.group(2)]]],
                [f"the {m.group(2)} drawer {'open' if is_open else 'closed'}"])
    for verb in PICK_VERBS:
        if c.startswith(verb + " "):
            obj = _find(OBJECTS, c[len(verb):])
            if obj and obj[1] == len(c) - len(verb):  # "pick up X" alone: remember X for "it"
                ctx["it"] = obj[2]
                return [], []
    verb = next((v for v in PUT_VERBS if c.startswith(v + " ")), None)
    if verb is None:
        return None
    rest = c[len(verb):].strip()
    if rest.startswith("it "):
        obj, after = ctx.get("it"), rest[3:]
    else:
        found = _find(OBJECTS, rest)
        if found is None or found[0] != 0:
            return None
        obj, after = found[2], rest[found[1]:].strip()
    if obj is None:
        return None
    ctx["it"] = obj
    after = re.sub(r"^(on top of|onto|on|into|inside of|inside|in|to|next to)\b ?", lambda mm: mm.group(1) + "|", after)
    prep, _, target = after.partition("|")
    target = target.strip()
    if prep == "next to":
        return None
    drawer = re.fullmatch(r"(top|middle|bottom) drawer(?: of cabinet)?", target)
    if drawer:
        ctx["drawer"] = DRAWERS[drawer.group(1)]
        return [["in", obj[1], DRAWERS[drawer.group(1)]]], [f"{obj[2]} in the {drawer.group(1)} drawer"]
    if prep in ("inside", "in", "into", "inside of") and target in ("", "it", "drawer") and ctx.get("drawer"):
        name = next(k for k, v in DRAWERS.items() if v == ctx["drawer"])
        return [["in", obj[1], ctx["drawer"]]], [f"{obj[2]} in the {name} drawer"]
    if prep == "on top of" and target in ("cabinet", "cabinet top"):
        target = "top of cabinet"
    place = _find(PLACES, target)
    if place is None or place[0] != 0 or place[1] != len(target) or not prep:
        return None
    if place[2][1] == obj[1]:
        return None
    return [["on", obj[1], place[2][1]]], [f"{obj[2]} {place[2][2]}"]


def parse(text: str) -> tuple[list[list[str]], str] | None:
    """Free text -> (conditions, label) for the Goal scene, or None."""
    clauses = [c.strip() for c in re.split(r"\band\b|,", _strip(normalize(text))) if c.strip()]
    if not clauses:
        return None
    ctx: dict = {}
    conditions, labels = [], []
    for c in clauses:
        out = _clause(c, ctx)
        if out is None:
            return None
        conditions += out[0]
        labels += out[1]
    if not conditions:
        return None
    # "open the top drawer and put the bowl inside": the drawer only has to be open on the way.
    if any(c[0] == "in" for c in conditions):
        dropped = [c for c in conditions if c[0] == "open" and any(i[0] == "in" and i[2] == c[1] for i in conditions)]
        conditions = [c for c in conditions if c not in dropped]
        labels = [lab for lab in labels if not (lab.endswith(" drawer open") and dropped)]
    return conditions, " and ".join(labels)


def resolve(suite: str, scene_instruction: str, text: str) -> dict:
    """The goal an episode is scored against. Shape is part of the API (see README)."""
    norm = normalize(text)
    if norm == normalize(scene_instruction):
        return {"scored": True, "mode": "scene", "source": "scene's own LIBERO goal",
                "label": scene_instruction, "conditions": None, "reason": None}
    if suite != GOAL_SUITE:
        return {"scored": False, "mode": "none", "source": None, "label": None, "conditions": None,
                "reason": "custom prompts are only scored in the Goal scenes; this scene ignores them"}
    if norm in GOAL_TASKS:
        task, conds = GOAL_TASKS[norm]
        return {"scored": True, "mode": "conditions", "source": f"LIBERO Goal task {task}",
                "label": norm, "conditions": conds, "reason": None}
    parsed = parse(text)
    if parsed is None:
        return {"scored": False, "mode": "none", "source": None, "label": None, "conditions": None,
                "reason": "not understood; try 'put the <object> on the <place>', 'open the top drawer' "
                          "or 'turn on the stove'"}
    conds, label = parsed
    return {"scored": True, "mode": "conditions", "source": "parsed prompt", "label": label,
            "conditions": conds, "reason": None}


def suggestions(suite: str) -> list[str]:
    return list(GOAL_TASKS) + list(SUGGESTIONS_EXTRA) if suite == GOAL_SUITE else []
