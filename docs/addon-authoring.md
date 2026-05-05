# Addon Authoring Guide

An addon is up to two files: a Python class on the server and a TypeScript object on the client.
The engine handles all communication between them — you never touch WebSockets directly.

A server addon and a client addon are **independent units with their own IDs**. They are linked
by the client addon declaring which server addon IDs it `listens_to`. Multiple client addons can
listen to the same server addon (e.g. a base skin and a premium VFX pack). A server addon with
no client counterpart is headless. A client addon with no server counterpart is view-only.

---

## Server addon

```python
# server/src/addons/keywords/divine_shield.py

from dataclasses import dataclass
from typing import ClassVar

from ...engine.actions import Action
from ...engine.addon import AddonBase, on_event, on_state, on_intent
from ...engine.context import CombatStateContext, ShopStateContext
from ...engine.events import DamagePayload
from ...engine.memory import MatchScope, StateScope, PerMinion


# --- Actions ---
# Define once here. The action_type string is what client effect handlers key on.

@dataclass
class DivineShieldBroken(Action):
    action_type: ClassVar[str] = "keyword.divine_shield_broken"
    target_id: str


# --- Addon ---

class DivineShieldAddon(AddonBase):
    id = "keywords/divine_shield"   # unique server-side ID

    # --- Memory schemas ---
    # Declare fields here. No string keys. The engine handles namespacing.

    class MatchMemory(MatchScope):
        # Persists for the full match. PerMinion[T] = keyed by minion instance_id.
        divine_shield: PerMinion[bool] = False

    class StateMemory(StateScope):
        # Cleared automatically on every state transition.
        shields_broken_this_round: int = 0

    # --- Event handlers ---
    # @on_event(event_name, phase, priority, in_state)
    # Receives (payload, ctx). ctx is typed to the in_state if provided.

    @on_event("damage", phase="pre", priority=100, in_state=CombatStateContext)
    def block_damage(self, payload: DamagePayload, ctx: CombatStateContext) -> None:
        if payload.amount <= 0:
            return

        mem = ctx.memory_match(self, payload.subject)   # match-wide, per-minion
        if not mem.divine_shield:
            return

        mem.divine_shield = False                       # queued — flushed on emit
        ctx.memory_state(self).shields_broken_this_round += 1

        ctx.emit(DivineShieldBroken(target_id=payload.subject.instance_id))
        # ^ pending mem writes are automatically included in this log entry

        payload.amount = 0
        payload.cancelled = True

    # --- State hooks ---
    # @on_state(ContextType) is called once when that state is entered.

    @on_state(ShopStateContext)
    def on_shop(self, ctx: ShopStateContext) -> None:
        pass  # set up shop-phase logic here if needed

    # --- Intent handlers ---
    # @on_intent(type, in_state) handles inbound client messages.
    # The engine validates that the type is declared and drops unknown types.

    @on_intent("divine_shield.activate", in_state=ShopStateContext)
    def handle_activate(self, player_id: str, payload: dict, ctx: ShopStateContext) -> None:
        minion_id = payload.get("minion_id")
        # ... grant divine shield to a minion the player owns
```

### Memory

| Call | Returns | Notes |
|---|---|---|
| `ctx.memory_match(self, minion)` | writable `MatchMemory` proxy | per-minion, full match |
| `ctx.memory_match(self, player)` | writable `MatchMemory` proxy | per-player, full match |
| `ctx.memory_match(self)` | writable `MatchMemory` proxy | match-global |
| `ctx.memory_state(self, minion)` | writable `StateMemory` proxy | per-minion, current state only |
| `ctx.memory_state(self)` | writable `StateMemory` proxy | state-global |
| `ctx.memory_match(OtherAddon, minion)` | **read-only** proxy | cross-addon access |
| `ctx.memory_state(OtherAddon)` | **read-only** proxy | cross-addon access |

Reading another addon's memory is typed to that addon's schema:
```python
from ..divine_shield import DivineShieldAddon

ds = ctx.memory_match(DivineShieldAddon, payload.subject)  # → DivineShieldAddon.MatchMemory
if ds.divine_shield:   # bool, not Any
    ...
```

Memory writes are queued and flushed atomically with the next `ctx.emit(Action)` call.
**Always call `ctx.emit()` after writing memory** to ensure the delta is logged.

#### Memory field markers

| Marker | Key format | Subject required |
|---|---|---|
| `PerMinion[T]` | `minion:{instance_id}:{field}` | Yes — pass a `Minion` |
| `PerPlayer[T]` | `player:{player_id}:{addon_id}:{field}` | Yes — pass a `PlayerState` |
| (plain type) | `{addon_id}:{field}` or `_state:{addon_id}:{field}` | No |

### Actions

