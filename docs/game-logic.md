# The Hobbit (Oric, 1982) — Game Logic (pseudocode only)

```text
// see: docs/map.md, docs/memory-map.md, docs/game_solution.md

type Place { id, exits[] }
type Exit { dir, dest, door }
type Thing { name, adjectives, locs[], carrier, locked, open, broken, glow, creature, present }
type Player { loc, inv[] }
type Character { name, loc, alive, hidden }
type Door { name, locked, open }
type Event { name, ticks, cond, on_tick, on_expire }
```

```text
function main():
  show_intro()
  tutorial_look()                      // game plays LOOK by itself
  loop:
    line = read_line("> ")
    cmd = understand(line)
    if cmd == UNKNOWN: say("I DO NOT KNOW ..."); continue
    if cmd == EMPTY: continue
    if cmd.kind == SPECIAL: run_special(cmd); continue
    if do_player_action(cmd) == false: continue
    advance_world()                    // 1 success = 1 tick
```

```text
function understand(line):
  w = lowercase(split(line))           // "." ends input
  w = remove(w, [THE, A, AN])
  if w == [d] and d in DIRS: return Move(d)
  if w == [GO|RUN, d] and d in DIRS: return Move(d)
  v = first_verb(w)                    // LOOK GET OPEN KILL SAY WEAR ...
  if v == null: return UNKNOWN
  if v in [LOOK, INVENTORY, WAIT, SCORE, HELP, QUIT, SAVE, LOAD]:
    return Simple(v)
  if v == SAY and w == [SAY, TO, friend, order]:
    return Order(friend, order)        // quotes required
  if v == FOLLOW: return Follow(w[1])
  if needs_two_objects(v):             // PUT X IN Y, BREAK X WITH Y
    return Act2(v, find_visible(w), find_visible(w))
  return Act1(v, find_visible(w))
```

```text
function do_player_action(cmd):
  if cmd is Move(d): return try_move(player, d)
  if cmd == LOOK: describe(player.loc); return true
  if cmd == INVENTORY: list(player.inv); return true
  if cmd == WAIT: say("You wait. Time passes..."); return true
  if cmd is Act1(GET, t):
    if t == null or t.loc != player.loc: say("I SEE NOTHING ..."); return false
    t.carrier = player; t.loc = null; say("You take ..."); return true
  if cmd is Act1(DROP, t):
    t.carrier = NOBODY; t.loc = player.loc; say("You drop ..."); return true
  if cmd is Act1|Act2: return manipulate(cmd)
  if cmd is Order(f, o): say("You talk to ..."); f.pending = o; return true
  if cmd is Follow(f): return try_move(player, f.last_dir)
  return false
```

```text
function try_move(who, d):
  e = exit_at(who.loc, d)
  if e == null: say("YOU CANNOT GO ..."); return false
  if e.door and (e.door.locked or not e.door.open):
    say(locked_msg(e.door)); return false
  if who == player and dark(e.dest) and not light_nearby():
    say("IT IS DARK."); return false
  who.loc = e.dest
  if who == player: describe(e.dest)
  else if who.loc == player.loc: say("<who> goes ...")
  return true

function describe(p):
  say(desc(p) + " visible exits are: " + exits(p))
  say("you see: " + things_at(p) + characters_at(p))

function dark(p):
  return no t where (t.loc == p or t.carrier.loc == p) and t.glow

function light_nearby():
  return sword.loc == player.loc or sword.carrier == player
```

```text
function manipulate(cmd):
  if cmd == UNLOCK(d) and has(right_key(d)): d.locked = false; return true
  if cmd == OPEN(d) and not d.locked: d.open = true; return true
  if cmd == BREAK_TRAP_WITH_SWORD: trap.broken = true; return true
  if cmd == DIG_SAND: trap.present = true; return true
  if cmd == OPEN_BARREL: barrel.open = true; wine.present = true; return true
  if cmd == WEAR_RING: player.hidden = true; ring.timer = 4; return true
  if cmd == CLIMB_BARREL and player.hidden: player.in_barrel = true; return true
  if cmd == OPEN_CHEST: chest.open = true; return true
  if cmd == PUT_TREASURE_IN_CHEST: return win_check()
  say("I CANNOT ..."); return false
```

