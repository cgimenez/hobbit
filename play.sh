#!/bin/bash
# The Hobbit (Oric 1982, Melbourne House) jouable en interactif sous sim65.
#
# Image dediee build/sim/play.sim (shim ASCII + SAVE/LOAD par snapshots,
# harness/snap.s) et sauvegarde sav/play.bin : RIEN n'est partage avec les
# experimentations solver (SLVW*.sim, solver.db, slv_run*.bin) — jouer ne
# les perturbe pas, ni l'inverse (repack isole, build/sim/ et sav/ ignorés).
#
# SAVE/LOAD in-game : SAVE ecrit sav/play.bin (4 regions memoire) ; au
# lancement suivant, play.sh repacke l'image avec ce blob -> LOAD le
# restaure. (Les invites PREPARE/REWIND/VERIFY + touches sacrifiées sont
# conservees : seul le "chemin cassette" est remplace.)
#
# Usage : ./play.sh [--no-pack]
#   --no-pack : saute le repack (demarrage immediat, image existante).
#   ./play.sh > partie.txt : enregistre la transcription (stderr = infos).
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/bin/python"
SIM65="$ROOT/tools/cc65/bin/sim65"
IMG="$ROOT/build/sim/play.sim"
BLOB="$ROOT/sav/play.bin"

# Etat initial : faute de sauvegarde, on part du checkpoint tunnel (SLVW).
if [ ! -f "$BLOB" ]; then
  if [ -f "$ROOT/sav/SLVW.bin" ]; then
    cp "$ROOT/sav/SLVW.bin" "$BLOB"
    echo "play.sh: seed sav/play.bin <- sav/SLVW.bin" >&2
  else
    echo "play.sh: ni sav/play.bin ni sav/SLVW.bin (etat initial requis)" >&2
    exit 1
  fi
fi

if [ "${1:-}" != "--no-pack" ]; then
  need_pack=0
  [ ! -f "$IMG" ] && need_pack=1
  for f in harness/shim.s harness/shim.cfg harness/snap.s harness/snap.cfg \
           scripts/pack_sim.py data/hobbit.bin data/basic10.rom; do
    [ "$ROOT/$f" -nt "$IMG" ] 2>/dev/null && need_pack=1
  done
  [ "$BLOB" -nt "$IMG" ] && need_pack=1
  if [ "$need_pack" = 1 ]; then
    if ! "$PY" "$ROOT/scripts/pack_sim.py" --snapshot play --solver \
         >/tmp/hobbit_play_pack.log 2>&1; then
      cat /tmp/hobbit_play_pack.log >&2
      echo "play.sh: echec du pack" >&2
      exit 1
    fi
  fi
elif [ ! -f "$IMG" ]; then
  echo "play.sh: pas d'image (retirez --no-pack pour packer)" >&2
  exit 1
fi
[ -x "$SIM65" ] || { echo "play.sh: $SIM65 absent" >&2; exit 1; }

# Clavier brut : touche = octet immediat ($0D pour ENTREE, sans echo
# local) ; Ctrl-C garde son signal pour quitter. Restauration garantie.
if [ -t 0 ]; then
  OLDSTTY="$(stty -g)"
  trap 'stty "$OLDSTTY" 2>/dev/null' EXIT INT TERM
  stty -icanon -echo isig -icrnl -ixon min 1 time 0
  {
    echo "The Hobbit (Oric 1982) — ENTREE valide, Ctrl-C quitte."
    echo "SAVE/LOAD in-game sur ${BLOB#$ROOT/} (recharge au relancement)."
    echo "  (sans touche, le jeu finit par jouer WAIT tout seul :"
    echo "   authentique)."
  } >&2
fi

"$SIM65" "$IMG" 2>/dev/null | "$PY" -u "$ROOT/scripts/play_filter.py" "$BLOB"
