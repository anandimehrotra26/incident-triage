# Label review report (n=60)

- category agreement: 85.0%, Cohen's kappa 0.829
- urgent agreement:   86.7%, Cohen's kappa 0.632
- disagreements: 16

## Disagreements (adjudicate each: fill final_category / final_urgent in the sheet, then run `apply`)

| id | text | recorded | reviewer | notes |
|---|---|---|---|---|
| INC-0260 | Re PO-2389: customer rejected 20 uits for scratched surface, packaging inadequate. | cargo_damage/0 | misdelivery_lost/0 | im guessing because its the only option that seems to work for rejected delivery |
| INC-0789 | Hi team, parcel SH-89525 delivered to the wrong address, a neighbour has it | misdelivery_lost/0 | misdelivery_lost/1 |  |
| INC-0136 | ASAP - ink cartridges box wet w/ leaked liquid, non-toxic per the SDS, cleaned. Let me know next steps. | hazmat_spill/0 | cargo_damage/0 |  |
| INC-0431 | ASAP - CCTV shows an unknown person near the fence last night, nothing reported missing Thanks. | theft_security/0 | theft_security/1 |  |
| INC-0243 | customer rejected 6 units for scratched surface, packaging inadequate No damage to the cargo. Photos to follow. | cargo_damage/0 | misdelivery_lost/0 |  |
| INC-0377 | high priority: not sure who handles this, the thing at jurong dc again. thanks. | unclear_other/0 | unclear_other/1 |  |
| INC-0470 | Re PO-7769: issue w/ the sihpment, details to follow Customer has been informed. | unclear_other/0 | misdelivery_lost/0 |  |
| INC-0010 | ASAP - trk stuck in traffic, will be 45 minutes late for the dock slot at Bangkok cross-dock Please advise. | delay_late/0 | delay_late/1 |  |
| INC-0475 | Reporting from Pasir Panjang terminal: bill of lading does not match the packing list for PO-4887 Will update later. | customs_documentation/0 | unclear_other/0 |  |
| INC-0167 | Gate guard here. T-423 stalled on a level crossing, driver evauating the cab. Need someone on site now. | accident_injury/1 | vehicle_breakdown/1 |  |
| INC-0303 | morning all, customer rejected 4 units for scratched surface, packaging inadequate. will update later. | cargo_damage/0 | misdelivery_lost/0 |  |
| INC-0779 | hi team, spare part for a grounded aircraft is delayed, the airline is escalating, shipment sh-85456. weather is bad today as well. | delay_late/1 | delay_late/0 |  |
| INC-0870 | Morning all, parcel left at the lobby and has disappeared, customer claims non-delivery This will probably delay the delivery. Please advise. | delay_late/0 | theft_security/1 |  |
| INC-0728 | Re PO-2927: customer is upset, please call him back. Photos to follow. | unclear_other/0 | unclear_other/1 |  |
| INC-0004 | customer rejected 3 units for scratched surface, packaging inadequate. Thanks. | cargo_damage/0 | misdelivery_lost/0 |  |
| INC-0326 | shipment SH-15651 is 3 days late and the customer is asking for an ETA. | delay_late/0 | delay_late/1 |  |

## Simulation-only diagnostic
Injected label-noise rows in the sample: 2; of those the reviewer's label equals the generator's true category in 1. (A real dataset has no such column.)