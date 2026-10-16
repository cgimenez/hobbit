#!/usr/bin/env python3
"""Décodeur statique des messages de The Hobbit (bloc 2, moteur $4444).

Réimplémente ``render_text`` ($4444), ``word_render`` ($4241) et
``common_lookup`` ($462D) pour transformer un pointeur de message (inline
``JSR $440D``) en texte anglais lisible, utilisé par ``disasm.py`` pour les
commentaires du listing (à la place des aperçus octets illisibles).

Format (cf. docs/block4-analysis.md) — le message est un flux d'octets :
  - ``$20-$5F`` : littéral ASCII ;
  - ``$60-$7F`` : mot courant, table $1117 (32 pointeurs 2 o) ;
  - bit7 set  : mot 2 octets du dictionnaire packé 5-bit : page ``$05 +
                (hi&$0F)``, offset ``lo`` ; le nibble haut de ``hi`` porte la
                grammaire (suffixes/espaces/ponctuation/CR) ;
  - ``<$20``  : tokens (interpolation d'état : noms d'objets, pronoms,
                messages imbriqués, GOTO/recurse…). Sans état runtime, ces
                tokens sont rendus en marqueurs ``<OBJ>``/``<NAME>``/…

Le décodage est approximatif (suffixes S/ES/ING et espaces dépendent du
contexte runtime) mais lisible. Usage :

    from msg_decode import decode_message, dict_words
    texte = decode_message(raw, 0x18AA)   # -> "A COMFORTABLE TUNNEL LIKE HALL"
    mots  = dict_words(raw)               # 570 mots du dictionnaire ($0540-$1116)

En ligne de commande :

    python scripts/msg_decode.py            # aperçu de 3 messages
    python scripts/msg_decode.py 18AA       # message à $18AA
    python scripts/msg_decode.py words      # dump des mots du dictionnaire (1 par ligne)
"""

from __future__ import annotations

BASE = 0x0400
CAP = 72  # longueur max d'un aperçu (caractères utiles)

# Tokens $00-$13 (table $4641). Rendus en marqueurs faute d'état runtime.
_TOKENS = {
    0x00: "<MSG>",   # message imbriqué (pile $466F)
    0x01: "<W>",     # mot à l'adresse empilée
    0x03: "<W>",     # mot pointé par wptr ($71)
    0x04: "<W>",     # variante empilée (tables $28BC/$28C4)
    0x06: "<OBJ>",   # nom de l'objet $C5
    0x07: "<ARG1>",  # nom/objet $15
    0x08: "<C>",     # vecteur $2C2F
    0x09: "<ARG2>",  # objet $16
    0x0C: "<HIS>",   # his/your (objet $C5)
    0x0E: "<HIS>",   # his/your (objet $15)
    0x10: "<NAME>",  # nom (objet $C5 ; someone si $FF)
    0x11: "<NAME>",  # nom (objet $15)
    0x13: "<NAME>",  # nom (mot empilé)
}


def decode_word_at(raw: bytes, addr: int) -> tuple[str, int]:
    """Mot du dictionnaire packé 5-bit à l'adresse absolue ``addr``.

    Réimplémente ``word_render`` ($4241) : renvoie ``(mot, longueur consommée)``.
    La fin d'un mot est signalée par le bit7 d'un octet (avec les cas
    particuliers 2/3 caractères) ou par un code 0.
    """
    codes: list[int] = []
    x = y = 0
    for _ in range(64):
        off = addr - BASE + y
        a = raw[off] if 0 <= off < len(raw) else 0
        code = a & 0x1F
        if code == 0:
            return "".join(chr(0x40 + c) for c in codes), y + 1
        codes.append(code)
        x += 1
        y += 1
        if (a & 0x80) == 0:
            continue
        if x == 2:
            continue
        if x != 3:
            return "".join(chr(0x40 + c) for c in codes), y
        if raw[addr - BASE + y - 2] & 0x80:
            continue
        return "".join(chr(0x40 + c) for c in codes), y
    return "".join(chr(0x40 + c) for c in codes), y


# Dictionnaire : ``$0540`` jusqu'a la table des mots courants ``$1117`` (32
# pointeurs 2 o, cf. Decoder._build_common). Precede d'un ``WordIndex`` en
# ``$0500`` (offsets 2 o par code de lettre, base ``$0500`` : A=code 1 -> $0540).
# Les mots sont ranges en blocs alphabetiques, un par lettre.
#
# Attention : la longueur d'une entree n'est PAS celle de ``word_render`` ($4241)
# mais celle du PARSEUR (``dict_read``, bloc 4). Apres les lettres (fin sur bit7,
# cas particuliers sur l'INDEX D'OCTET Y==2 / Y==3, code 0 saute), le parseur
# teste le BIT6 du dernier octet : s'il est pose, l'entree est suivie de 2 octets
# annexes (grammaire/flexion) a sauter :
#     longueur = nb_octets_lettres + (2 si (dernier_octet & $40) sinon 0)
# Ignorer ce ``+2`` desynchronise tout parcours sequentiel (recollages du type
# ``CBUTLER`` = ``C`` + ``BUTLER``). Le rendu des MESSAGES (``Decoder.word`` ->
# ``decode_word_at``, qui suit ``word_render``) n'est pas affecte.
DICT_LO, DICT_HI = 0x0540, 0x1116
WORD_INDEX = 0x0500  # table d'offsets 2 o par lettre (base $0500), A=code 1


def _u16(raw: bytes, addr: int) -> int:
    off = addr - BASE
    if 0 <= off < len(raw) - 1:
        return raw[off] | (raw[off + 1] << 8)
    return 0


