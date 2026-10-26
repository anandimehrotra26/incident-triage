"""Synthetic incident-report generator (fully fictional, non-confidential).

Reports are composed from hand-written fragments + random slot values, then
degraded with typos / abbreviations / casing / over- and under-escalation
language. A small fraction of recorded labels are deliberately flipped to
simulate intake-clerk errors (see DATA_PROVENANCE.md).

IMPORTANT LIMITATION: this is template-derived text written by one author
(an AI assistant, directed by the project owner). It is far more regular than
real incident reports, so scores on it are optimistic. See README.

Usage:  python -m triage.data_gen            # writes data/incidents.csv and data/incidents_coldchain_ext.csv
"""
import csv
import random
import re
from pathlib import Path

from .config import BASE_CATEGORIES, NEW_CATEGORY, SEED

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ------------------------------------------------------------------ slot values
SITES = ["Tuas hub", "Jurong DC", "Changi cargo terminal", "Port Klang depot", "Johor Bahru checkpoint",
         "Pasir Panjang terminal", "Woodlands checkpoint", "Batam ferry terminal", "Penang depot",
         "Bangkok cross-dock", "Laem Chabang yard", "Kuantan warehouse", "Ipoh transfer point"]
ROLES = ["Driver", "Dock supervisor", "Warehouse clerk", "Customer", "Dispatcher", "Gate guard",
         "Shift lead", "Subcontractor", "Customer service agent", "Yard marshal"]


def slots(rng):
    return {
        "veh": rng.choice(["T-", "VAN-", "TRK-", "LRY-"]) + str(rng.randint(2, 480)),
        "cont": rng.choice(["MSKU", "TGHU", "CMAU", "OOLU"]) + str(rng.randint(100000, 999999)),
        "ref": "SH-" + str(rng.randint(10000, 99999)),
        "po": "PO-" + str(rng.randint(1000, 9999)),
        "n": rng.randint(1, 12),
        "qty": rng.choice([2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24]),
        "pct": rng.choice([5, 10, 15, 20, 30, 40]),
        "site": rng.choice(SITES),
        "hrs": rng.choice([2, 3, 4, 5, 6, 8, 12, 24, 36, 48]),
        "days": rng.choice([1, 2, 3, 4, 5]),
        "mins": rng.choice([20, 30, 45, 60, 90]),
        "temp": rng.choice([9, 10, 12, 14, 16, 18]),
    }


