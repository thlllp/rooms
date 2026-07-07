"""The content file: every level/sublevel the game knows about is declared
here as one LevelDefinition each. Importing this module populates
world.level_registry.LEVEL_REGISTRY as a side effect -- the engine never
references a generator function directly, only registry lookups by id.
"""

from __future__ import annotations

from backrooms.constants import Color
from backrooms.entity.components.ai import HostileAI, WanderingAI
from backrooms.entity.components.consumable import (
    make_fuel_restore_item,
    make_hp_for_sanity_item,
    make_hp_restore_item,
    make_hunger_restore_item,
    make_sanity_restore_item,
)
from backrooms.entity.components.dialogue import DialogueComponent
from backrooms.entity.components.equippable import EquippableComponent
from backrooms.entity.components.fighter import Fighter
from backrooms.entity.components.hazard import LootEntry, make_debris_pile, make_spore_zone, make_unstable_floor
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.procgen.generator_office import generate_office_level
from backrooms.world import tile_types
from backrooms.world.crafting import CraftingRecipe, register_recipe
from backrooms.world.level_registry import (
    DestinationOption,
    LevelDefinition,
    LevelKind,
    LevelStability,
    SpawnEntry,
    TransitionRule,
    TriggerKind,
    register,
)


def _spawn_spore_zone() -> Entity:
    return Entity(
        0,
        0,
        char='"',
        color=Color.SPORE_PINK,
        name="Spore Cloud",
        render_order=RenderOrder.HAZARD,
        hazard=make_spore_zone(radius=1, severity=2.0),
    )


def _spawn_unstable_floor() -> Entity:
    return Entity(
        0,
        0,
        char="=",
        color=Color.WARNING,
        name="Unstable Floor",
        render_order=RenderOrder.HAZARD,
        hazard=make_unstable_floor(collapse_threshold=4, event_flag="floor_collapsed"),
    )


def _spawn_wanderer() -> Entity:
    return Entity(
        0,
        0,
        char="?",
        color=(150, 130, 170),
        name="Wandering Presence",
        blocks_movement=True,
        render_order=RenderOrder.ACTOR,
        causes_dread=True,
        dread_radius=5,
        ai=WanderingAI(perception_radius=8),
        fighter=Fighter(hp=1, endurance=0, power=0),
    )


def _spawn_hollow() -> Entity:
    return Entity(
        0,
        0,
        char="h",
        color=(180, 60, 60),
        name="Hollow",
        blocks_movement=True,
        render_order=RenderOrder.ACTOR,
        causes_dread=True,
        dread_radius=4,
        ai=HostileAI(perception_radius=8),
        fighter=Fighter(hp=6, endurance=0, power=2, xp_reward=10),
    )


def _spawn_almond_water() -> Entity:
    return Entity(
        0,
        0,
        char="!",
        color=(230, 222, 190),
        name="Almond Water Bottle",
        render_order=RenderOrder.ITEM,
        consumable=make_sanity_restore_item(30.0),
    )


# Debris-pile loot for level_1_office (see LEVEL_1_OFFICE's hazard_table) --
# a small pool of possible finds instead of always the same one item.
def _spawn_first_aid_kit() -> Entity:
    return Entity(
        0, 0, char="+", color=(220, 60, 60), name="First Aid Kit", render_order=RenderOrder.ITEM,
        consumable=make_hp_restore_item(15.0),
    )


def _spawn_rag() -> Entity:
    return Entity(
        0, 0, char="~", color=(200, 195, 180), name="Rag", render_order=RenderOrder.ITEM,
        consumable=make_hp_restore_item(5.0),
    )


def _spawn_liquid_pain() -> Entity:
    return Entity(
        0, 0, char="!", color=(140, 40, 90), name="Liquid Pain", render_order=RenderOrder.ITEM,
        consumable=make_hp_for_sanity_item(hp_amount=20.0, sanity_cost=10.0),
    )


def _spawn_duct_tape() -> Entity:
    return Entity(
        0, 0, char="-", color=(150, 150, 40), name="Duct Tape", render_order=RenderOrder.ITEM,
        consumable=make_sanity_restore_item(15.0),
    )


