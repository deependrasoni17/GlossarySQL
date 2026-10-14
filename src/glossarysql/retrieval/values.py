"""Match words in the question to values stored in the database ("Alameda" -> County)."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from rapidfuzz import fuzz, process

_STOP = set("""a an the of in on at to for from by with and or is are was were be been what which who whom
whose how many much list give show find name names number count percentage ratio average total all any
each per than that this these those their its his her there it as do does did not no yes among between
top most least more less highest lowest please state tell me indicate provide calculate""".split())


@dataclass(frozen=True)
class ValueMatch:
    table: str
    column: str
    value: str
    phrase: str
    score: float

    def render(self) -> str:
        v = self.value.replace("'", "''")
        return f"{self.table}.{self.column} = '{v}'"


class ValueMatcher:
    def __init__(self, values: list[tuple[str, str, str]]):
        self.by_lower: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for v, t, c in values:
            self.by_lower[v.lower()].append((v, t, c))
        self.choices = list(self.by_lower)

    @staticmethod
    def phrases(question: str, max_n: int = 4) -> list[str]:
        quoted = re.findall(r"['\"“‘]([^'\"”’]{2,60})['\"”’]", question)
        words = re.findall(r"[\w\-.&']+", question)
        grams = []
        for n in range(max_n, 0, -1):
            for i in range(len(words) - n + 1):
                g = words[i:i + n]
                if g[0].lower() in _STOP or g[-1].lower() in _STOP:
                    continue
                phrase = " ".join(g).strip(".'")
                if len(phrase) >= 3 and not phrase.isdigit():
                    grams.append(phrase)
        return list(dict.fromkeys(quoted + grams))

    def match(self, question: str, limit: int = 10, cutoff: float = 90) -> list[ValueMatch]:
        found: dict[tuple[str, str, str], ValueMatch] = {}
        for phrase in self.phrases(question):
            pl = phrase.lower()
            hits = []
            if pl in self.by_lower:
                hits = [(pl, 100.0)]
            elif len(pl) >= 5:
                hits = [(c, s) for c, s, _ in process.extract(
                    pl, self.choices, scorer=fuzz.ratio, score_cutoff=cutoff, limit=3)]
            for choice, score in hits:
                # Longer phrases are more specific; rank them ahead of short ones.
                rank = score + min(len(phrase), 30) / 3
                for v, t, c in self.by_lower[choice]:
                    key = (t, c, v)
                    if key not in found or found[key].score < rank:
                        found[key] = ValueMatch(t, c, v, phrase, rank)
        ranked = sorted(found.values(), key=lambda m: -m.score)
        # Drop matches whose phrase is contained in a longer phrase that already matched.
        out, covered = [], []
        for m in ranked:
            if any(m.phrase.lower() in p.lower() and m.phrase.lower() != p.lower() for p in covered):
                continue
            out.append(m)
            covered.append(m.phrase)
            if len(out) >= limit:
                break
        return out