# ------------------------------------------------------------------ category fragments
# (non_urgent_cores, urgent_cores) -- each core is a format string using slots()
FRAGMENTS = {
    "accident_injury": (
        [
            "minor fender bender at the yard gate involving {veh}, no injuries, both vehicles still drivable",
            "forklift clipped a pallet rack at dock {n}, nobody hurt, rack needs inspection",
            "worker twisted his ankle while unloading, walked to the clinic himself, incident form to follow",
            "{veh} scraped a bollard while reversing, driver is fine, bumper cracked",
            "slipped on wet floor near dock {n}, bruised knee, back at work after first aid",
            "near miss: pallet jack almost hit a pedestrian at the loading bay, nobody injured",
            "driver reports a small collision in the car park, thankfully no one was hurt, exchanging details",
            "employee got a minor cut on the hand from a strapping band, plaster applied, logging for record",
            "reversing accident at {site}, light damage to the van, driver unharmed",
        ],
        [
            "{veh} collided with a car on the expressway, driver is bleeding and an ambulance has been called",
            "worker trapped under a fallen pallet at dock {n}, he is unconscious",
            "forklift overturned and the operator is not responding",
            "driver complaining of chest pain and cannot continue, pulled over at the roadside",
            "multi-vehicle crash involving our van {veh}, several people injured",
            "worker's hand crushed by the roller door, heavy bleeding, first aider on the way",
            "{veh} rolled over on the slip road, driver stuck in the cab and in pain",
            "pedestrian struck by a reversing lorry at {site}, casualty on the ground, calling 995",
        ],
    ),
    "hazmat_spill": (
        [
            "small oil drip from a pallet of lubricant drums, contained with absorbent, no fumes",
            "cleaning chemical bottle cracked inside a carton, small puddle in the trailer, no smell",
            "hazmat class 3 package arrived with the label missing, needs verification before storage",
            "diesel stain on the dock floor from a parked truck, minor, already cleaned up",
            "paint thinner can dented and weeping slightly at the seam, bagged and isolated",
            "{qty} aerosol cans leaking a bit of propellant in a cage, ventilated area, no one affected",
            "ink cartridges box wet with leaked liquid, non-toxic per the SDS, cleaned",
            "spill kit used for a litre of hydraulic oil near the yard, area cordoned and cleaned",
        ],
        [
            "drum of corrosive acid leaking inside the trailer, strong fumes, staff evacuated",
            "unknown liquid leaking from container {cont}, smells chemical, people coughing",
            "fuel tanker valve leaking onto the road at {site}, fire risk, traffic stopped",
            "pallet of pesticide ruptured, vapour cloud near the loading bay, we are clearing the area",
            "gas cylinders hissing and leaking in the warehouse, alarm sounding",
            "chlorine tablets drum split open and reacting with water, fumes spreading in the shed",
            "ammonia smell strong near {site} cold store, workers feeling dizzy",
        ],
    ),
    "theft_security": (
        [
            "seal broken on trailer {veh} on arrival, looks tampered overnight, {qty} cartons missing from the count",
            "pilferage suspected: shortage of {qty} units of phones against the manifest",
            "visitor badge cloned alert for pass number {n}{n}, flagged by access control, no entry made",
            "CCTV shows an unknown person near the fence last night, nothing reported missing",
            "fuel siphoning noticed on {veh}, tank much lower than logged",
            "pallet of laptops short by {qty} boxes, suspect internal theft, reviewing footage",
            "padlock cut on the cage at {site}, inventory check ongoing",
            "driver found the trailer door unlatched after rest stop, count looks fine so far",
        ],
        [
            "armed men stopped our truck near {site} and the driver is being held",
            "break-in in progress at the warehouse, alarm triggered, guard sees two people inside",
            "driver reports being followed by a car trying to force him off the road",
            "hijack attempt on route, driver locked the doors and is calling from the cab",
            "suspects still on site loading goods into a van, security needed now",
            "person threatening staff with a knife at the gate of {site}",
            "men in balaclavas cutting the fence at {site} right now, guard calling police",
        ],
    ),
    "cargo_damage": (
        [
            "received {qty} cartons crushed on pallet {n}, forklift marks visible, photos attached",
            "water damage on the bottom layer of pallets, roof leak above dock {n}",
            "pallet collapsed in transit, around {pct}% of boxes broken",
            "shrink wrap torn and {n} boxes open, goods intact but repacking needed",
            "dented machine casing noticed on delivery to the customer",
            "wet cartons after the rain, contents seem dry, will check tomorrow",
            "customer rejected {qty} units for scratched surface, packaging inadequate",
            "container {cont} opened with mould on some cartons, humidity suspected",
            "glass panels arrived with {n} cracked, claim form requested",
        ],
        [
            "medical equipment for a surgery in {hrs} hours arrived cracked, hospital needs a replacement or repair today",
            "aircraft part damaged on arrival, airline says the aircraft is grounded until a replacement arrives, shipment {ref}",
            "damaged components will stop the customer's production line in {hrs} hours, they are threatening penalties",
        ],
    ),
    "delay_late": (
        [
            "shipment {ref} is {days} days late and the customer is asking for an ETA",
            "truck stuck in traffic, will be {mins} minutes late for the dock slot at {site}",
            "port congestion, vessel berthing delayed by a day, no impact on the customer yet",
            "missed the delivery window because of a driver shortage, rescheduling",
            "customer says the parcel has not arrived since Monday, tracking shows in transit",
            "pickup not done today, collection requested again for tomorrow",
            "{ref} still at the hub, connection missed, next departure tomorrow",
            "late arrival of the linehaul trailer, outbound wave pushed back by {hrs} hours",
            "customer asks why delivery is delayed again, third time this month",
        ],
        [
            "temperature-sensitive vaccines now {hrs} hours behind schedule, the clinic needs them by noon or the doses are wasted",
            "spare part for a grounded aircraft is delayed, the airline is escalating, shipment {ref}",
            "components {hrs} hours late, the customer's production line halts without them, penalty clause active",
            "organ-transport courier delayed at {site}, hospital is waiting",
        ],
    ),
    "vehicle_breakdown": (
        [
            "check engine light on {veh}, finishing the route then going to the workshop",
            "flat tyre on {veh} at the depot, spare fitted, back in service",
            "air conditioning not working in the cab, driver uncomfortable, service requested",
            "brake pads worn on {veh}, schedule service this week",
            "battery dead on {veh} in the yard, jump started",
            "{veh} making a grinding noise from the rear axle, driver parked it at the depot",
            "wiper motor failed on {veh}, fix before the next trip",
            "power steering fluid low on {veh}, topped up, monitoring",
            "tail gate lift stuck on {veh}, loading by hand for now",
        ],
        [
            "truck {veh} broke down in the middle lane of the expressway, hazard lights on, traffic building up behind",
            "brakes failed on a downhill stretch, driver managed to stop on the shoulder with a full load",
            "engine smoking heavily on {veh}, driver pulled over and flames visible under the bonnet",
            "{veh} stalled on a level crossing, driver evacuating the cab",
            "steering locked up on {veh} while at highway speed, now stopped on the hard shoulder",
        ],
    ),
    "customs_documentation": (
        [
            "customs hold on container {cont}, commercial invoice missing",
            "wrong HS code on the declaration for {ref}, broker needs to amend",
            "bill of lading does not match the packing list for {po}",
            "certificate of origin not attached, clearance paused",
            "import permit expired for the goods on {po}, renewing",
            "documents rejected by the authority, resubmission needed by next week",
            "e-manifest mismatch on {cont}, weight differs from the declaration",
            "broker waiting for the original invoice before filing the declaration",
            "duty payment query from customs on {ref}, finance is checking",
        ],
        [
            "customs threatening to seize the shipment today if the declaration is not corrected by 5pm",
            "vessel sails in {hrs} hours and export clearance is still pending, container {cont} will miss the cut-off",
        ],
    ),
    "misdelivery_lost": (
        [
            "parcel {ref} delivered to the wrong address, a neighbour has it",
            "proof of delivery signed by someone unknown, customer denies receipt",
            "carton missing from the pallet delivered, count is {n} vs {qty}",
            "package scanned at the hub but not seen since, tracking stuck",
            "label unreadable, parcel {ref} stuck in sorting",
            "customer received someone else's order, wants it collected",
            "delivered to the wrong unit in the building, customer is upset",
            "parcel left at the lobby and has disappeared, customer claims non-delivery",
            "{ref} marked delivered but the customer says nothing arrived",
        ],
        [
            "sealed legal documents were delivered to the wrong office and are needed in court this afternoon",
            "lost parcel containing the customer's passport, flight leaves tomorrow morning",
            "wrong delivery of the replacement heart-monitor cable the ward needs tonight",
        ],
    ),
    "unclear_other": (
        [
            "problem at dock {n}, please advise",
            "something is wrong with the load, call me when you can",
            "need help with {ref}",
            "question about yesterday's issue",
            "customer is upset, please call him back",
            "see attached",
            "pls check {ref} when you get a chance",
            "not sure who handles this, the thing at {site} again",
            "follow up needed",
            "can someone look at this please",
            "issue with the shipment, details to follow",
            "weird situation at the gate, will explain later",
        ],
        [
            "help! something bad at gate {n}, come quickly",
            "need someone at {site} immediately, cannot explain on the phone",
            "emergency at dock {n}!! call me now",
            "please send someone ASAP to {site}, it's serious",
        ],
    ),
    # --- NEW category used in the changed-requirement experiment (not in the base dataset) ---
    NEW_CATEGORY: (
        [
            "temperature logger on {ref} shows a short excursion to {temp}C while the door was open, within tolerance review",
            "reefer set point was wrong on {cont}, corrected, product temperature back in range",
            "chiller alarm at {site} for {mins} minutes, goods probably unaffected, QA to check the logger",
            "pharma pallet logger shows one reading above range during the transfer, needs a QA disposition",
            "reefer unit {veh} cycling on and off, product still within the 2-8C range",
            "cold room door left ajar overnight, internal temperature reached {temp}C, stock check requested",
        ],
        [
            "reefer unit failed on {cont}, temperature now {temp}C against a required 2-8C, vaccines inside, still {hrs} hours from port",
            "freezer container alarm, temperature rising, frozen seafood on board, {hrs} hours from the destination",
            "pharma shipment {ref} logger shows {temp}C for {mins} minutes and still rising, truck is on the road",
            "cold chain failure on {veh}, refrigeration down, insulin shipment in the back, driver stuck in traffic",
        ],
    ),
}

