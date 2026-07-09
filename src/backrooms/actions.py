from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from backrooms.constants import Color
from backrooms.entity.components.attributes import attribute_value
from backrooms.entity.components.hazard import pick_loot
from backrooms.entity.components.inventory import effective_capacity, store_or_drop
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
        if engine.show_interact:
            # Closes just the menu, not look mode itself -- a second Escape
            # (falling through to the look_mode branch below) is what backs
            # all the way out to normal movement.
            engine.show_interact = False
            engine.interact_options = []
        elif engine.look_mode:
            engine.look_mode = False
        elif engine.show_character_screen:
            engine.show_character_screen = False
        elif engine.show_inventory:
            engine.show_inventory = False
        elif engine.show_barter:
            engine.show_barter = False
            engine.barter_partner = None
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
        if len(player.inventory.items) >= effective_capacity(player):
            self.costs_turn = False
            engine.message_log.add_message("You can't carry anything else.", color=Color.WARNING)
            return

        game_map.entities.discard(item)
        player.inventory.items.append(item)
        engine.message_log.add_message(f"You pick up the {item.name}.", color=Color.WHITE)


class CraftAction(Action):
    """Tries every registered recipe in order and crafts the first one whose
    ingredients are all currently held -- removes one of each ingredient,
    adds the result. A recipe with `required_tool` set (see
    entity.components.tool.ToolComponent/the Sewing Kit) additionally needs
    a held tool of that name, which is NOT consumed as an ingredient but
    instead ticks down one charge (see ToolComponent.consume_charge),
    discarded only once that use empties it. No crafting-station/location
    requirement; a no-op (free) if nothing currently matches."""

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
            tool_item = None
            if recipe.required_tool is not None:
                tool_item = next((item for item in held if item.name == recipe.required_tool and item.tool is not None), None)
                if tool_item is None:
                    continue

            for ingredient_name in recipe.ingredients:
                held.remove(next(item for item in held if item.name == ingredient_name))

            result = recipe.result_factory()
            held.append(result)
            engine.message_log.add_message(f"You craft a {result.name}.", color=Color.WHITE)

            if tool_item is not None and tool_item.tool.consume_charge():
                held.remove(tool_item)
                engine.message_log.add_message(f"Your {tool_item.name} is used up.", color=Color.GREY)
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
    systems.auto_explore.find_path_to). costs_turn=False for the same
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
    uses it (removed from inventory); a held tool (e.g. Scissors, see
    entity.components.tool) uses its effect but stays in inventory -- the
    whole point of a tool over a consumable; a held equippable equips it
    (swapping out whatever already occupied that slot back into inventory,
    if anything); an already-equipped item un-equips it back into inventory.
    Invalid/empty slots are a free no-op rather than wasting the player's
    turn."""

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
                capacity_after_swap = effective_capacity(player) - previous_bonus + item.equippable.capacity_bonus
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
            elif item.tool is not None:
                # A tool that did nothing (Scissors with no fabric held, or
                # a tool with no direct-use effect at all) is a free no-op,
                # same as an empty/invalid slot below -- don't burn a turn
                # and hand hazards/enemies a free move for a selection that
                # changed no game state.
                if not item.tool.use(player, engine):
                    self.costs_turn = False
            engine.show_inventory = False
            return

        item = equipped[self.slot_index - len(held)]
        # If `item` itself grants a capacity bonus (a back-slot backpack),
        # removing it takes that bonus with it -- capacity_after_removal
        # reflects the capacity the player will actually have the instant
        # after this un-equip, not the (possibly higher, backpack-inflated)
        # capacity they have right now.
        capacity_after_removal = effective_capacity(player) - item.equippable.capacity_bonus
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
        GameMap.exit_hallway_position (see LevelDefinition.exit_hallway_chance/
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

        base_power = attacker.fighter.power if attacker.fighter is not None else 0
        # A wielded hand-slot weapon (e.g. a salvaged Chair Leg/Table Leg,
        # see EquipmentComponent.power_bonus) adds straight onto the
        # attacker's own power, on top of whatever their Fighter grants.
        weapon_bonus = attacker.equipment.power_bonus() if attacker.equipment is not None else 0
        power = base_power + weapon_bonus
        if power <= 0:
            engine.message_log.add_message(f"{attacker.name} bumps into {target.name}, harmlessly.", color=Color.GREY)
            return

        if engine.rng.random() >= _hit_chance(attacker, target):
            engine.message_log.add_message(f"{attacker.name} attacks {target.name}, but misses.", color=Color.GREY)
            return

        applied = target.fighter.take_damage(power)
        color = Color.HAZARD if target is engine.player else Color.WARNING
        engine.message_log.add_message(f"{attacker.name} hits {target.name} for {applied:.0f}.", color=color)

        # Only ticks down whatever actually contributed to this swing (see
        # EquipmentComponent.register_weapon_hit) -- a connecting hit only,
        # never a miss (the early return above already excludes that).
        if attacker.equipment is not None:
            for broken in attacker.equipment.register_weapon_hit():
                engine.message_log.add_message(f"{attacker.name}'s {broken.name} breaks apart from the blow.", color=Color.WARNING)

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


class SalvageAction(Action):
    """Bumping into salvageable wooden furniture (see
    entity.components.salvageable.SalvageableComponent) attempts to wrench
    a usable weapon free of it -- a flat strength check, not a probability
    (see SalvageableComponent.strength_required), same "attribute compared
    against a threshold" shape as _hit_chance's dexterity delta, just
    pass/fail instead of a roll. A failed attempt still costs a turn (same
    as a swing that misses) and leaves the furniture standing, so it's
    worth retrying once strength grows (see
    systems.experience_system.STRENGTH_PER_LEVEL). On success the result
    goes straight into the pack, same "don't drop it underfoot" reasoning
    as tick_debris_pile, falling back to the ground only if there's no
    room."""

    def __init__(self, entity: "Entity", *, target: "Entity") -> None:
        super().__init__(entity)
        self.target = target

    def perform(self, engine: "Engine") -> None:
        player = self.entity
        target = self.target

        if attribute_value(player, "strength") < target.salvageable.strength_required:
            engine.message_log.add_message(
                f"You strain against the {target.name}, but can't wrench anything loose.", color=Color.GREY
            )
            return

        engine.game_map.entities.discard(target)
        item = target.salvageable.result_factory()
        store_or_drop(
            player, item, target.x, target.y, engine,
            stored_message=f"You wrench a {item.name} free of the {target.name}.",
            dropped_message=f"You wrench a {item.name} free, but your pack is full -- it's on the ground.",
        )


class SearchDebrisAction(Action):
    """Bumping a debris pile (see entity.components.debris.DebrisComponent)
    gambles on its pool: `good_chance` odds of a weighted-random find (same
    pick_loot/store_or_drop plumbing as SalvageAction/OpenContainerAction),
    else a jolt of bad luck that drains sanity instead of turning up
    anything. No strength gate, unlike SalvageAction -- anyone can dig
    through debris, they just might not like what they find. One-shot
    either way: a search that comes up empty is still a search, so the pile
    is removed regardless of outcome, same as tick_debris_pile used to do
    the instant the player stepped onto it -- now it takes an explicit bump
    instead, since debris piles block movement rather than being walked
    onto."""

    def __init__(self, entity: "Entity", *, target: "Entity") -> None:
        super().__init__(entity)
        self.target = target

    def perform(self, engine: "Engine") -> None:
        player = self.entity
        target = self.target
        debris = target.debris

        engine.game_map.entities.discard(target)
        if engine.rng.random() < debris.good_chance:
            item = pick_loot(engine.rng, debris.item_factories)
            store_or_drop(
                player, item, target.x, target.y, engine,
                stored_message=f"You dig through the {target.name} and find a {item.name}.",
                dropped_message=f"You find a {item.name}, but your pack is full -- it's at your feet.",
            )
        else:
            if player.sanity is not None:
                player.sanity.drain(debris.sanity_penalty)
            engine.message_log.add_message("Something about the debris unsettles you.", color=Color.HAZARD)


class OpenContainerAction(Action):
    """Bumping a container (see entity.components.container.ContainerComponent,
    e.g. a Toolbox) opens it for one weighted-random item from its pool. No
    strength gate, unlike SalvageAction -- a container just opens; it shares
    the same weighted pick (hazard.pick_loot) and store-or-drop placement,
    differing only in flavor and the missing gate. One-shot: the container is
    removed whether or not the find fit the pack (an emptied toolbox is
    emptied)."""

    def __init__(self, entity: "Entity", *, target: "Entity") -> None:
        super().__init__(entity)
        self.target = target

    def perform(self, engine: "Engine") -> None:
        player = self.entity
        target = self.target

        engine.game_map.entities.discard(target)
        item = pick_loot(engine.rng, target.container.loot_pool)
        store_or_drop(
            player, item, target.x, target.y, engine,
            stored_message=f"You open the {target.name} and find a {item.name}.",
            dropped_message=f"You open the {target.name}, but your pack is full -- the {item.name} stays on the ground.",
        )


class OpenBarterAction(Action):
    """Opens engine.show_barter for `target` -- extracted out of BumpAction's
    barter branch so actions.available_interactions (the interact-menu's
    "Trade with X" option) can trigger the exact same screen a bump into the
    Elder does, rather than duplicating the three-line setup. Free like
    browsing itself (see BarterAction's own costs_turn=False); the caller
    (BumpAction) still sets its own costs_turn=False after delegating here,
    same as it already does for TalkAction/AttackAction et al."""

    costs_turn = False

    def __init__(self, entity: "Entity", *, target: "Entity") -> None:
        super().__init__(entity)
        self.target = target

    def perform(self, engine: "Engine") -> None:
        engine.show_barter = True
        engine.barter_partner = self.target
        engine.barter_greeting = self.target.barter.pick_greeting(engine.rng)


class BarterAction(Action):
    """Buys one of the Elder's offers by row number while the barter screen is
    open (see engine.MODAL_FLAGS "show_barter"). Browsing/trading never costs a
    turn -- you're in a safe community. The price is the offer's base price
    scaled by this level's barter_price_multiplier (so the same good costs
    more/less per community), paid in whole currency items from the player's
    held inventory; the bought offer is then removed from the Elder's stock."""

    costs_turn = False

    def __init__(self, entity: "Entity", offer_index: int) -> None:
        super().__init__(entity)
        self.offer_index = offer_index

    def perform(self, engine: "Engine") -> None:
        partner = engine.barter_partner
        if partner is None or partner.barter is None:
            return
        barter = partner.barter
        if not (0 <= self.offer_index < len(barter.offers)):
            return  # a number key with no offer behind it

        offer = barter.offers[self.offer_index]
        multiplier = LEVEL_REGISTRY[engine.current_level_id].barter_price_multiplier
        price = barter.price_for(offer, multiplier=multiplier)

        held = self.entity.inventory.items if self.entity.inventory is not None else []
        currency = [item for item in held if item.name == barter.currency_item_name]
        if len(currency) < price:
            engine.message_log.add_message(
                f"Not enough {barter.currency_item_name} ({len(currency)}/{price}).", color=Color.GREY
            )
            return

        # Pay (currency items are consumed), then hand over the good. Net held
        # count never rises -- price is >=1 and one item comes back -- so no
        # capacity check is needed here.
        for spent in currency[:price]:
            held.remove(spent)
        reward = offer.result_factory()
        held.append(reward)
        barter.offers.pop(self.offer_index)
        engine.message_log.add_message(
            f"Traded {price} {barter.currency_item_name} for {reward.name}.", color=Color.WHITE
        )