def _spawn_canned_food() -> Entity:
    return Entity(
        0, 0, char="c", color=(180, 150, 60), name="Canned Food", render_order=RenderOrder.ITEM,
        consumable=make_hunger_restore_item(35.0),
    )


# Refuels a light source (see LightSourceComponent/tick_light_fuel) -- before
# this, a light that burned out at fuel=0 had no way back; ToggleLightAction
# would just refuse forever.
def _spawn_lighter_fluid() -> Entity:
    return Entity(
        0, 0, char="!", color=(230, 160, 60), name="Lighter Fluid", render_order=RenderOrder.ITEM,
        consumable=make_fuel_restore_item(50.0),
    )


# Crafted, not found -- see the recipe registered below. Face-slot
# equipment: full protection against spore damage/sanity drain while worn
# (see hazard.tick_spore_damage), no effect on anything else.
def _spawn_mask() -> Entity:
    return Entity(
        0, 0, char="[", color=(90, 90, 100), name="Mask", render_order=RenderOrder.ITEM,
        equippable=EquippableComponent(slot="face", spore_resistance=1.0),
    )


register_recipe(CraftingRecipe(name="Mask", ingredients=("Duct Tape", "Rag"), result_factory=_spawn_mask))


# Back-slot equipment -- no passive protection, just extra carrying room
# (see EquippableComponent.capacity_bonus/EquipmentComponent.capacity_bonus,
# read by actions._effective_capacity). Found in debris piles like any other
# item, not crafted.
def _spawn_simple_backpack() -> Entity:
    return Entity(
        0, 0, char="B", color=(120, 100, 70), name="Simple Backpack", render_order=RenderOrder.ITEM,
        equippable=EquippableComponent(slot="back", capacity_bonus=5),
    )


def _spawn_hiking_bag() -> Entity:
    return Entity(
        0, 0, char="H", color=(70, 110, 80), name="Hiking Bag", render_order=RenderOrder.ITEM,
        equippable=EquippableComponent(slot="back", capacity_bonus=10),
    )


# Peaceful NPC -- the starting slice of the interaction framework. Reuses
# WanderingAI (already non-hostile, never attacks) rather than a new AI
# class; the only thing distinguishing it from a hostile wanderer is
# causes_dread=False (just another person, not unsettling) plus dialogue.
# Only ever registered on levels with isolation=False -- currently just
# LEVEL_2_SETTLEMENT's spawn_table (see systems/npc_social.py).
def _spawn_colonist() -> Entity:
    return Entity(
        0,
        0,
        char="p",
        color=(200, 175, 140),
        name="Survivor",
        blocks_movement=True,
        render_order=RenderOrder.ACTOR,
        ai=WanderingAI(perception_radius=8),
        dialogue=DialogueComponent(
            lines=(
                "You're... you're actually real?",
                "I've stopped counting the days.",
                "Don't trust the ones that look like almost-people.",
                "We stick together out here. Safer that way.",
                "Have you seen the walls move, or is it just me?",
            )
        ),
    )


# Placed next to a settlement door (see LevelDefinition.settlement_door_chance/
# sign_factory) -- purely a marker, reuses the dialogue/TalkAction bump
# mechanic already built for NPCs rather than a new "read this" interaction.
def _spawn_settlement_sign() -> Entity:
    return Entity(
        0,
        0,
        char="i",
        color=Color.SIGN,
        name="Sign",
        blocks_movement=True,
        render_order=RenderOrder.ACTOR,
        dialogue=DialogueComponent(lines=("A hand-painted sign: \"SURVIVORS -- SAFE HAVEN THROUGH THE DOOR.\"",)),
    )


# Purely decorative clutter -- see LevelDefinition.furniture_table. Static,
# no hazard/ai/etc, just something that's there and blocks a tile. Unlike
# _make_column, deliberately doesn't set blocks_sight -- desk/cabinet height
# clutter isn't meant to create the same tactical sightline gaps a
# floor-to-ceiling support column does.
def _spawn_desk() -> Entity:
    return Entity(0, 0, char="d", color=(120, 90, 60), name="Desk", blocks_movement=True, render_order=RenderOrder.HAZARD)


