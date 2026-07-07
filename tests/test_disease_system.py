from backrooms.entity.components.afflictions import AfflictionsComponent
from backrooms.entity.components.attributes import AttributesComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.systems.disease_system import HYDROLITIS_PLAGUE, process_diseases
from backrooms.world import tile_types
from backrooms.world.game_map import GameMap


class FakeLog:
    def __init__(self):
        self.messages = []

    def add_message(self, text, color=None):
        self.messages.append(text)


class FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


class FakeEngine:
    def __init__(self, player, roll):
        self.player = player
        self.rng = FixedRng(roll)
        self.message_log = FakeLog()
        self.game_map = GameMap(10, 10, wall_tile=tile_types.WALL)
        # A single pool of contaminated water under the player at (5, 5).
        self.game_map.tiles[5, 5] = tile_types.FLOODED_FLOOR


def _player(*, endurance=5):
    p = Entity(
        5, 5, char="@", color=(255, 255, 255), name="Player", render_order=RenderOrder.PLAYER,
        attributes=AttributesComponent(endurance=endurance), afflictions=AfflictionsComponent(),
    )
    return p


def test_contracts_plague_on_contaminated_tile_when_roll_succeeds():
    player = _player()
    engine = FakeEngine(player, roll=0.0)  # 0.0 < any positive chance -> contract
    process_diseases(engine)
    assert player.afflictions.has(HYDROLITIS_PLAGUE)
    assert any("Hydrolitis Plague" in m for m in engine.message_log.messages)


def test_no_plague_when_roll_exceeds_chance():
    player = _player()
    engine = FakeEngine(player, roll=0.99)  # far above the ~8% baseline chance
    process_diseases(engine)
    assert not player.afflictions.has(HYDROLITIS_PLAGUE)


def test_no_plague_off_contaminated_water():
    player = _player()
    engine = FakeEngine(player, roll=0.0)
    engine.game_map.tiles[5, 5] = tile_types.FLOOR  # dry ground, no zone effect
    process_diseases(engine)
    assert not player.afflictions.has(HYDROLITIS_PLAGUE)


def test_higher_endurance_resists_a_roll_that_infects_baseline():
    # roll 0.06: below baseline chance (0.08) so a tough-5 character catches it,
    # but above the endurance-10 chance (0.04) so a hardier one shrugs it off.
    weak = _player(endurance=5)
    tough = _player(endurance=10)
    process_diseases(FakeEngine(weak, roll=0.06))
    process_diseases(FakeEngine(tough, roll=0.06))
    assert weak.afflictions.has(HYDROLITIS_PLAGUE)
    assert not tough.afflictions.has(HYDROLITIS_PLAGUE)


def test_already_infected_does_not_relog():
    player = _player()
    player.afflictions.add(HYDROLITIS_PLAGUE)
    engine = FakeEngine(player, roll=0.0)
    process_diseases(engine)
    assert engine.message_log.messages == []  # no duplicate contraction message