```text
function advance_world():
  if win_check(): return
  for c in [GANDALF, THORIN, ELF, WARG, GOLLUM, BUTLER, BARD,
            DRAGON, TROLL1, TROLL2, GOBLINS, ELROND]:
    if not c.alive: continue
    act(c)
  tick_events()

function act(c):
  switch c:
    case GANDALF: follow(player); open(GREEN_DOOR); wander()
    case THORIN: follow(player); obey_pending_order(); pickup_small_key()
    case TROLL1|TROLL2:
      if player.loc == TROLL_CLEAR and player.stayed >= 3: eat(player)
      if dawn(): stone(); drop(LARGE_KEY)
    case GOLLUM: wander_tunnels(); ask_riddle(); steal_ring()
    case ELF: if player at RIVER: capture_to(ELVEN_DUNGEON)
    case BUTLER: lock_red_door(); open_barrel(); drink(); capture_warg()
    case BARD: obey_pending_order(); if ordered_shoot: kill(DRAGON)
    case DRAGON: stalk(); burn_or_fly()
    case WARG|GOBLINS|SPIDERS: chase() or capture() or attack(player)
    case ELROND: greet_once(); give(LUNCH)
    default: idle_line()              // HELLO, HURRY UP, ...
  if c.loc == player.loc and c.spoke: say("<c> ...")
  if c.moved and c.loc == player.loc: say("<c> enters.")

function tick_events():
  for e in events:                     // magic door, mountain hole,
    e.ticks -= 1                       // barrel float, red door, eyes
    if e.cond(): e.on_tick()
    if e.ticks == 0: e.on_expire(); disarm(e)
```

```text
function attack(a, d):
  if dodged(d) or too_strong(d): say("... wasted."); return
  d.hp -= strength(a)
  if d.hp <= 0:
    d.alive = false; drop_all(d)
    if d == player: die("... KILLED ..."); reboot(TUNNEL_HALL)
    else: say("<d> is dead.")

function capture(victim, dest):
  victim.loc = dest; describe(dest)    // goblin->dungeon, elf->dungeon

function win_check():
  if player.loc == TUNNEL_HALL and treasure in chest and chest.open:
    say("A cheering crowd ... master adventurer!!!")
    say("You have mastered 80.0% of this adventure.")
    won = true; return true
  return false
```

```text
function win_game():                   // canon path
  OPEN_CHEST(); EAST()
  NORTH(); WAIT(); WAIT(); WAIT(); WAIT()   // Day dawns, trolls stone
  NORTH(); GET(LARGE_KEY); SOUTHWEST(); NORTHEAST()
  UNLOCK(ROCK_DOOR); OPEN(ROCK_DOOR); NORTH()
  GET(SWORD); GET(ROPE); SOUTH(); SOUTH(); SOUTHEAST()
  EAST(); EAST(); NORTH()                   // fall to goblin dungeon
  DIG_SAND(); BREAK_TRAP_WITH_SWORD()
  ORDER(THORIN, CARRY_ME); ORDER(THORIN, OPEN_WINDOW); ORDER(THORIN, WEST)
  walk_to(UNDERGROUND_LAKE); GET(RING); walk_out()
  walk_to(RIVER); await_capture(ELVEN_DUNGEON)
  SOUTHWEST()                               // to wine cellar
  WEAR(RING); WAIT(); CLIMB_BARREL(); WEAR(RING); WAIT() x4
  EAST()                                    // wooden town
  ORDER(BARD, NORTH); FOLLOW(BARD)
  ORDER(BARD, UP); FOLLOW(BARD)
  ORDER(BARD, UP); FOLLOW(BARD)
  ORDER(BARD, NORTH); FOLLOW(BARD)
  ORDER(BARD, NORTH); FOLLOW(BARD)
  ORDER(BARD, NORTH); FOLLOW(BARD)           // dragon halls
  ORDER(BARD, SHOOT_DRAGON); GET(TREASURE)
  walk_back(TUNNEL_HALL)
  OPEN_CHEST(); PUT(TREASURE, CHEST)         // 80%
```