```python
@dataclass
class DivineShieldBroken(Action):
    action_type: ClassVar[str] = "keyword.divine_shield_broken"
    target_id: str                       # fields become the client data payload
```

Emit:
```python
ctx.emit(DivineShieldBroken(target_id=minion.instance_id))
```

If you need to include a raw store delta beyond your own memory writes (e.g. setting
another minion's health), pass it explicitly:
```python
ctx.emit(PoisonousKill(source_id=..., target_id=...), store={f"minion:{id}:health": 0})
```

### Concepts cheat-sheet

| Concept | API |
|---|---|
| Read match memory | `ctx.memory_match(self, subject?).field` |
| Write match memory | `ctx.memory_match(self, subject).field = value` |
| Read state memory | `ctx.memory_state(self, subject?).field` |
| Write state memory | `ctx.memory_state(self, subject).field = value` |
| Emit action | `ctx.emit(MyAction(...))` |
| Emit + extra delta | `ctx.emit(MyAction(...), store={key: val})` |
| React to event | `@on_event("name", phase, priority, in_state)` |
| State init | `@on_state(ContextType)` |
| Handle client intent | `@on_intent("type", in_state)` |
| Register cards | `cards = [MyCard()]` class attribute |
| Match init | `on_load(ctx: MatchContext)` override |

---

## Client addon

```typescript
// client/src/lib/addons/keywords/divine_shield.ts

import type { ClientAddon, GameAction, GameScene } from "../types";
import DivineShieldLayer from "./DivineShieldLayer.svelte";

// Manually define action shapes to match the server Action classes.
interface DivineShieldBroken {
  type: "keyword.divine_shield_broken";
  target_id: string;
}

// Declare intents this addon can send.
type DivineShieldIntent =
  | { type: "divine_shield.activate"; minion_id: string };

const addon: ClientAddon<DivineShieldIntent> = {
  id: "ui/divine_shield",                     // unique client-side ID
  listens_to: ["keywords/divine_shield"],     // server addon IDs to receive actions from

  // Card and hero visuals
  cards: {
    cobalt_guard: { card_id: "cobalt_guard", art: "/art/cobalt_guard.png" },
  },

  // Layers: Svelte components mounted during a game phase.
  // The component receives { scene, send } as props.
  // send is typed to DivineShieldIntent — only declared intents are accepted.
  layers: {
    combat: { component: DivineShieldLayer },
    shop: {
      component: DivineShieldLayer,
      when: (phase) => phase === "shop",
    },
  },

  // Effects: visual reactions keyed by action type from the server.
  // Type the action parameter using the matching interface above.
  effects: {
    "keyword.divine_shield_broken": (action: GameAction, scene: GameScene) => {
      const { target_id } = action.data as DivineShieldBroken;
      const el = scene.getMinionEl(target_id);
      if (el) scene.spawnEffect(el, { type: "css", src: "shield-break", duration_ms: 400 });
    },
  },

  // Declared intent type strings. The engine validates inbound messages against
  // this list — unknown types are dropped before reaching any server handler.
  intents: ["divine_shield.activate"],
};

export default addon;
```

```svelte
<!-- DivineShieldLayer.svelte -->
<script lang="ts">
  import type { GameScene } from "../types";
  import type { DivineShieldIntent } from "./divine_shield";

  let { scene, send } = $props<{ scene: GameScene; send: (i: DivineShieldIntent) => void }>();
</script>

<button onclick={() => send({ type: "divine_shield.activate", minion_id: "abc123" })}>
  Activate
</button>
```

### Concepts cheat-sheet

| Concept | API |
|---|---|
| Addon ID | `id: string` — unique client-side identifier |
| Server dependency | `listens_to: string[]` — server addon IDs to receive from |
| Card visuals | `cards: Record<card_id, CardVisual>` |
| Hero visuals | `heroes: Record<card_id, HeroVisual>` |
| Phase layers | `layers: Partial<Record<Phase, LayerDef<TIntent>>>` |
| Action effects | `effects: Record<action_type, EffectHandler>` |
| Send intent | `send({ type: "...", ...fields })` in layer components |
| Declare intents | `intents: string[]` — validated by engine |

Layers receive a `send` prop typed to `TIntent`. Calling `send(...)` routes the
message to the server through the engine — no direct WebSocket access needed.

---

## Replay log entry shape

```json
{
  "seq": 42,
  "at": 3.14,
  "type": "keyword.divine_shield_broken",
  "data": { "target_id": "abc123" },
  "store": { "minion:abc123:divine_shield": false }
}
```

- `type` + `data` → fed to client `effects` handlers for animations
- `store` → applied to reconstruct exact store state at any point in the replay

The `store` delta in each log entry is the union of:
1. Memory writes made via proxy before `ctx.emit()` was called
2. Any explicit `store={}` dict passed to `ctx.emit()`