def _spawn_filing_cabinet() -> Entity:
    return Entity(
        0, 0, char="f", color=(100, 100, 110), name="Filing Cabinet", blocks_movement=True, render_order=RenderOrder.HAZARD
    )


# Same purely-decorative shape as _spawn_desk/_spawn_filing_cabinet, but
# placed near a settlement's inn room specifically (see
# LevelDefinition.inn_furniture_factories/Engine._generate_map) rather than
# scattered anywhere via furniture_table -- what makes an inn read as an inn
# instead of just a differently-colored floor tile.
def _spawn_bedroll() -> Entity:
    return Entity(0, 0, char="b", color=(150, 110, 70), name="Bedroll", blocks_movement=True, render_order=RenderOrder.HAZARD)


def _spawn_cooking_pot() -> Entity:
    return Entity(
        0, 0, char="o", color=(90, 90, 95), name="Cooking Pot", blocks_movement=True, render_order=RenderOrder.HAZARD
    )


# Searchable, one-shot: resolves into either a dropped item or a sanity hit
# the moment the player steps onto it, then removes itself (see
# make_debris_pile/tick_debris_pile). Not on level_0_office -- these are
# meant for the levels the player is stuck looping through.
def _spawn_debris_pile_office() -> Entity:
    return Entity(
        0,
        0,
        char="%",
        color=Color.DEBRIS,
        name="Debris Pile",
        render_order=RenderOrder.HAZARD,
        hazard=make_debris_pile(
            item_factories=(
                LootEntry(_spawn_almond_water),
                LootEntry(_spawn_first_aid_kit),
                LootEntry(_spawn_rag),
                LootEntry(_spawn_liquid_pain),
                LootEntry(_spawn_duct_tape),
                LootEntry(_spawn_canned_food),
                LootEntry(_spawn_lighter_fluid),
                # Fairly rare here -- weight 0.15 against everything else's
                # default 1.0, so it turns up roughly 1/7th as often as any
                # one of the common items above. No Hiking Bag on this pool
                # at all -- that one's exclusive to the garage's debris (see
                # _spawn_debris_pile_garage).
                LootEntry(_spawn_simple_backpack, weight=0.15),
            ),
            good_chance=0.6,
            sanity_penalty=10.0,
        ),
    )


def _spawn_debris_pile_garage() -> Entity:
    return Entity(
        0,
        0,
        char="%",
        color=Color.DEBRIS,
        name="Debris Pile",
        render_order=RenderOrder.HAZARD,
        hazard=make_debris_pile(
            item_factories=(
                LootEntry(_spawn_almond_water),
                LootEntry(_spawn_canned_food),
                LootEntry(_spawn_lighter_fluid),
                # Slightly more common than the office debris pool's 0.15 --
                # still rarer than an ordinary find, just not as rare here.
                LootEntry(_spawn_simple_backpack, weight=0.3),
                # Turns up randomly alongside everything else -- rare, and
                # only ever found here, not in the office's debris pool.
                LootEntry(_spawn_hiking_bag, weight=0.2),
            ),
            good_chance=0.6,
            sanity_penalty=10.0,
        ),
    )


LEVEL_OFFICE = register(
    LevelDefinition(
        id="level_0_office",
        display_name="Level 0",
        generator=generate_office_level,
        # ~1 sanity per 5 turns before willpower mitigation (SanityComponent.drain
        # subtracts willpower from the combined total each turn) -- the intended
        # early-game baseline; deeper levels should drain faster than this.
        ambient_sanity_drain=0.2,
        is_well_lit=True,
        is_entry_level=True,
        kind=LevelKind.INDOOR,
        stability=LevelStability.UNSTABLE,
        isolation=True,
        spawn_table=(
            SpawnEntry(factory=_spawn_wanderer, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_hollow, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_almond_water, weight=1.0, min_count=1, max_count=2),
        ),
        hazard_table=(
            SpawnEntry(factory=_spawn_spore_zone, weight=1.0, min_count=1, max_count=2),
            SpawnEntry(factory=_spawn_unstable_floor, weight=1.0, min_count=1, max_count=1),
        ),
        transition_rules=(
            TransitionRule(
                trigger=TriggerKind.EVENT_FLAG_SET,
                event_flag="floor_collapsed",
                destinations=(DestinationOption("level_1_office", 1.0),),
                message="The floor gives way beneath your feet entirely.",
            ),
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="stairs_down",
                destinations=(DestinationOption("level_1_office", 1.0),),
                message="You take the stairs down.",
            ),
        ),
    )
)

