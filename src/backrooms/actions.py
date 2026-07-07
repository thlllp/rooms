from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.entity.components.attributes import attribute_value
from backrooms.entity.entity import RenderOrder
from backrooms.world.crafting import CRAFTING_RECIPES
from backrooms.world.level_registry import LEVEL_REGISTRY, LEVEL_STYLES

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity

# Sentinel distinguishing "caller didn't resolve this, look it up yourself"
# from a legitimate `None` (no blocker at all) -- lets BumpAction hand its
# already-resolved get_blocking_entity_at() result to the action it
# delegates to, instead of that action re-scanning the same tile.
_UNRESOLVED = object()


class Action:
    # Whether performing this action should advance the game clock (tick
    # sanity/hazards/AI). UI-only actions (menus, escaping a menu) set this
    # False so opening a screen doesn't cost the player a turn.
    costs_turn = True

    def __init__(self, entity: "Entity") -> None:
        self.entity = entity

    def perform(self, engine: "Engine") -> None:
        raise NotImplementedError


class EscapeAction(Action):
    costs_turn = False

    def perform(self, engine: "Engine") -> None:
        if engine.look_mode:
            engine.look_mode = False
        elif engine.show_character_screen:
            engine.show_character_screen = False
        elif engine.show_inventory:
            engine.show_inventory = False
        else:
            raise SystemExit()


class ToggleCharacterScreenAction(Action):
    costs_turn = False

    def perform(self, engine: "Engine") -> None:
        engine.show_character_screen = not engine.show_character_screen


class ToggleLookModeAction(Action):
    costs_turn = False

    def perform(self, engine: "Engine") -> None:
        engine.look_mode = not engine.look_mode
        if engine.look_mode:
            engine.look_cursor = (engine.player.x, engine.player.y)


class ToggleInventoryAction(Action):
    costs_turn = False

    def perform(self, engine: "Engine") -> None:
        engine.show_inventory = not engine.show_inventory


class ToggleLightAction(Action):
    """Switching a light source on/off is a real gameplay choice (fuel is
    finite -- see LightSourceComponent/tick_light_fuel), not a UI toggle, so
    unlike ToggleCharacterScreenAction/ToggleLookModeAction/ToggleInventoryAction
    this costs a turn on success. A no-op flip (no light source, or trying to
    relight an empty one) is free."""

    def perform(self, engine: "Engine") -> None:
        light = self.entity.light_source
        if light is None:
            self.costs_turn = False
            return
        if not light.is_lit and light.fuel <= 0:
            self.costs_turn = False
            engine.message_log.add_message("There's no fuel left to light it.", color=Color.GREY)
            return

        light.is_lit = not light.is_lit
        if light.is_lit:
            engine.message_log.add_message("You switch on your light.", color=Color.WHITE)
        else:
            engine.message_log.add_message("You switch off your light.", color=Color.GREY)


def _effective_capacity(player: "Entity") -> int:
    """Inventory.capacity plus whatever equipped gear adds (e.g. a back-slot
    backpack) -- computed fresh rather than mutating Inventory.capacity on
    equip/unequip, so it can never drift out of sync with what's actually
    worn. Shared by PickupAction and UseItemAction's un-equip path, the two
    places something can be added to held inventory."""
    bonus = player.equipment.capacity_bonus() if player.equipment is not None else 0
    return player.inventory.capacity + bonus


class PickupAction(Action):
    def perform(self, engine: "Engine") -> None:
        player = self.entity
        if player.inventory is None:
            self.costs_turn = False
            return

        game_map = engine.game_map
        item = next((e for e in game_map.entities_at(player.x, player.y) if e.render_order == RenderOrder.ITEM), None)
        if item is None:
            self.costs_turn = False
            engine.message_log.add_message("There's nothing here to pick up.", color=Color.GREY)
            return
        if len(player.inventory.items) >= _effective_capacity(player):
            self.costs_turn = False
            engine.message_log.add_message("You can't carry anything else.", color=Color.WARNING)
            return

        game_map.entities.discard(item)
        player.inventory.items.append(item)
        engine.message_log.add_message(f"You pick up the {item.name}.", color=Color.WHITE)


