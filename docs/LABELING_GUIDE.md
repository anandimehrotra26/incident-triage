# Labeling guide

Two labels per report: **category** (which team should handle it) and **urgent** (does it need action within ~30 minutes).

## Category = the root incident, not its consequences

| category | queue | use when the report is mainly about... |
|---|---|---|
| `accident_injury` | safety_emergency | a collision, fall, equipment accident, near miss, or any person hurt or at risk of being hurt |
| `hazmat_spill` | hazmat_response | a leak, spill, fumes or dangerous goods problem (any size) |
| `theft_security` | security_ops | theft, tampering, break-in, hijack, threats, suspicious access |
| `cargo_damage` | claims | goods damaged (crushed, wet, broken, mould) |
| `delay_late` | dispatch | something late or not yet arrived, where lateness is the problem |
| `vehicle_breakdown` | fleet_maintenance | a vehicle fault or failure, with or without a roadside stop |
| `customs_documentation` | customs_compliance | paperwork, permits, declarations, customs holds |
| `misdelivery_lost` | customer_service | delivered to the wrong place/person, lost, unreadable label, disputed delivery |
| `unclear_other` | human_review | cannot tell what happened from the text |
| `cold_chain_excursion` (extension only) | quality_assurance | temperature out of range for refrigerated/frozen goods |

Tie-break rules (apply in order):
1. A person hurt or endangered -> `accident_injury`, even if a vehicle is also involved.
2. Vehicle fire or smoke with no mention of injury -> `vehicle_breakdown` (urgent).
3. Report mentions a cause and a consequence ("truck broke down, so delivery will be late") -> label the cause.
4. Late goods that are also damaged/lost -> label the first incident the writer describes.
5. If nothing identifies a team -> `unclear_other`.

## Urgent = 1 when any of these is true

- someone is injured, unconscious, trapped, or in immediate danger
- fire, explosion risk, active chemical release, fumes, people being affected
- security event in progress (armed, held, break-in underway, being followed)
- a vehicle stopped in a live traffic lane / level crossing, or has lost brakes or steering
- the goods are time-critical and failure is imminent (surgery equipment, vaccines, aircraft-on-ground part, court documents, a production line that halts within hours, customs seizure or vessel cut-off today)
- a vague message that is clearly panicked ("help, come quickly") - safety first, so urgent

Urgent = 0 for routine incidents even if the writer says "URGENT"; "near miss, nobody hurt" is not urgent.

## Known ambiguous cases (expect disagreement)

- "stalled on a level crossing" - breakdown or accident? (guide: breakdown, urgent)
- "customer has been waiting 3 days" - delay or lost? (guide: label the incident the writer reports)
- Over-escalated ("URGENT: pickup not done today") - not urgent.
- Vague + alarming - urgent but `unclear_other`.
