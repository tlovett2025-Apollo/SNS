# Main-Protein Execution

Round 2 separates a customer's broad cooking environment from the verified
method used by a particular protein family.

`selected environment -> protein family contract -> KO method -> activities`

For example, Oven Roast resolves to `roast` for chicken thighs, `oven_braise`
for collagen-rich brisket, `bake` for eggs, and `reheat` for an already-cooked
protein. The environment is not itself a cooking instruction.

## Contract

Every main-protein family declares:

- its safety or observable completion endpoint;
- whether a separate verification action is mandatory;
- minimum resting time;
- holding quality;
- supported broad environments and their exact KO methods; and
- at least one failure mode and recovery action in each method KO.

Sixteen current protein families are covered: ground meat, collagen-rich
roasts, stew cuts, poultry pieces, fish fillets, quick shellfish, sausage, firm
plant proteins, tender steaks, intact pork cuts, pork roasts, whole poultry,
bacon, ready proteins, eggs, and ready cured meats.

## Oven Roast

Oven Roast is distinct from Casserole / One Dish. It roasts the main protein as
its own component while selected sides retain their trained vessels. The first
oven expansion adds verified roasting or baking methods for poultry pieces,
fish fillets, sausage, firm plant proteins, pork cuts, bacon, eggs, and stew-cut
oven braises.

An oven-roasted main does not inherit braising sauce language. Sauce is warmed
separately and used as a finishing glaze or table accompaniment unless a future
component explicitly trains another application stage.

## Verification

Verification is family knowledge. When several skillet activities consolidate,
the endpoint may be absorbed into the combined cook instruction. This preserves
the mandatory temperature or observable check without creating a second,
duplicate two-minute task.

## Coverage gate

The Round 2 matrix verifies that every declared family/environment pair resolves
to a real KO method with a doneness cue, failure mode, and recovery hint. A
separate integration test compiles an oven-roasted chicken main with stovetop
macaroni and cheese.
