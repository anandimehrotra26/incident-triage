# Demo feedback

**Status: collected after submission (14-16 Nov 2026)** from two testers, Dhruv and Pranav, friends with no part in building the project. Each typed 5 reports of their own into the live demo (https://incident-triage-demo.onrender.com) with the trained thresholds (urgent 0.050, category confidence 0.85), sent screenshots, and answered the five questions below by message. Their answers are copied verbatim; nothing was edited. They answered by message rather than with the demo's yes/no buttons.

## Questions

1. Did the route and priority match what you would have chosen? (n of 5)
2. Was there a case where it was confidently wrong? What was it?
3. Did "needs human review" feel helpful or annoying?
4. What would stop you trusting it for real incidents?
5. One thing to change.

## What they typed and what the demo did

| tester | report typed | route | priority | urgent probability | top category | screenshot |
|---|---|---|---|---|---|---|
| Dhruv | Forklift toppled operator is unresponsive | human review | URGENT | 6.5% | accident_injury 32% | `docs/feedback/dhruv_1_forklift_toppled.jpg` |
| Dhruv | Shipment is 2 days late, driver is not responding | dispatch | URGENT | 89.8% | delay_late 85% | `docs/feedback/dhruv_2_late_driver_not_responding.jpg` |
| Dhruv | Customer is disappointed shipment goods arrived with scratches no damage to cargo | human review | STANDARD | 2.5% | unclear_other 46% | `docs/feedback/dhruv_3_scratches.jpg` |
| Dhruv | Gas leak from cargo | hazmat response | URGENT | 41.2% | hazmat_spill 100% | `docs/feedback/dhruv_4_gas_leak.jpg` |
| Dhruv | workers feeling faint and nauseous near shipment SH-45123 due to unknown reasons | human review | URGENT | 36.2% | unclear_other 29% | `docs/feedback/dhruv_5_workers_faint.jpg` |
| Pranav | parcel lost, customer never received | customer service | STANDARD | 2.7% | misdelivery_lost 99% | `docs/feedback/pranav_1_parcel_lost.jpg` |
| Pranav | the delivery man took extra money than he was supposed to | human review | STANDARD | 2.8% | misdelivery_lost 40% | `docs/feedback/pranav_2_extra_money.jpg` |
| Pranav | wrong items delivered | customer service | STANDARD | 4.2% | misdelivery_lost 92% | `docs/feedback/pranav_3_wrong_items.jpg` |
| Pranav | items that were returned were damaged | human review | URGENT | 12.8% | cargo_damage 80% | `docs/feedback/pranav_4_returned_damaged.jpg` |
| Pranav | someone is bleeding | safety emergency | URGENT | 99.3% | accident_injury 98% | `docs/feedback/pranav_5_bleeding.jpg` |

## Answers (verbatim)

**Dhruv (14-15 Nov 2026)**

> a. I would agree with 3 out of 5 results outputted
> b. It was 29% confident that a toppled forklift with an unresponsive operator was an unclear urgent incident which appears to be incorrect.
> c. Needs human review seems to be a very common response. The intuition for having such a response is very helpful however it probably requires more finetuning.
> d. If it is able to accurately predict real incidents I would not stop trusting it. The issue for this appears to be unreported incidents rather than reporting false urgent incidents.
> e. I would change the UI, there seems to be alot of things going on which at first glance distract you. Elements such as urgent probability, each category having a progress bar seem redundant and vibe coded. I would use more intuitive visuals which clearly display the distribution of output or confidence via a pie chart or some comparitive visual. Besides that It would help if we can view past classifications made by the model.

Note on (b): in the screenshot, the toppled-forklift report's top guess was accident_injury at 32%; the 29% unclear_other result belongs to the "workers feeling faint" report.

**Pranav (16 Nov 2026)**

> Yeah I think for A all five results matched for what I would have chosen. Then for B I don't think it was confidently wrong. For C I think I would like to have a human review rather than an AI review. I would trust a human more. Yeah I think for real incidents, like I said, I would love to talk to a person who is real. e - yeah maybe for changing, I think it would be great to have some follow-up questions so you can confirm what is actually going on and then route it to the perfect category.

## What I take from it

- **The most important finding:** "Forklift toppled operator is unresponsive" scored 6.5% urgent, just over the 5% cut-off. Neither "toppled" nor "unresponsive" appears anywhere in the 900 training reports, so the model had almost nothing to go on. This is the unseen-wording weakness in `results/RESULTS.md`, found by a real user.
- **"Needs human review" is frequent:** 5 of the 10 reports went to a person. That is the system failing safe, but it limits the saving.
- **Both testers want a person involved for real incidents,** which matches the recommendation in `BUSINESS_SUMMARY.md`: a supervised pilot, not unattended use.
- **Product ideas from testers, not yet done:** simpler confidence display, a history of past classifications (the demo has a session log, but only for the current visit), and follow-up questions before routing.