class CraftAction(Action):
    """Tries every registered recipe in order and crafts the first one whose
    ingredients are all currently held -- removes one of each ingredient,
    adds the result. No crafting-station/location requirement; a no-op
    (free) if nothing currently matches."""

    def perform(self, engine: "Engine") -> None:
        player = self.entity
        if player.inventory is None:
            self.costs_turn = False
            return

        held = player.inventory.items
        held_names = [item.name for item in held]

        for recipe in CRAFTING_RECIPES:
            needed = {name: recipe.ingredients.count(name) for name in set(recipe.ingredients)}
            if any(held_names.count(name) < count for name, count in needed.items()):
                continue

            for ingredient_name in recipe.ingredients:
                held.remove(next(item for item in held if item.name == ingredient_name))

            result = recipe.result_factory()
            held.append(result)
            engine.message_log.add_message(f"You craft a {result.name}.", color=Color.WHITE)
            return

        self.costs_turn = False
        engine.message_log.add_message("You don't have the materials to craft anything.", color=Color.GREY)


class AutoExploreAction(Action):
    """Starts auto-explore mode -- main.py's loop then calls
    engine.step_auto_explore() once per real-time tick (rate-limited there)
    while engine.auto_exploring is set, so a single keypress animates
    step-by-step instead of resolving instantly. costs_turn=False since
    starting the mode doesn't itself consume a turn -- each step taken while
    it runs does, via its own engine.advance_turn() call."""

    costs_turn = False

    def perform(self, engine: "Engine") -> None:
        engine.start_auto_explore()


class TravelToAction(Action):
    """Click-to-travel: main.py's loop then calls engine.step_travel() once
    per real-time tick (rate-limited there) while engine.traveling is set --
    same shape as AutoExploreAction, just pathed at (x, y) specifically
    instead of the nearest unexplored frontier (see
    systems.auto_explore.find_step_toward). costs_turn=False for the same
    reason as AutoExploreAction: each step taken advances a turn on its own."""

    costs_turn = False

    def __init__(self, entity: "Entity", x: int, y: int) -> None:
        super().__init__(entity)
        self.x = x
        self.y = y

    def perform(self, engine: "Engine") -> None:
        engine.start_travel((self.x, self.y))


class UseItemAction(Action):
    """`slot_index` indexes a combined list: held inventory items first, then
    currently equipped items -- exactly the order render_inventory_screen
    prints them (see EquipmentComponent.equipped_items), so a given index
    always means the same row on both sides. Selecting a held consumable
    uses it; a held equippable equips it (swapping out whatever already
    occupied that slot back into inventory, if anything); an already-equipped
    item un-equips it back into inventory. Invalid/empty slots are a free
    no-op rather than wasting the player's turn."""

    def __init__(self, entity: "Entity", slot_index: int) -> None:
        super().__init__(entity)
        self.slot_index = slot_index

    def perform(self, engine: "Engine") -> None:
        player = self.entity
        held = player.inventory.items if player.inventory is not None else []
        equipped = player.equipment.equipped_items() if player.equipment is not None else []

        if not (0 <= self.slot_index < len(held) + len(equipped)):
            self.costs_turn = False
            return

        if self.slot_index < len(held):
            item = held[self.slot_index]
            if item.equippable is not None:
                slot = item.equippable.slot
                previous = player.equipment.slots[slot]
                # A straight swap (item out of held, previous back into held)
                # never changes held's SIZE by more than the +1/-1 of
                # `previous` existing or not -- but if `item`'s own
                # capacity_bonus is smaller than whatever it displaces (e.g.
                # swapping a Hiking Bag +10 for a Simple Backpack +5),
                # capacity itself shrinks the instant this equip completes.
                # Check the post-swap fit against the post-swap capacity
                # before committing, not the current (possibly
                # backpack-inflated) capacity.
                previous_bonus = previous.equippable.capacity_bonus if previous is not None else 0
                capacity_after_swap = _effective_capacity(player) - previous_bonus + item.equippable.capacity_bonus
                held_after_swap = len(held) - 1 + (1 if previous is not None else 0)
                if held_after_swap > capacity_after_swap:
                    engine.message_log.add_message(
                        "You don't have room to stow what that would displace.", color=Color.GREY
                    )
                    self.costs_turn = False
                    return
                held.remove(item)
                player.equipment.slots[slot] = item
                if previous is not None:
                    held.append(previous)
                engine.message_log.add_message(f"You equip the {item.name}.", color=Color.WHITE)
            elif item.consumable is not None:
                held.remove(item)
                item.consumable.use(player, engine)
            engine.show_inventory = False
            return

        item = equipped[self.slot_index - len(held)]
        # If `item` itself grants a capacity bonus (a back-slot backpack),
        # removing it takes that bonus with it -- capacity_after_removal
        # reflects the capacity the player will actually have the instant
        # after this un-equip, not the (possibly higher, backpack-inflated)
        # capacity they have right now.
        capacity_after_removal = _effective_capacity(player) - item.equippable.capacity_bonus
        if len(held) >= capacity_after_removal:
            engine.message_log.add_message("Your inventory is full.", color=Color.GREY)
            self.costs_turn = False
            return
        player.equipment.slots[item.equippable.slot] = None
        held.append(item)
        engine.message_log.add_message(f"You remove the {item.name}.", color=Color.WHITE)
        engine.show_inventory = False


