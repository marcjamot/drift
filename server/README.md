# Drift Server

WebSocket game server for a Battlegrounds-style autobattler.

The server owns the match state. Clients send player input and receive state,
combat logs, and replay/action data for rendering.

## Files

```text
src/main.py        WebSocket entrypoint
src/engine/        match setup, state machine, events, actions, replay
src/engine/models/ plain game data: cards, minions, players, pool
src/states/        core game states: begin, hero_select, shop, combat, end
src/addons/        cards, heroes, keywords, and custom game content
```

## Match Flow

`main.py` receives WebSocket messages.

`Matchmaker` waits for players, fills bots, then creates a `Match`.

`Match` builds the catalog, pool, event bus, replay recorder, and states.

`StateMachine` runs:

```text
begin -> hero_select -> (shop -> combat)* -> end
```

`shop -> combat` repeats until one player remains or the match ends.

Each state may have a deadline. Most states use `None`. Shop uses
`BUY_DEADLINE`.

## Events And Actions

Events are internal hooks for cards and addons.

Actions are visible game facts. They are stored in replays and used for
client rendering.

```py
ctx.match.event_bus.on("damage", callback, phase="pre")
ctx.actions.entity_damage(source, target, amount)
ctx.actions.record("addon.my_addon.my_action", {"value": 1})
```

Use events to decide what happens. Use actions when visible state changes.

## Replay

Replay files are state based:

```text
metadata
states[]:
  entered_at
  deadline
  snapshot
  actions[]
  exited_at
```

To replay a time, load the state's snapshot and apply actions up to that time.

## Add A Server Addon

Use `src/addons/neutrals/` as the simplest reference.

Short version:

1. Add a card file in an addon folder.
2. Inherit from `MinionCard` or `HeroCard`.
3. Register the card in that folder's `__init__.py`.
4. Register a new addon package in `src/addons/__init__.py` if needed.

Card data usually looks like this:

```py
class SkyDuelist(MinionCard):
    card_id = "sky_duelist"
    card_name = "Sky Duelist"
    attack = 4
    health = 4
    tavern_tier = 3
```
