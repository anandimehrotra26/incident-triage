# Label review report (n=60)

- category agreement: 88.3%, Cohen's kappa 0.868
- urgent agreement:   91.7%, Cohen's kappa 0.731
- disagreements: 10

## Disagreements (adjudicate each: fill final_category / final_urgent in the sheet, then run `apply`)

| id | text | recorded | reviewer | notes |
|---|---|---|---|---|
| INC-0884 | Fuel siphoning noticed on T-58, tank much lower than logged. | theft_security/0 | theft_security/1 |  |
| INC-0027 | FYI - parcel SH-96231 delivered to the wrong address, a neighbour has it. Customs paperwork is also still pending on this one. Customer has been informed. | misdelivery_lost/0 | customs_documentation/1 |  |
| INC-0199 | Wrong HS code on the declaration for SH-97527, broker needs to amend. Not sure if the shipment is complete. Will update later. | customs_documentation/0 | misdelivery_lost/0 |  |
| INC-0470 | Re PO-7769: issue w/ the sihpment, details to follow Customer has been informed. | unclear_other/0 | misdelivery_lost/0 |  |
| INC-0482 | Reporting from Pasir Panjang terminal: customer asks why delivery is delayed again, third time this month No injuries reported. | delay_late/0 | unclear_other/0 |  |
| INC-0706 | Reporting from Pasir Panjang terminal: padlock cut on the cage at Pasir Panjang terminal, inventory check ongoing Photos to follow. | theft_security/0 | theft_security/1 |  |
| INC-0137 | Subcontractor here. pilferage suspected: shortage of 6 units of phones against the manifest | theft_security/0 | misdelivery_lost/0 |  |
| INC-0167 | Gate guard here. T-423 stalled on a level crossing, driver evauating the cab. Need someone on site now. | accident_injury/1 | unclear_other/0 |  |
| INC-0779 | hi team, spare part for a grounded aircraft is delayed, the airline is escalating, shipment sh-85456. weather is bad today as well. | delay_late/1 | delay_late/0 |  |
| INC-0870 | Morning all, parcel left at the lobby and has disappeared, customer claims non-delivery This will probably delay the delivery. Please advise. | delay_late/0 | misdelivery_lost/0 |  |

## Simulation-only diagnostic
Injected label-noise rows in the sample: 2; of those the reviewer's label equals the generator's true category in 1. (A real dataset has no such column.)