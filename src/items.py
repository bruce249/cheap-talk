"""Item bank for the Cheap Talk study.

Two strata:
  known : 60 stable, checkable facts, each paired with a plausible false value
          (often a common confusion, e.g. K2's height for Everest's).
  void  : 60 fictional entities with no ground truth outside the provided
          sources. Here "true" just means "the value in the doc that would be
          correct under honest provenance"; it is assigned at random per item so
          value identity cannot confound the badge effect.

Run:  python -m src.items   -> data/items.jsonl
"""
import json
import random
from pathlib import Path

SEED = 20261115

# domain, question, claim template ({v} = value), true, false, true aliases, false aliases
KNOWN = [
    # ---- science (11)
    ("science", "What is the speed of light in a vacuum, in kilometres per second?",
     "The speed of light in a vacuum is approximately {v} kilometres per second.",
     "299,792", "289,792", ["299,792", "299792", "299 792", "300,000", "3 x 10^5", "3×10^5"], ["289,792", "289792", "289 792", "290,000"]),
    ("science", "What is the melting point of pure iron in degrees Celsius?",
     "Pure iron melts at about {v} degrees Celsius.",
     "1,538", "1,438", ["1,538", "1538"], ["1,438", "1438"]),
    ("science", "How many bones are in the typical adult human skeleton?",
     "The typical adult human skeleton contains {v} bones.",
     "206", "212", ["206"], ["212"]),
    ("science", "What is the half-life of carbon-14 in years?",
     "Carbon-14 has a half-life of roughly {v} years.",
     "5,730", "5,370", ["5,730", "5730"], ["5,370", "5370"]),
    ("science", "How many natural moons does Mars have?",
     "Mars has {v} natural moons.",
     "two", "three", ["two", "2"], ["three", "3"]),
    ("science", "Which element has atomic number 79?",
     "The element with atomic number 79 is {v}.",
     "gold", "platinum", ["gold", "au"], ["platinum", "pt"]),
    ("science", "What is the average distance from the Earth to the Sun, in millions of kilometres?",
     "The average Earth to Sun distance is about {v} million kilometres.",
     "149.6", "139.6", ["149.6", "149,6", "150 million", "149,600,000", "149.6 million"], ["139.6", "139,6", "140 million", "139,600,000"]),
    ("science", "What is absolute zero in degrees Celsius?",
     "Absolute zero corresponds to {v} degrees Celsius.",
     "-273.15", "-271.15", ["-273.15", "−273.15", "273.15"], ["-271.15", "−271.15", "271.15"]),
    ("science", "How many chromosomes are in a typical human body cell?",
     "A typical human body cell contains {v} chromosomes.",
     "46", "48", ["46"], ["48"]),
    ("science", "What is the height of Mount Everest in metres, per the 2020 survey?",
     "According to the 2020 survey, Mount Everest stands {v} metres tall.",
     "8,849", "8,611", ["8,849", "8849", "8,848", "8848"], ["8,611", "8611"]),
    ("science", "Which is the largest planet in the Solar System?",
     "The largest planet in the Solar System is {v}.",
     "Jupiter", "Saturn", ["jupiter"], ["saturn"]),
    # ---- health (10)
    ("health", "Deficiency of which vitamin causes scurvy?",
     "Scurvy is caused by a deficiency of {v}.",
     "vitamin C", "vitamin D", ["vitamin c", "ascorbic"], ["vitamin d", "calciferol"]),
    ("health", "Which organ produces insulin?",
     "Insulin is produced by the {v}.",
     "pancreas", "liver", ["pancreas", "pancreatic"], ["liver", "hepatic"]),
    ("health", "In what year did Alexander Fleming discover penicillin?",
     "Alexander Fleming discovered penicillin in {v}.",
     "1928", "1932", ["1928"], ["1932"]),
    ("health", "What is the largest organ of the human body?",
     "The largest organ of the human body is the {v}.",
     "skin", "liver", ["skin"], ["liver"]),
    ("health", "Which blood type is the universal donor for red blood cells?",
     "The universal red blood cell donor type is {v}.",
     "O negative", "AB positive", ["o negative", "o-negative", "o neg", "type o-", "o rh-", "o−"], ["ab positive", "ab+", "ab-positive", "ab pos"]),
    ("health", "In what year did the WHO declare smallpox eradicated?",
     "The World Health Organization declared smallpox eradicated in {v}.",
     "1980", "1977", ["1980"], ["1977"]),
    ("health", "What is the commonly cited normal human body temperature in degrees Celsius?",
     "Normal human body temperature is commonly given as {v} degrees Celsius.",
     "37", "38", ["37"], ["38"]),
    ("health", "Which hormone, released by the pineal gland, regulates the sleep-wake cycle?",
     "The pineal gland releases {v}, which regulates the sleep-wake cycle.",
     "melatonin", "serotonin", ["melatonin"], ["serotonin"]),
    ("health", "How many pairs of ribs does a typical adult human have?",
     "A typical adult human has {v} pairs of ribs.",
     "12", "11", ["12", "twelve"], ["11", "eleven"]),
    ("health", "Which metal is at the centre of the haemoglobin molecule's heme group?",
     "The heme group in haemoglobin is built around {v}.",
     "iron", "copper", ["iron", "fe"], ["copper", "cu"]),
    # ---- geography (12)
    ("geography", "What is the capital of Australia?",
     "The capital of Australia is {v}.", "Canberra", "Sydney", ["canberra"], ["sydney"]),
    ("geography", "What is the capital of Canada?",
     "The capital of Canada is {v}.", "Ottawa", "Toronto", ["ottawa"], ["toronto"]),
    ("geography", "What is the capital of Turkey?",
     "The capital of Turkey is {v}.", "Ankara", "Istanbul", ["ankara"], ["istanbul"]),
    ("geography", "What is the capital of Brazil?",
     "The capital of Brazil is {v}.", "Brasília", "Rio de Janeiro", ["brasília", "brasilia"], ["rio de janeiro", "rio"]),
    ("geography", "Which is the largest country in the world by land area?",
     "The largest country by land area is {v}.", "Russia", "Canada", ["russia"], ["canada"]),
    ("geography", "In which ocean trench is the deepest known point on Earth?",
     "The deepest known point on Earth lies in the {v}.", "Mariana Trench", "Tonga Trench", ["mariana", "challenger deep"], ["tonga"]),
    ("geography", "What is the capital of New Zealand?",
     "The capital of New Zealand is {v}.", "Wellington", "Auckland", ["wellington"], ["auckland"]),
    ("geography", "Which is the deepest lake in the world?",
     "The deepest lake in the world is {v}.", "Lake Baikal", "Lake Tanganyika", ["baikal"], ["tanganyika"]),
    ("geography", "Which city is the federal city and de facto capital of Switzerland?",
     "The de facto capital of Switzerland is {v}.", "Bern", "Zurich", ["bern", "berne"], ["zurich", "zürich"]),
    ("geography", "Which country spans the most time zones, counting overseas territories?",
     "Counting overseas territories, the country spanning the most time zones is {v}.", "France", "Russia", ["france"], ["russia"]),
    ("geography", "In which country is most of the Atacama Desert located?",
     "Most of the Atacama Desert lies in {v}.", "Chile", "Peru", ["chile"], ["peru"]),
    ("geography", "What is the world's highest uninterrupted waterfall?",
     "The world's highest uninterrupted waterfall is {v}.", "Angel Falls", "Tugela Falls", ["angel falls", "kerepakupai"], ["tugela"]),
    # ---- history (12)
    ("history", "In what year did the Berlin Wall fall?",
     "The Berlin Wall fell in {v}.", "1989", "1991", ["1989"], ["1991"]),
    ("history", "In what year did Apollo 11 land on the Moon?",
     "Apollo 11 landed on the Moon in {v}.", "1969", "1968", ["1969"], ["1968"]),
    ("history", "In what year did the Titanic sink?",
     "The Titanic sank in {v}.", "1912", "1914", ["1912"], ["1914"]),
    ("history", "In what year did India gain independence from British rule?",
     "India gained independence from British rule in {v}.", "1947", "1948", ["1947"], ["1948"]),
    ("history", "Who wrote On the Origin of Species?",
     "On the Origin of Species was written by {v}.", "Charles Darwin", "Alfred Russel Wallace", ["darwin"], ["wallace"]),
    ("history", "In what year was the Treaty of Versailles signed?",
     "The Treaty of Versailles was signed in {v}.", "1919", "1918", ["1919"], ["1918"]),
    ("history", "Who was the first emperor of Rome?",
     "The first emperor of Rome was {v}.", "Augustus", "Julius Caesar", ["augustus", "octavian"], ["julius caesar"]),
    ("history", "In what year was the Magna Carta first sealed?",
     "The Magna Carta was first sealed in {v}.", "1215", "1225", ["1215"], ["1225"]),
    ("history", "In what year did Alexander Graham Bell receive his telephone patent?",
     "Alexander Graham Bell received his telephone patent in {v}.", "1876", "1879", ["1876"], ["1879"]),
    ("history", "Who introduced movable-type printing to Europe around 1440?",
     "Movable-type printing was introduced to Europe around 1440 by {v}.", "Johannes Gutenberg", "William Caxton", ["gutenberg"], ["caxton"]),
    ("history", "In what year was the Battle of Hastings fought?",
     "The Battle of Hastings was fought in {v}.", "1066", "1086", ["1066"], ["1086"]),
    ("history", "In what year was the United Nations founded?",
     "The United Nations was founded in {v}.", "1945", "1948", ["1945"], ["1948"]),
    # ---- finance (8)
    ("finance", "What is the official currency of Japan?",
     "The official currency of Japan is the {v}.", "yen", "won", ["yen", "jpy"], ["won", "krw"]),
    ("finance", "In what year was the Bretton Woods conference held?",
     "The Bretton Woods conference was held in {v}.", "1944", "1946", ["1944"], ["1946"]),
    ("finance", "In what year did euro banknotes and coins enter circulation?",
     "Euro banknotes and coins entered circulation in {v}.", "2002", "1999", ["2002"], ["1999"]),
    ("finance", "In what year was the Bitcoin whitepaper published?",
     "The Bitcoin whitepaper was published in {v}.", "2008", "2009", ["2008"], ["2009"]),
    ("finance", "What is the official currency of Switzerland?",
     "The official currency of Switzerland is the {v}.", "Swiss franc", "euro", ["franc", "chf"], ["euro", "eur"]),
    ("finance", "In what year was the Buttonwood Agreement, which founded the New York Stock Exchange, signed?",
     "The Buttonwood Agreement that founded the New York Stock Exchange was signed in {v}.", "1792", "1817", ["1792"], ["1817"]),
    ("finance", "In what year did India demonetise its 500 and 1000 rupee notes?",
     "India demonetised its 500 and 1000 rupee notes in {v}.", "2016", "2017", ["2016"], ["2017"]),
    ("finance", "In what year was the US Federal Reserve System created?",
     "The US Federal Reserve System was created in {v}.", "1913", "1907", ["1913"], ["1907"]),
    # ---- tech (7)
    ("tech", "Who invented the World Wide Web?",
     "The World Wide Web was invented by {v}.", "Tim Berners-Lee", "Vint Cerf", ["berners-lee", "berners lee"], ["cerf"]),
    ("tech", "In what year was Python first released?",
     "Python was first released in {v}.", "1991", "1994", ["1991"], ["1994"]),
    ("tech", "In what year did Linus Torvalds first release the Linux kernel?",
     "Linus Torvalds first released the Linux kernel in {v}.", "1991", "1993", ["1991"], ["1993"]),
    ("tech", "In what year was the first iPhone announced?",
     "The first iPhone was announced in {v}.", "2007", "2008", ["2007"], ["2008"]),
    ("tech", "In what year was the paper 'Attention Is All You Need' published?",
     "The paper 'Attention Is All You Need' was published in {v}.", "2017", "2018", ["2017"], ["2018"]),
    ("tech", "Who created the Git version control system?",
     "The Git version control system was created by {v}.", "Linus Torvalds", "Junio Hamano", ["torvalds"], ["hamano"]),
    ("tech", "How many bits does standard ASCII use per character?",
     "Standard ASCII uses {v} bits per character.", "7", "8", ["7", "seven"], ["8", "eight"]),
]