# The only level past the entry, for now -- no flooded/cave sublevels. Its
# own exit feature loops back into a freshly generated instance of itself
# (see generate_office_level, called fresh by load_level() every time), so
# past level 0 the game is an endless procedurally-regenerating office maze
# rather than a fixed sequence of distinct areas. door_exit_chance gives that
# feature a 50/50 chance of being a door in the wall instead of the usual
# floor-standing stairs -- same effect, different flavor (see the matching
# door_exit rule below and TILE_DESCRIPTIONS["door_exit"] in rendering/ui.py).
LEVEL_1_OFFICE = register(
    LevelDefinition(
        id="level_1_office",
        display_name="Level 1",
        generator=generate_office_level,
        ambient_sanity_drain=0.2,
        is_well_lit=True,
        door_exit_chance=0.5,
        kind=LevelKind.INDOOR,
        stability=LevelStability.UNSTABLE,
        isolation=True,
        spawn_table=(
            SpawnEntry(factory=_spawn_wanderer, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_hollow, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_almond_water, weight=1.0, min_count=1, max_count=2),
        ),
        hazard_table=(
            SpawnEntry(factory=_spawn_spore_zone, weight=1.0, min_count=1, max_count=2),
            SpawnEntry(factory=_spawn_unstable_floor, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_debris_pile_office, weight=1.0, min_count=1, max_count=1),
        ),
        # Empty on a fresh visit -- accumulates the longer you keep
        # regenerating this same level in a row (see Engine.level_repeat_streak,
        # spawner.spawn_from_table's bonus_max).
        furniture_table=(
            SpawnEntry(factory=_spawn_desk, weight=1.0, min_count=0, max_count=0),
            SpawnEntry(factory=_spawn_filing_cabinet, weight=1.0, min_count=0, max_count=0),
        ),
        transition_rules=(
            TransitionRule(
                trigger=TriggerKind.EVENT_FLAG_SET,
                event_flag="floor_collapsed",
                destinations=(DestinationOption("level_1_office", 1.0),),
                message="The floor gives way beneath your feet entirely.",
            ),
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="stairs_down",
                destinations=(DestinationOption("level_1_office", 1.0),),
                message="You take the stairs down.",
            ),
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="door_exit",
                # Chance of leading to level_2_garage instead of another
                # level_1_office loop grows with Engine.level_repeat_streak
                # (how many times in a row you've regenerated level_1_office)
                # -- 0% the first time you find a door, rising the longer
                # you've been stuck repeating this level type. See
                # DestinationOption.weight_per_streak.
                destinations=(
                    DestinationOption("level_1_office", weight=1.0),
                    DestinationOption("level_2_garage", weight=0.0, weight_per_streak=0.25),
                ),
                message="You open the door and step through.",
            ),
        ),
    )
)