# Base-dataset class mix and urgent rate per category (deliberately imbalanced).
CLASS_MIX = {
    "delay_late": 0.21, "cargo_damage": 0.16, "misdelivery_lost": 0.12, "customs_documentation": 0.10,
    "vehicle_breakdown": 0.11, "theft_security": 0.08, "accident_injury": 0.08, "hazmat_spill": 0.05,
    "unclear_other": 0.09,
}
URGENT_RATE = {
    "accident_injury": 0.50, "hazmat_spill": 0.55, "theft_security": 0.42, "cargo_damage": 0.08,
    "delay_late": 0.10, "vehicle_breakdown": 0.30, "customs_documentation": 0.12,
    "misdelivery_lost": 0.08, "unclear_other": 0.20, NEW_CATEGORY: 0.45,
}

# ------------------------------------------------------------------ context & noise
OPENERS_NEUTRAL = ["", "", "", "", "Hi team, ", "FYI - ", "Update on {ref}: ", "Reporting from {site}: ",
                   "{role} here. ", "Quick note: ", "Re {po}: ", "Morning all, "]
URGENT_WORDS = ["URGENT: ", "URGENT - ", "Emergency! ", "ASAP: ", "Please act immediately. ", "Need help NOW. "]
OVER_ESCALATE = ["URGENT: ", "ASAP - ", "Urgent please, ", "High priority: "]
ASKS_NEUTRAL = ["", "", "", " Please advise.", " Let me know next steps.", " Will update later.",
                " Photos to follow.", " Thanks.", " Customer has been informed.", " Logged for the record."]