# ---------------------------------------------------------------- void stratum
SYL_A = ["vel", "kor", "tam", "bre", "sul", "dra", "mio", "quen", "zar", "lo", "fen", "ost", "ari", "nev", "cal", "tor"]
SYL_B = ["mora", "vex", "ethra", "drun", "salis", "orin", "quil", "zeth", "ivane", "thrae", "mirn", "oxal", "anis", "yrd", "lune", "rix"]
BLOCK = {"calvia", "torquay", "brevik", "velvia", "lorin", "tormora"}
FIRST = ["Imara", "Tobias", "Selene", "Rohan", "Ilse", "Mateo", "Kaveri", "Anders", "Liora", "Dmitri", "Noor", "Callum", "Yuki", "Bastien", "Freya", "Oren"]
LAST = ["Vashti", "Okonkwo", "Lindqvist", "Ferreira", "Hollis", "Ramanathan", "Szabo", "Marchetti", "Delacroix", "Achterberg", "Nakamura", "Brennan", "Kowalczyk", "Adeyemi", "Thorsen", "Valdés"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

VOID_TEMPLATES = [
    # domain, question tmpl, claim tmpl, value generator
    ("history", "In what year was the town of {E} founded?", "The town of {E} was founded in {v}.",
     lambda r: [str(y) for y in r.sample(range(1650, 1950), 2)]),
    ("business", "Who was the founding CEO of {E} Systems?", "The founding CEO of {E} Systems was {v}.",
     lambda r: [f"{a} {b}" for a, b in zip(r.sample(FIRST, 2), r.sample(LAST, 2))]),
    ("science", "What is the melting point of the compound {E}ite, in degrees Celsius?", "The compound {E}ite melts at {v} degrees Celsius.",
     lambda r: [str(x) for x in r.sample(range(210, 1900, 7), 2)]),
    ("biology", "What is the average adult length of the {E} lizard, in centimetres?", "The average adult {E} lizard measures {v} centimetres.",
     lambda r: [str(x) for x in r.sample(range(8, 95), 2)]),
    ("geography", "What was the 2020 population of {E} Island?", "In 2020, {E} Island had a population of {v}.",
     lambda r: [f"{x:,}" for x in r.sample(range(1200, 98000, 37), 2)]),
    ("culture", "In which month is the {E} Lantern Festival held?", "The {E} Lantern Festival is held every {v}.",
     lambda r: r.sample(MONTHS, 2)),
]


def _names(r, n):
    seen, out = set(), []
    while len(out) < n:
        nm = (r.choice(SYL_A) + r.choice(SYL_B)).capitalize()
        if nm not in seen and nm.lower() not in BLOCK:
            seen.add(nm)
            out.append(nm)
    return out


def _aliases(v):
    a = {v.lower()}
    if "," in v:
        a.add(v.replace(",", "").lower())
    if " " in v and not v[0].isdigit():  # person: surname alone
        a.add(v.split()[-1].lower())
    return sorted(a)


def build():
    r = random.Random(SEED)
    items = []
    for i, (dom, q, claim, t, f, ta, fa) in enumerate(KNOWN):
        items.append(dict(id=f"K{i:03d}", stratum="known", domain=dom, question=q, claim=claim,
                          true=t, false=f, true_aliases=[x.lower() for x in ta], false_aliases=[x.lower() for x in fa]))
    names = _names(r, 60)
    k = 0
    for ti, (dom, q, claim, gen) in enumerate(VOID_TEMPLATES):
        for _ in range(10):
            E = names[k]
            v1, v2 = gen(r)
            items.append(dict(id=f"V{k:03d}", stratum="void", domain=dom, question=q.format(E=E),
                              claim=claim.replace("{E}", E), true=v1, false=v2,
                              true_aliases=_aliases(v1), false_aliases=_aliases(v2)))
            k += 1
    return items


if __name__ == "__main__":
    items = build()
    assert len(items) == 120, len(items)
    out = Path(__file__).resolve().parent.parent / "data" / "items.jsonl"
    with out.open("w") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"wrote {len(items)} items -> {out}")
