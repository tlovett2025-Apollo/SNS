I actually think you're protecting something very important.

One of the biggest reasons I believe SNS can succeed is because you've consistently said:

> **"Don't ask the user unnecessary questions."**

That's not a small UX preference—it's part of the product philosophy.

So let me revise what I was thinking.

## The user should almost never answer more questions.

Instead, **SNS should infer more.**

For example...

Current inputs might be:

* Protein
* Vegetables
* Foundation
* Time
* Energy
* Equipment
* Skill

That's enough.

Now suppose Energy = Low.

SNS should automatically infer things like:

* Prefer one-pan meals.
* Avoid recipes requiring constant attention.
* Avoid recipes with five different prep stages.
* Minimize cleanup.
* Favor passive cooking.

The user never answers "Do you want fewer dishes?"

SNS already knows.

---

### Another example

Time = 20 minutes.

SNS shouldn't ask:

> "Would you like to use frozen vegetables?"

It should think:

> Fresh broccoli takes longer than frozen florets.
>
> Frozen is acceptable.
>
> Time is tight.
>
> Frozen gets a higher score.

No extra question.

---

### Premium is even better.

Inventory says:

```
Fresh mushrooms
2 days old

Frozen peas

Fresh spinach
Today
```

SNS quietly thinks:

> Spinach first.

No question.

No popup.

No decision overload.

---

## This actually gives us a design rule.

I think we should write this down.

> **Never ask the user a question if the answer can be reasonably inferred from information already provided.**

That is gold.

---

## I think Horizon D becomes...

Not "more inputs."

Better inference.

For example, imagine this little internal table:

| User Input        | Engine Infers                                           |
| ----------------- | ------------------------------------------------------- |
| Low Energy        | Reduce cleanup, simplify prep, favor passive cooking    |
| 20 minutes        | Prefer quick-cooking ingredients, avoid braises         |
| Beginner          | Avoid difficult techniques, increase instruction detail |
| Air fryer only    | Remove oven candidates automatically                    |
| Premium inventory | Prefer ingredients nearing end of freshness             |
| Chicken thighs    | High forgiveness, suitable for beginners                |

The user never sees any of this.

The engine simply gets smarter.

---

## Something else just clicked.

I don't think Horizon D is really about "decision factors."

I think it's about **derived knowledge**.

Inputs become conclusions.

Example:

```
Low Energy
        ↓
Need fewer dishes
        ↓
Need fewer pans
        ↓
Need simpler meal
        ↓
Prefer skillet dinner
        ↓
Rank skillet recipes higher
```

That's a chain of inference.

Not another user setting.

---

### I think we're accidentally building an expert system.

And I mean that in the old-school AI sense.

Users provide a handful of facts.

SNS derives dozens of additional facts.

Those derived facts influence ranking.

That feels very much in line with the product you've been describing for weeks.

The user doesn't experience more complexity. In fact, they experience **less**. The intelligence moves behind the curtain, where it belongs.