def dict_entry(raw: bytes, addr: int) -> tuple[str, int]:
    """Entree du dictionnaire a ``addr``, longueur selon le PARSEUR Oric.

    Reproduit ``dict_read`` (bloc 4) : lettres jusqu'au bit7 (cas particuliers
    sur l'index d'octet ``Y==2`` et ``Y==3``), code 0 saute ; puis ``+2`` si le
    dernier octet a le bit6 pose (2 octets de grammaire/flexion sautes). Renvoie
    ``(mot, longueur_totale)``.
    """
    off = addr - BASE
    codes = [raw[off] & 0x1F]  # 1re lettre (dict_cmp1 l'a deja lue)
    y = 1
    while y < 64:
        b = raw[off + y] if off + y < len(raw) else 0
        if b & 0x1F:
            codes.append(b & 0x1F)
        y += 1
        if (b & 0x80) == 0:
            continue
        if y == 2:
            continue
        if y != 3:
            break
        if raw[off + y - 2] & 0x80:
            continue
        break
    length = y
    if raw[off + y - 1] & 0x40:  # suffixe 2 o marque par le bit6 (dict_read)
        length += 2
    return "".join(chr(0x40 + c) for c in codes), length


def dict_words(raw: bytes) -> list[str]:
    """Mots du dictionnaire ``$0540-$1116``, enumeres par blocs ``WordIndex``.

    Parcours exact (semantique du parseur Oric, cf. ``dict_entry``) : les mots
    sont lus bloc par bloc (un par lettre A->Y), sans recollage.
    """
    starts = sorted(
        {
            WORD_INDEX + off
            for letter in range(1, 27)
            if (off := _u16(raw, WORD_INDEX + 2 * letter))
            and DICT_LO <= WORD_INDEX + off < DICT_HI
        }
    )
    words: list[str] = []
    for k, start in enumerate(starts):
        end = min(starts[k + 1] if k + 1 < len(starts) else DICT_HI, DICT_HI)
        i = start
        while i < end:
            w, n = dict_entry(raw, i)
            if n <= 0:
                break
            if w:
                words.append(w)
            i += n
    return words


class Decoder:
    """Décodeur adossé à l'image mémoire ``raw`` (base ``$0400``)."""

    def __init__(self, raw: bytes):
        self.raw = raw
        self._words: dict[tuple[int, int], str] = {}
        self._common = self._build_common()

    def _b(self, addr: int) -> int:
        off = addr - BASE
        return self.raw[off] if 0 <= off < len(self.raw) else 0

    def word(self, hi: int, lo: int) -> str:
        """Mot du dictionnaire packé 5-bit (word_render $4241)."""
        key = (hi, lo)
        if key in self._words:
            return self._words[key]
        base = ((0x05 + (hi & 0x0F)) << 8) | lo
        text, _ = decode_word_at(self.raw, base)
        self._words[key] = text
        return text

    def _build_common(self) -> dict[int, str]:
        """Table $1117 : $60-$7F -> mot courant (common_lookup $462D)."""
        out = {}
        for i in range(32):
            hi = self._b(0x1118 + 2 * i)
            lo = self._b(0x1117 + 2 * i)
            out[0x60 + i] = self.word(hi, lo)
        return out

    def message(self, addr: int, cap: int = CAP) -> str:
        """Décode le message à ``addr`` (render_text $4444)."""
        if addr == 0:
            return ""
        ptr, tidx = addr, 0
        out: list[str] = []

        def add_word(w: str) -> None:
            if not w:
                return
            if out and out[-1][-1:].isalnum():
                out.append(" ")
            out.append(w)

        for _ in range(1000):
            if sum(len(s) for s in out) > cap * 4:
                break
            b = self._b(ptr + tidx)
            if b & 0x80:  # mot 2 octets
                hi, lo = b & 0x7F, self._b(ptr + tidx + 1)
                tidx += 2
                add_word(self.word(hi, lo))
                if (hi & 0xF0) in (0x20, 0x30, 0x60):
                    break
            elif 0x20 <= b < 0x60:  # littéral
                out.append(chr(b))
                tidx += 1
            elif b >= 0x60:  # mot courant
                add_word(self._common.get(b, "?"))
                tidx += 1
            else:  # token
                if b == 0x02:  # GOTO offset signé
                    tidx += 1
                    off = self._b(ptr + tidx)
                    off -= 256 if off >= 0x80 else 0
                    ptr, tidx = ptr + tidx + off, 0
                    continue
                if b == 0x0D:  # CR inline
                    out.append("\n")
                    tidx += 1
                    continue
                if b == 0x14:
                    out.append("\n")
                    break
                if b == 0x15:
                    out.append(".")
                    break
                if b == 0x16:
                    break
                if b in (0x05, 0x0A, 0x0F, 0x12):  # no-op
                    tidx += 1
                    continue
                out.append(_TOKENS.get(b, f"<{b:02X}>"))
                tidx += 1
        return "".join(out)


def decode_message(raw: bytes, addr: int, cap: int = CAP) -> str:
    """Texte anglais lisible du message à ``addr`` (1 ligne, nettoyé)."""
    text = Decoder(raw).message(addr, cap)
    text = text.replace("\n", " ").replace('"', "'")
    text = " ".join(text.split())  # espaces multiples -> 1
    return text[:cap]


if __name__ == "__main__":
    import sys

    raw = open("data/hobbit.bin", "rb").read()
    args = sys.argv[1:]
    if args and args[0] in ("words", "dict", "--words"):
        ws = dict_words(raw)
        print(f"; {len(ws)} mots du dictionnaire ($0540-$1116)")
        print("\n".join(ws))
    else:
        addrs = [int(x, 16) for x in args] or [0x18AA, 0x143F, 0x1582]
        for a in addrs:
            print(f"${a:04X}: {decode_message(raw, a)}")