URGENT_ASKS = [" Send help.", " Need someone on site now.", " Please escalate.", " Calling you now.", ""]
SECONDARY = [
    " This will probably delay the delivery.",
    " We may need to file a damage claim.",
    " Customs paperwork is also still pending on this one.",
    " The truck has also been making a noise lately.",
    " Customer has asked for an update.",
    " Weather is bad today as well.",
    " Same lane had a problem last week.",
    " Insurance may need to be told.",
    " Not sure if the shipment is complete.",
]
NO_ACCIDENT_NOISE = [" No injuries reported.", " Nobody was hurt.", " No spill.", " Not a theft as far as we know.",
                     " No damage to the cargo."]
ABBR = {"please": "pls", "customer": "cust", "delivery": "dlvry", "truck": "trk", "warehouse": "wh",
        "approximately": "approx", "container": "cntr", "shipment": "shpmt", "because": "bcos", "with": "w/",
        "driver": "drvr", "about": "abt"}

CONFUSABLE = {  # recorded-label noise: what an intake clerk might plausibly pick instead
    "delay_late": "misdelivery_lost", "misdelivery_lost": "delay_late", "cargo_damage": "theft_security",
    "theft_security": "cargo_damage", "vehicle_breakdown": "accident_injury", "accident_injury": "vehicle_breakdown",
    "customs_documentation": "delay_late", "hazmat_spill": "cargo_damage", "unclear_other": "delay_late",
    NEW_CATEGORY: "cargo_damage",
}


def typo(word, rng):
    if len(word) < 5:
        return word
    i = rng.randrange(1, len(word) - 2)
    op = rng.random()
    if op < 0.5:  # swap neighbours
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if op < 0.8:  # drop char
        return word[:i] + word[i + 1:]
    return word[:i] + word[i] + word[i:]  # double char


def degrade(text, rng, strength):
    words = text.split(" ")
    out = []
    for w in words:
        lw = w.lower().strip(",.")
        if lw in ABBR and rng.random() < 0.35 * strength:
            w = w.lower().replace(lw, ABBR[lw])
        elif rng.random() < 0.07 * strength:
            w = typo(w, rng)
        out.append(w)
    t = " ".join(out)
    if rng.random() < 0.18 * strength:
        t = t.lower()
    if rng.random() < 0.08 * strength:
        t = re.sub(r"[,.]", "", t)
    if rng.random() < 0.05 * strength:  # truncated message
        cut = int(len(t) * rng.uniform(0.6, 0.9))
        t = t[:cut].rstrip(" ,") + "..."
    return t