class WaitAction(Action):
    def perform(self, engine: "Engine") -> None:
        pass


class MovementAction(Action):
    def __init__(self, entity: "Entity", dx: int, dy: int, *, blocker: "Entity | None" = _UNRESOLVED) -> None:
        super().__init__(entity)
        self.dx = dx
        self.dy = dy
        # Optional pre-resolved get_blocking_entity_at() result -- see
        # BumpAction, which already looked this up to decide attack-vs-move
        # and shouldn't need to scan the entity list a second time.
        self._blocker = blocker

    def perform(self, engine: "Engine") -> None:
        dest_x = self.entity.x + self.dx
        dest_y = self.entity.y + self.dy
        game_map = engine.game_map

        if not game_map.in_bounds(dest_x, dest_y):
            self._handle_edge(engine)
            return
        if not game_map.tiles["walkable"][dest_x, dest_y]:
            return
        if not game_map.allows_diagonal_step(self.entity.x, self.entity.y, self.dx, self.dy):
            return

        blocker = game_map.get_blocking_entity_at(dest_x, dest_y) if self._blocker is _UNRESOLVED else self._blocker
        if blocker is not None:
            return

        self.entity.move(self.dx, self.dy)

    def _handle_edge(self, engine: "Engine") -> None:
        """Walking off the map's edge is normally just a no-op bump, same as
        any other unwalkable destination -- except on a level whose kind
        opts in (LEVEL_STYLES[level_def.kind].uses_edge_exit), where it
        instead sets an event flag for evaluate_transitions to pick up this
        same turn, the same mechanism tick_unstable_floor already uses for
        floor_collapsed. Only the player can trigger a level exit this way;
        a wandering entity bumping the world boundary is just a wall to it.
        Also records *which* wall was crossed (engine.pending_edge_wall) --
        a STABLE level uses this to know which neighboring zone to enter
        (see Engine.load_level).

        If the player is standing exactly on this zone's
        GameMap.exit_hallway_position (see LevelDefinition.has_exit_hallway/
        generator_office._place_exit_hallway), sets "exit_hallway_crossed"
        INSTEAD of the usual "map_edge_exited" -- deliberately mutually
        exclusive, so this level's own TransitionRule for that flag decides
        where the hallway leads, deterministically, without the generic
        per-edge-crossing rule ever competing for the same turn."""
        if self.entity is not engine.player:
            return
        level_def = LEVEL_REGISTRY[engine.current_level_id]
        if not LEVEL_STYLES[level_def.kind].uses_edge_exit:
            return

        game_map = engine.game_map
        dest_x = self.entity.x + self.dx
        dest_y = self.entity.y + self.dy
        if dest_x < 0:
            wall = "left"
        elif dest_x >= game_map.width:
            wall = "right"
        elif dest_y < 0:
            wall = "top"
        else:
            wall = "bottom"

        engine.pending_edge_wall = wall
        if (self.entity.x, self.entity.y) == game_map.exit_hallway_position:
            engine.event_flags.add("exit_hallway_crossed")
        else:
            engine.event_flags.add("map_edge_exited")


BASE_HIT_CHANCE = 0.85
HIT_CHANCE_PER_DEX_DELTA = 0.03
MIN_HIT_CHANCE = 0.5
MAX_HIT_CHANCE = 0.95