class BumpAction(Action):
    """What a directional key actually dispatches. In look mode it steers the
    look cursor (free of walkability/turn cost); otherwise it attacks if the
    destination tile holds a Fighter-bearing entity, salvages if it holds
    salvageable furniture (see SalvageAction), opens it if it's a container
    (see OpenContainerAction), searches it if it's a debris pile (see
    SearchDebrisAction), else moves. Resolves the blocking-entity lookup once
    and hands it to whichever action it delegates to, so the tile isn't
    scanned twice."""

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

        if target is not None and target.barter is not None:
            # Bumping the community Elder opens their barter screen (see
            # engine.MODAL_FLAGS "show_barter" / rendering.render_barter_screen)
            # rather than talking or attacking -- checked before dialogue so an
            # Elder can carry flavor lines too without them shadowing the trade.
            OpenBarterAction(self.entity, target=target).perform(engine)
            self.costs_turn = False
        elif target is not None and target.dialogue is not None:
            TalkAction(self.entity, target=target).perform(engine)
        elif target is not None and target.fighter is not None:
            AttackAction(self.entity, self.dx, self.dy, target=target).perform(engine)
        elif target is not None and target.salvageable is not None:
            SalvageAction(self.entity, target=target).perform(engine)
        elif target is not None and target.container is not None:
            OpenContainerAction(self.entity, target=target).perform(engine)
        elif target is not None and target.debris is not None:
            SearchDebrisAction(self.entity, target=target).perform(engine)
        else:
            MovementAction(self.entity, self.dx, self.dy, blocker=target).perform(engine)


