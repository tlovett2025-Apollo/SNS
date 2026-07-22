# Retail Product Knowledge

Round 5 separates a purchasable product from a canonical cooking ingredient.
Barcode and photo providers return evidence; they do not write directly to the
CKB and their preparation text is not executable until reviewed.

`retail_products.py` defines eight retail kinds:

- canned ingredient;
- boxed side;
- bread product;
- sauce or condiment;
- prepared beverage;
- prepared meal;
- single ingredient; and
- unknown retail product.

Each kind owns a meal job and preparation-direction policy. Barcode drafts also
carry field-level provenance, schema version, confirmation state, enrichment
status, and their eventual promotion target.

The boundary prevents substring accidents. “Ginger ale” is a beverage, not a
package of ginger. Boxed scalloped potatoes are a known side product, not raw
potatoes. Hawaiian rolls may become a confirmed bread foundation or side, but
their marketing name does not create new cooking science.

Household confirmation may save the reviewed inventory object. Reusable retail
knowledge enters the product registry only through a later promotion gate;
canonical ingredient and behavior knowledge remain separately governed.