def _hit_chance(attacker: "Entity", defender: "Entity") -> float:
    """One roll captures both halves of dexterity's job: a higher-dex
    attacker hits more often, a higher-dex defender lowers the attacker's
    effective hit chance -- i.e. dodges more. A miss here IS a dodge from
    the defender's side; there's no separate dodge roll on top of this.
    Entities without an AttributesComponent (every NPC today -- Hollow,
    Wanderer, ... -- see data/registrations.py) are treated as baseline
    dexterity via attribute_value, rather than giving them a whole
    component just for this one number."""
    delta = attribute_value(attacker, "dexterity") - attribute_value(defender, "dexterity")
    return max(MIN_HIT_CHANCE, min(MAX_HIT_CHANCE, BASE_HIT_CHANCE + delta * HIT_CHANCE_PER_DEX_DELTA))


class AttackAction(Action):
    """Melee only for now -- a directional target resolution (dx, dy) rather
    than a stored target reference, so future ranged/thrown actions can reuse
    the same "target = get_blocking_entity_at(...)" resolution at any distance
    instead of only an adjacent tile."""

    def __init__(self, entity: "Entity", dx: int, dy: int, *, target: "Entity | None" = _UNRESOLVED) -> None:
        super().__init__(entity)
        self.dx = dx
        self.dy = dy
        # Optional pre-resolved target -- see MovementAction's `blocker` for why.
        self._target = target

    def perform(self, engine: "Engine") -> None:
        attacker = self.entity
        game_map = engine.game_map

        # Same corner-cutting rule MovementAction enforces: a diagonal attack
        # through a corner both flanking tiles wall off is just as illegal as
        # a diagonal move through it would be.
        if not game_map.allows_diagonal_step(attacker.x, attacker.y, self.dx, self.dy):
            return

        dest_x = attacker.x + self.dx
        dest_y = attacker.y + self.dy
        target = game_map.get_blocking_entity_at(dest_x, dest_y) if self._target is _UNRESOLVED else self._target
        if target is None or target.fighter is None:
            return

        power = attacker.fighter.power if attacker.fighter is not None else 0
        if power <= 0:
            engine.message_log.add_message(f"{attacker.name} bumps into {target.name}, harmlessly.", color=Color.GREY)
            return

        if engine.rng.random() >= _hit_chance(attacker, target):
            engine.message_log.add_message(f"{attacker.name} attacks {target.name}, but misses.", color=Color.GREY)
            return

        applied = target.fighter.take_damage(power)
        color = Color.HAZARD if target is engine.player else Color.WARNING
        engine.message_log.add_message(f"{attacker.name} hits {target.name} for {applied:.0f}.", color=color)

        if target.fighter.hp <= 0:
            engine.kill_entity(target)


class TalkAction(Action):
    """Bumping into a dialogue-bearing NPC talks instead of attacking or
    moving -- logs one of its flavor lines. Simple one-shot dialogue for
    now (no branching menu), the starting slice of the NPC interaction
    framework to build on."""

    def __init__(self, entity: "Entity", *, target: "Entity") -> None:
        super().__init__(entity)
        self.target = target

    def perform(self, engine: "Engine") -> None:
        line = self.target.dialogue.pick_line(engine.rng)
        engine.message_log.add_message(f'{self.target.name}: "{line}"', color=Color.WHITE)


class BumpAction(Action):
    """What a directional key actually dispatches. In look mode it steers the
    look cursor (free of walkability/turn cost); otherwise it attacks if the
    destination tile holds a Fighter-bearing entity, else moves. Resolves the
    blocking-entity lookup once and hands it to whichever action it delegates
    to, so the tile isn't scanned twice."""

    def __init__(self, entity: "Entity", dx: int, dy: int) -> None:
        super().__init__(entity)
        self.dx = dx
        self.dy = dy

    def perform(self, engine: "Engine") -> None:
        if engine.look_mode:
            self.costs_turn = False
            game_map = engine.game_map
            cursor_x, cursor_y = engine.look_cursor
            engine.look_cursor = (
                max(0, min(game_map.width - 1, cursor_x + self.dx)),
                max(0, min(game_map.height - 1, cursor_y + self.dy)),
            )
            return

        dest_x = self.entity.x + self.dx
        dest_y = self.entity.y + self.dy
        target = engine.game_map.get_blocking_entity_at(dest_x, dest_y)

        if target is not None and target.dialogue is not None:
            TalkAction(self.entity, target=target).perform(engine)
        elif target is not None and target.fighter is not None:
            AttackAction(self.entity, self.dx, self.dy, target=target).perform(engine)
        else:
            MovementAction(self.entity, self.dx, self.dy, blocker=target).perform(engine)