class InteractOption(NamedTuple):
    """One row of engine.interact_options (see OpenInteractMenuAction): a
    label to print and the already-constructed Action that pressing its row
    number performs (see InteractAction) -- built ready-to-go rather than as
    a factory, since by the time the menu is open the target entity is
    already resolved and can't change out from under the player."""

    label: str
    action: Action


def available_interactions(player: "Entity", engine: "Engine", x: int, y: int) -> list[InteractOption]:
    """Every interaction offered here mirrors a branch BumpAction already
    has -- this exists so look mode's Space key can present the SAME set of
    outcomes as walking into (x, y) would, just as an explicit menu instead
    of one branch silently winning. Per-entity precedence (barter > dialogue
    > fighter > salvageable > container > debris) matches BumpAction's own
    elif chain exactly, so the two never disagree about what a given entity
    offers -- but unlike BumpAction, entities are considered independently, so e.g. an
    item lying on the same tile as a container both show up as their own
    row. "Pick up" is the one option BumpAction has no equivalent for (bump
    never fires for the player's own tile) -- restricted to (x, y) being
    exactly where the player stands, same as PickupAction/the G key."""
    options: list[InteractOption] = []
    dx, dy = x - player.x, y - player.y
    for entity in engine.game_map.entities_at(x, y):
        if entity is player:
            continue
        if entity.barter is not None:
            options.append(InteractOption(f"Trade with {entity.name}", OpenBarterAction(player, target=entity)))
        elif entity.dialogue is not None:
            options.append(InteractOption(f"Talk to {entity.name}", TalkAction(player, target=entity)))
        elif entity.fighter is not None:
            options.append(InteractOption(f"Attack {entity.name}", AttackAction(player, dx, dy, target=entity)))
        elif entity.salvageable is not None:
            options.append(InteractOption(f"Salvage {entity.name}", SalvageAction(player, target=entity)))
        elif entity.container is not None:
            options.append(InteractOption(f"Open {entity.name}", OpenContainerAction(player, target=entity)))
        elif entity.debris is not None:
            options.append(InteractOption(f"Search {entity.name}", SearchDebrisAction(player, target=entity)))
        elif entity.render_order == RenderOrder.ITEM and dx == 0 and dy == 0:
            options.append(InteractOption(f"Pick up {entity.name}", PickupAction(player)))
    return options