def build_report(rng, cat, urgent):
    non_urg, urg = FRAGMENTS[cat]
    s = slots(rng)
    s["role"] = rng.choice(ROLES)
    pool = urg if urgent else non_urg
    tidx = rng.randrange(len(pool))
    template_id = f"{cat}|{'U' if urgent else 'N'}|{tidx}"
    core = pool[tidx].format(**s)

    hard = False
    # opener: urgent reports are only sometimes labelled "urgent" by the reporter; some non-urgent ones are over-escalated
    if urgent:
        opener = rng.choice(URGENT_WORDS) if rng.random() < 0.45 else rng.choice(OPENERS_NEUTRAL).format(**s)
    else:
        opener = rng.choice(OVER_ESCALATE) if rng.random() < 0.07 else rng.choice(OPENERS_NEUTRAL).format(**s)
        if opener in OVER_ESCALATE:
            hard = True
    text = opener + core  # every opener ends with a space (or is empty)
    if text[0].islower() and rng.random() < 0.8:
        text = text[0].upper() + text[1:]
    if not text.rstrip().endswith((".", "!", "?")) and rng.random() < 0.7:
        text += "."

    # secondary clause from another category (label stays the root incident)
    if cat != "unclear_other" and rng.random() < 0.18:
        text += rng.choice(SECONDARY)
        hard = True
    # negation / absence noise ("no injuries", "no spill") on reports of OTHER categories
    if cat not in ("accident_injury", "hazmat_spill") and not urgent and rng.random() < 0.10:
        text += rng.choice(NO_ACCIDENT_NOISE)
    if urgent and rng.random() < 0.5:
        text += rng.choice(URGENT_ASKS)
    elif not urgent:
        text += rng.choice(ASKS_NEUTRAL)

    strength = rng.choice([0.0, 0.0, 0.5, 1.0, 1.6])
    if strength >= 1.6:
        hard = True
    text = degrade(text, rng, strength)
    if cat == "unclear_other":
        hard = True
    return text.strip(), hard, template_id


def generate(n, class_mix, seed, noise_rate=0.03, id_prefix="INC"):
    rng = random.Random(seed)
    cats = list(class_mix)
    counts = {c: round(n * class_mix[c]) for c in cats}
    # fix rounding drift on the largest class
    biggest = max(counts, key=counts.get)
    counts[biggest] += n - sum(counts.values())
    rows = []
    for c in cats:
        k_urg = round(counts[c] * URGENT_RATE[c])
        flags = [True] * k_urg + [False] * (counts[c] - k_urg)
        for u in flags:
            text, hard, tid = build_report(rng, c, u)
            rows.append({"category_true": c, "urgent": int(u), "text": text, "hard": int(hard), "template_id": tid})
    rng.shuffle(rows)
    for i, r in enumerate(rows):
        r["id"] = f"{id_prefix}-{i + 1:04d}"
        flipped = rng.random() < noise_rate
        r["category"] = CONFUSABLE[r["category_true"]] if flipped else r["category_true"]
        r["label_noise_injected"] = int(flipped)
    return rows


def write_csv(path, rows):
    cols = ["id", "text", "category", "urgent", "category_true", "label_noise_injected", "hard", "template_id"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in cols})


def stats_markdown(rows, title):
    import collections
    by = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        by[r["category"]][0] += 1
        by[r["category"]][1] += r["urgent"]
    L = [f"### {title}", f"Reports: {len(rows)}; urgent: {sum(r['urgent'] for r in rows)} "
         f"({sum(r['urgent'] for r in rows) / len(rows):.1%}); distinct texts: {len({r['text'] for r in rows})}; "
         f"distinct templates: {len({r['template_id'] for r in rows})}; "
         f"recorded labels flipped by simulated clerk error: {sum(r['label_noise_injected'] for r in rows)}; "
         f"flagged hard: {sum(r['hard'] for r in rows)}\n", "| recorded category | reports | urgent |", "|---|---|---|"]
    for c, (n, u) in sorted(by.items(), key=lambda kv: -kv[1][0]):
        L.append(f"| {c} | {n} | {u} |")
    return "\n".join(L) + "\n"


def main():
    DATA_DIR.mkdir(exist_ok=True)
    base = generate(900, CLASS_MIX, SEED, id_prefix="INC")
    write_csv(DATA_DIR / "incidents.csv", base)
    ext = generate(120, {NEW_CATEGORY: 1.0}, SEED + 1, id_prefix="CC")
    write_csv(DATA_DIR / "incidents_coldchain_ext.csv", ext)
    (DATA_DIR / "DATASET_STATS.md").write_text("# Dataset statistics (auto-generated)\n\n" + stats_markdown(base, "incidents.csv")
                                               + "\n" + stats_markdown(ext, "incidents_coldchain_ext.csv"))
    print(f"wrote {len(base)} base reports and {len(ext)} cold-chain extension reports to {DATA_DIR}")


if __name__ == "__main__":
    main()
