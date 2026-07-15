# Stock & Stir — Quantity-Aware Inventory

**Date:** July 14, 2026  
**Area:** My Kitchen inventory

## Decision

My Kitchen now records ordinary household quantities without requiring product-level tracking.

- Countable foods use actual counts: cans, jars, boxes, bags, packages, noodles, eggs, or pieces.
- Foods commonly measured by weight or volume can use pounds, ounces, or cups.
- The system still stores one generic ingredient lot; it does not create a separate record for every can or require brands, barcodes, or package identities.
- Existing qualitative inventory records remain readable and migrate into the quantity editor when loaded.

## User impact

Examples now supported directly include `3 cans of beans`, `2 jars of sauce`, and `8 lasagna noodles`. Lasagna noodles are included in the Pantry starter list.

## Contract impact

The public My Kitchen payload now sends the existing flat `quantity` and `unit` fields. Exact positive quantities are valid without a `quantity_band`; legacy quantity bands remain backward compatible.