# A third look entirely -- a giant car garage, grey concrete instead of the
# office levels' warm wallpaper/carpet (see LevelDefinition.wall_tile/
# floor_tile and tile_types.GARAGE_WALL/GARAGE_FLOOR). Tagged SPACIOUS
# (see LevelKind/LEVEL_STYLES) rather than INDOOR like level_0/level_1:
# much bigger rooms packed to fill the map, fewer/shorter corridors, a
# scattered grid of support columns per room instead of one dead center, and
# no stairs/door exit tile -- walking off any edge of the map is the way out,
# Caves-of-Qud style (see actions.MovementAction._handle_edge,
# generator_office.py's forced one-room-per-wall placement, and the
# map_edge_exited rule below). STABLE: each direction you exit through leads
# to its own persistent zone -- walk back the way you came and it's the SAME
# garage you left (same layout, same remaining loot/enemies); a wall you
# haven't crossed before generates a brand new one (see
# Engine._load_stable_zone). Reachable from level_1_office's door (see the
# destinations above).
LEVEL_2_GARAGE = register(
    LevelDefinition(
        id="level_2_garage",
        display_name="Level 2",
        generator=generate_office_level,
        ambient_sanity_drain=0.2,
        is_well_lit=True,
        wall_tile=tile_types.GARAGE_WALL,
        floor_tile=tile_types.GARAGE_FLOOR,
        kind=LevelKind.SPACIOUS,
        stability=LevelStability.STABLE,
        # Colonies don't happen out in the open garage itself -- isolation
        # stays True here. A settlement (where isolation=False and NPCs
        # actually gather/interact) is a separate small sublevel behind a
        # door, see settlement_door_chance/sign_factory below and
        # LEVEL_2_SETTLEMENT.
        spawn_table=(
            SpawnEntry(factory=_spawn_wanderer, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_hollow, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_almond_water, weight=1.0, min_count=1, max_count=2),
        ),
        # No floor hazards (spore cloud, unstable floor) here -- just the
        # searchable debris pile. Guaranteed at least one per visit
        # (min_count=1), growing with Engine.level_repeat_streak same as
        # every other SpawnEntry table.
        hazard_table=(SpawnEntry(factory=_spawn_debris_pile_garage, weight=1.0, min_count=1, max_count=1),),
        # A settlement is a bonus find, not guaranteed every zone -- a sign
        # (see sign_factory) marks it from a distance before the door itself
        # is reached (see generator_office._place_settlement_door).
        settlement_door_chance=0.3,
        sign_factory=_spawn_settlement_sign,
        # A bonus find, not guaranteed every zone (same idea as
        # settlement_door_chance) -- a long, narrow hallway running straight
        # from spawn to one (randomly chosen per zone) map edge, structurally
        # distinct from the cavernous SPACIOUS rooms around it. When one DOES
        # generate, walking its full length and stepping off the map at its
        # far end is THE way to level_3_pipeworks -- deterministic once
        # you've found and walked it, not a per-edge-crossing chance (see the
        # exit_hallway_crossed transition rule above and
        # generator_office._place_exit_hallway).
        exit_hallway_chance=0.25,
        transition_rules=(
            # Deliberately NOT the same mechanism as level_1_office's door
            # into here (a random per-edge-crossing chance that grows with
            # repeat streak) -- this is one specific, findable hallway (see
            # exit_hallway_chance/generator_office._place_exit_hallway) that
            # always leads to level_3_pipeworks once you walk its length and
            # step off the map at its far end. Checked before the generic
            # map_edge_exited rule below since MovementAction._handle_edge
            # sets this instead of (never in addition to) that one when the
            # player is standing on the hallway's exact terminal tile.
            TransitionRule(
                trigger=TriggerKind.EVENT_FLAG_SET,
                event_flag="exit_hallway_crossed",
                destinations=(DestinationOption("level_3_pipeworks", 1.0),),
                message="The hallway ends, and the world outside it doesn't look like the garage anymore.",
            ),
            TransitionRule(
                trigger=TriggerKind.EVENT_FLAG_SET,
                event_flag="map_edge_exited",
                destinations=(DestinationOption("level_2_garage", 1.0),),
                message="The garage keeps going, well past where the light gives out.",
            ),
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="settlement_door",
                destinations=(DestinationOption("level_2_settlement", 1.0),),
                message="You step through the door into a small, quiet room.",
            ),
        ),
    )
)