class OpenInteractMenuAction(Action):
    """Bound to Space while look mode is active (see input_handlers.py) --
    builds engine.interact_options for whatever's at engine.look_cursor (see
    available_interactions) and opens engine.show_interact so
    rendering.ui.render_interact_menu can list them. Only the player's own
    tile or one of the eight adjacent ones qualifies -- every interaction
    available_interactions can offer is itself bump-range only, so a cursor
    parked further out always has nothing legal to show. Opening the menu is
    free, same as any other modal; the chosen option's own cost applies once
    something is actually picked (see InteractAction)."""

    costs_turn = False

    def perform(self, engine: "Engine") -> None:
        if not engine.look_mode:
            return

        player = self.entity
        cursor_x, cursor_y = engine.look_cursor
        if max(abs(cursor_x - player.x), abs(cursor_y - player.y)) > 1:
            engine.message_log.add_message("That's too far away to interact with.", color=Color.GREY)
            return

        options = available_interactions(player, engine, cursor_x, cursor_y)
        if not options:
            engine.message_log.add_message("There's nothing here to interact with.", color=Color.GREY)
            return

        engine.interact_options = options
        engine.show_interact = True


class InteractAction(Action):
    """Picks row `index` from engine.interact_options (see
    OpenInteractMenuAction) -- same number-key row as UseItemAction/
    BarterAction (see input_handlers.py). Closes the menu either way: a
    resolved pick is done, and an out-of-range index (a stray number key past
    however many rows are actually listed) is the same free no-op the other
    modals already give a slot with nothing behind it. Adopts the picked
    action's own costs_turn rather than always costing a turn itself, since
    e.g. "Trade with X" (OpenBarterAction) only opens a screen and shouldn't
    burn a turn just for that."""

    def __init__(self, entity: "Entity", index: int) -> None:
        super().__init__(entity)
        self.index = index

    def perform(self, engine: "Engine") -> None:
        options = engine.interact_options
        engine.show_interact = False
        engine.interact_options = []

        if not (0 <= self.index < len(options)):
            self.costs_turn = False
            return

        action = options[self.index].action
        action.perform(engine)
        self.costs_turn = action.costs_turn
