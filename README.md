# Backrooms

A 2D tactical roguelike inspired by The Backrooms, built with [tcod](https://github.com/libtcod/python-tcod).
Sanity and environmental hazards matter more than combat.

## Setup

Requires Python 3.11+. Using [uv](https://github.com/astral-sh/uv):

```sh
uv sync
uv run python run_game.py
```

## Controls

| Key(s) | Action |
| --- | --- |
| Arrow keys / `hjkl` / numpad | Move / attack / talk (bump into a wanderer, hollow, or NPC) |
| `y` `u` `b` `n` / numpad diagonals | Move diagonally |
| `.` / numpad `5` | Wait one turn |
| `Home` | Auto-explore (stops on danger, a level transition, or any keypress) |
| `g` | Pick up an item |
| `i` | Inventory (number keys use/equip/unequip a slot) |
| `r` | Craft (uses the first recipe you have the materials for) |
| `f` | Toggle your light source |
| `x` | Look mode (inspect tiles/entities with the movement keys) |
| `c` / `Tab` | Character screen |
| `Esc` | Close a screen / menu |

## What's here

- **Procedural levels.** Every level is a data-driven `LevelDefinition` (see
  `src/backrooms/data/registrations.py`) rather than special-cased generator code.
  Levels are tagged `INDOOR` or `SPACIOUS` (room size, exit style, column density)
  and `UNSTABLE` or `STABLE` (regenerates fresh every visit vs. a persistent
  Caves-of-Qud-style zone grid you can retrace).
- **Sanity, hunger, and hazards.** Sanity drains ambiently and from hazards
  (spore clouds, unstable floors, unsettling presences), mitigated by willpower.
  Debris piles are a searchable one-shot gamble: a useful item or a jolt of bad luck.
- **NPCs.** Peaceful wanderers can be talked to (bump into them) for flavor
  dialogue. Some levels allow NPC "colonies" — clustered encampments where NPCs
  can interact with each other; others carry an "isolation phenomenon" where
  that never happens.
- **Equipment and crafting.** Four gear slots (head, face, chest, legs) hold
  worn items with passive effects — e.g. a crafted Mask (Duct Tape + Rag) in
  the face slot blocks spore damage/sanity drain entirely. Equipping and
  unequipping both happen from the inventory screen; crafting is its own key.
- **Dev mode.** `--dev` logs each level's layout/entities to stdout on load.
  `--dev-level LEVEL_ID` starts on a specific level with effectively infinite
  HP/sanity, for testing a level directly:

  ```sh
  uv run python run_game.py --dev-level level_2_garage
  ```

## Tests

```sh
uv run pytest
```