# A small, enclosed, safe sublevel behind one of level_2_garage's settlement
# doors -- SETTLEMENT kind (see LEVEL_STYLES) bakes in even smaller rooms and
# a lower room cap than INDOOR, so it reads as "one small area" rather than
# another sprawling maze. wall_tile=GARAGE_WALL reuses level_2_garage's own
# reskin (this is a room off the garage, not the plain office wallpaper the
# generator otherwise defaults to). floor_tile=SETTLEMENT_FLOOR still marks
# the whole thing a safe zone (sanity actively recovers, see
# sanity_system.SAFE_ZONE_RESTORE) -- that's a functional flag, not just a
# reskin, so it stays distinct from the garage's own floor.
# STABLE with no edge-exit means every visit -- via any garage zone's door --
# lands on the exact same cached zone (0,0): there's one persistent
# settlement, not a new one per door (see Engine._load_stable_zone's
# fallback for a STABLE level that never sets pending_edge_wall). Leaving
# returns the player to the exact garage zone and tile they left from (see
# Engine._stable_return), not just some canonical spot.
# inn_floor_tile carves one room out as a small inn -- HP and hunger
# passively recover there too, on top of the sanity recovery the rest of the
# settlement already gives (see systems/rest_system.py). inn_furniture_factories
# gives that room an actual bedroll/cooking pot, so it reads as an inn rather
# than just a differently-colored floor tile.
LEVEL_2_SETTLEMENT = register(
    LevelDefinition(
        id="level_2_settlement",
        display_name="Settlement",
        generator=generate_office_level,
        ambient_sanity_drain=0.0,
        is_well_lit=True,
        wall_tile=tile_types.GARAGE_WALL,
        floor_tile=tile_types.SETTLEMENT_FLOOR,
        inn_floor_tile=tile_types.INN_FLOOR,
        inn_furniture_factories=(_spawn_bedroll, _spawn_cooking_pot),
        kind=LevelKind.SETTLEMENT,
        stability=LevelStability.STABLE,
        door_exit_chance=1.0,
        # The one place isolation is off and colonists actually gather --
        # see _spawn_colonist/systems/npc_social.py.
        isolation=False,
        spawn_table=(
            SpawnEntry(factory=_spawn_colonist, weight=1.0, min_count=2, max_count=4, cluster_radius=6),
            SpawnEntry(factory=_spawn_almond_water, weight=1.0, min_count=0, max_count=1),
        ),
        transition_rules=(
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="stairs_down",
                destinations=(DestinationOption("level_2_garage", 1.0),),
                message="You step back out into the garage.",
            ),
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="door_exit",
                destinations=(DestinationOption("level_2_garage", 1.0),),
                message="You step back out into the garage.",
            ),
        ),
    )
)

# A fourth look -- "pipeworks": brown floor tile and a wall that's a grey/
# brown amalgamation (see tile_types.PIPEWORKS_WALL/PIPEWORKS_FLOOR), built
# the same cramped-cubicle-maze way as level_0/level_1 (kind=INDOOR) rather
# than the garage's cavernous SPACIOUS style. Reachable from level_2_garage
# (see the map_edge_exited rule above) -- same growing-chance-with-streak
# mechanism as level_1_office's own door into level_2_garage. No further
# level past this one yet, so its own exit just loops back into a freshly
# generated instance of itself, same as level_1_office did before
# level_2_garage existed.
LEVEL_3_PIPEWORKS = register(
    LevelDefinition(
        id="level_3_pipeworks",
        display_name="Level 3",
        generator=generate_office_level,
        ambient_sanity_drain=0.2,
        is_well_lit=True,
        wall_tile=tile_types.PIPEWORKS_WALL,
        floor_tile=tile_types.PIPEWORKS_FLOOR,
        door_exit_chance=0.5,
        kind=LevelKind.INDOOR,
        stability=LevelStability.UNSTABLE,
        isolation=True,
        spawn_table=(
            SpawnEntry(factory=_spawn_wanderer, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_hollow, weight=1.0, min_count=1, max_count=1),
            SpawnEntry(factory=_spawn_almond_water, weight=1.0, min_count=1, max_count=2),
        ),
        hazard_table=(
            SpawnEntry(factory=_spawn_spore_zone, weight=1.0, min_count=1, max_count=2),
            SpawnEntry(factory=_spawn_debris_pile_office, weight=1.0, min_count=1, max_count=1),
        ),
        transition_rules=(
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="stairs_down",
                destinations=(DestinationOption("level_3_pipeworks", 1.0),),
                message="You take the stairs down.",
            ),
            TransitionRule(
                trigger=TriggerKind.FEATURE_STEPPED_ON,
                feature_tile_id="door_exit",
                destinations=(DestinationOption("level_3_pipeworks", 1.0),),
                message="You open the door and step through.",
            ),
        ),
    )
)
