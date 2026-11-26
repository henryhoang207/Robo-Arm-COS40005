"""Prompt -> goal conditions for the Goal scene."""
import pytest

from demo_bridge.goals import GOAL_TASKS, parse, resolve, suggestions

BOWL, CHEESE, WINE, PLATE = "akita_black_bowl_1", "cream_cheese_1", "wine_bottle_1", "plate_1"
STOVE, TOP, RACK, FRONT = "flat_stove_1_cook_region", "wooden_cabinet_1_top_side", "wine_rack_1_top_region", "main_table_stove_front_region"


@pytest.mark.parametrize("instruction", list(GOAL_TASKS))
def test_parser_agrees_with_every_libero_goal_task(instruction):
    """The parser alone reproduces all 10 BDDL goals, so near-paraphrases score the same way."""
    assert parse(instruction)[0] == GOAL_TASKS[instruction][1]


@pytest.mark.parametrize("text,conditions,label", [
    ("Put the cream cheese on the plate.", [["on", CHEESE, PLATE]], "the cream cheese on the plate"),
    ("place the wine bottle onto the plate", [["on", WINE, PLATE]], "the wine bottle on the plate"),
    ("put the cream-cheese box on the stove please", [["on", CHEESE, STOVE]], "the cream cheese on the stove"),
    ("move the bowl to the front of the stove", [["on", BOWL, FRONT]], "the bowl in front of the stove"),
    ("put the bowl on the wine rack", [["on", BOWL, RACK]], "the bowl on the rack"),
    ("put the cream cheese on top of the cabinet", [["on", CHEESE, TOP]], "the cream cheese on top of the cabinet"),
    ("put the cream cheese in the bowl", [["on", CHEESE, BOWL]], "the cream cheese in the bowl"),
    ("pick up the bowl and place it on the stove", [["on", BOWL, STOVE]], "the bowl on the stove"),
    ("open the bottom drawer and put the cream cheese inside",
     [["in", CHEESE, "wooden_cabinet_1_bottom_region"]], "the cream cheese in the bottom drawer"),
    ("put the bowl in the middle drawer", [["in", BOWL, "wooden_cabinet_1_middle_region"]], "the bowl in the middle drawer"),
    ("close the top drawer", [["close", "wooden_cabinet_1_top_region"]], "the top drawer closed"),
    ("switch the stove off", [["turnoff", "flat_stove_1"]], "the stove turned off"),
    ("turn on the stove and put the bowl on the plate", [["turnon", "flat_stove_1"], ["on", BOWL, PLATE]],
     "the stove turned on and the bowl on the plate"),
])
def test_parses_new_requests(text, conditions, label):
    assert parse(text) == (conditions, label)


@pytest.mark.parametrize("text", [
    "wave hello", "put the bowl", "put the plate on the plate", "put the ramekin on the plate",
    "put the bowl next to the plate", "open the fridge", "", "and",
])
def test_rejects_what_it_cannot_check(text):
    assert parse(text) is None


def test_resolve_modes():
    own = resolve("libero_goal", "put the bowl on the plate", "Put the bowl on the plate")
    assert own["mode"] == "scene" and own["scored"]
    task = resolve("libero_goal", "put the bowl on the plate", "turn on the stove")
    assert task["mode"] == "conditions" and task["source"] == "LIBERO Goal task 7"
    new = resolve("libero_goal", "put the bowl on the plate", "put the wine bottle on the plate")
    assert new["source"] == "parsed prompt" and new["conditions"] == [["on", WINE, PLATE]]
    nope = resolve("libero_goal", "put the bowl on the plate", "dance")
    assert nope["mode"] == "none" and not nope["scored"] and nope["reason"]
    spatial = resolve("libero_spatial", "pick up the black bowl", "put the bowl on the stove")
    assert spatial["mode"] == "none" and "Goal scenes" in spatial["reason"]


def test_prepared_scene_is_not_reused_after_another_scene_ran():
    """Another scene taking the GL context made the prepared one render blank (26 Nov)."""
    from demo_bridge.sim import SceneCache

    resets = []

    class Scene:
        def __init__(self, suite, task_id, max_steps):
            self.key = (suite, task_id)

        def reset(self, seed):
            resets.append(self.key)
            return object()

    cache = SceneCache(100, factory=Scene)
    cache.prepare("libero_goal", 8, 1000)
    cache.prepare("libero_spatial", 0, 1000)
    assert not cache.is_prepared("libero_goal", 8, 1000) and cache.is_prepared("libero_spatial", 0, 1000)
    cache.reset("libero_goal", 8, 1000)
    assert resets == [("libero_goal", 8), ("libero_spatial", 0), ("libero_goal", 8)]  # fresh reset, not reused
    cache.prepare("libero_goal", 8, 1000)
    cache.reset("libero_goal", 8, 1000)
    assert len(resets) == 4  # still current: reused


def test_suggestions_only_for_goal_suite():
    assert len(suggestions("libero_goal")) == 14 and suggestions("libero_spatial") == []
    for s in suggestions("libero_goal"):
        assert parse(s) is not None
