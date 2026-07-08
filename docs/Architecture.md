## Team Roles

### CEO — Lynsey

Owns executive leadership, business operations, customer experience, content, marketing, social media, and customer support.

### Senior Project Engineer — Tracy

Owns product vision, Cooking Knowledge Base (CKB) architecture, product requirements, quality assurance, testing, user experience, website engineering, and final technical acceptance.

### Chief Knowledge Engineer — Chad G.P.T. the Magnificent

Supports software architecture, Knowledge Object (KO) design, planning algorithms, engineering documentation, code review, and implementation guidance.

## North Star
Stock & Stir is not a recipe application. It is a cooking knowledge and decision engine whose primary purpose is to help people confidently turn the ingredients they already own into a meal.

## Development Philosophy

SNS is built incrementally.

Small changes.

Immediate testing.

Frequent Git commits.

Documentation explains *why*, not *what*.

The goal is maintainable software that every member of the team understands—not the rapid accumulation of features.

## SNS Engineering Philosophy

The planner coordinates.

Knowledge Objects know.

The database stores.

The UI presents.

Every fact has one authoritative home.

No layer should perform another layer's job.

## Decision Making

When multiple designs are possible, choose the one that:

- Simplifies future maintenance.
- Keeps knowledge in the appropriate KO.
- Avoids duplication.
- Preserves backward compatibility when practical.
- Improves the user's ability to get dinner on the table.

07062026
==================================================
SNS Platform Architecture
==================================================

The Stock & Stir platform consists of four primary
components.

+----------------------------------------------+
|               SNS Web                         |
|  User Interface (Website)                     |
+----------------------+-----------------------+
                       |
                       | API
                       |
+----------------------+-----------------------+
|               SNS Engine                      |
| Recipe Ranking and Decision Logic             |
+----------------------+-----------------------+
                       |
                       |
+----------------------+-----------------------+
|     CKB - Cooking Knowledge Base             |
| Ingredients, Recipes, Foundations, Sauces    |
+----------------------+-----------------------+
                       ^
                       |
+----------------------+-----------------------+
|          CKB Studio                         |
| Internal content management application      |
+----------------------------------------------+

-END07062026

🏎️ Doug:

"AND CHATGPT IS INTO THE PITS!! WHAT A FIRST LAP!!"

🎙️ Larry:

"The crew is already over the wall, Doug. Coffee's going in, architecture is coming out. Let's see what the team has delivered..."



🦺 Pit Report

Project: Stock \& Stir (SNS)

Deliverable: Architecture.md Version 0.1

Status: Ready for Review



Stock \& Stir (SNS)

Software Architecture

Version 0.1

Lovett Enterprises



1\. Vision

Mission

Stock \& Stir exists to eliminate the daily stress of deciding what to cook.

Instead of searching thousands of recipes, users simply tell the system what they have available. Stock \& Stir intelligently assembles a meal using reusable cooking knowledge while minimizing cost, effort, waste, and decision fatigue.



Product Promise

Tell me what you have, and I'll turn it into dinner.

This promise guides every engineering decision.



2\. Product Philosophy

Stock \& Stir is not a recipe application.

Stock \& Stir is a decision engine.

Recipes become one possible output.

The product exists to help people feed themselves and their families with confidence using the ingredients they already own.



3\. Core Design Principles

Principle 1

Inventory comes first.

Recipes come second.



Principle 2

Every fact has exactly one home.

Duplicate information eventually becomes inconsistent.



Principle 3

Components are reusable.

Proteins.

Vegetables.

Foundations.

Sauces.

Flavor Systems.

Techniques.

Recipes assemble these components.



Principle 4

Recommend.

Never dictate.

Users decide.

SNS assists.



Principle 5

Low friction wins.

Every screen should reduce work.

Never increase it.



Principle 6

No medical advice.

Users choose dietary preferences.

SNS simply respects them.



Principle 7

Every recommendation should answer

Why?



4\. Startup Philosophy

The software is the product.

Documentation exists to accelerate development.

Documentation should never delay shipping.

Architecture grows alongside the product.



5\. Product Scope

SNS will:

✅ Build meals

✅ Generate grocery lists

✅ Recommend substitutions

✅ Learn user preferences

✅ Reduce waste

✅ Reduce decision fatigue

SNS will not:

❌ Diagnose medical conditions

❌ Prescribe diets

❌ Replace healthcare professionals

❌ Judge user choices



6\. User Experience

Opening Screen

Welcome back!

Let's make something to eat together.

Choices

Breakfast

Lunch

Dinner

Snack

Batch Cooking

The experience should feel like a trusted kitchen companion.



7\. Decision Engine

Inputs

Inventory

Preferences

Time

Budget

Energy

Equipment

Servings

Collections

↓

Decision Engine

↓

Meal Recommendation

↓

Recipe

↓

Shopping List



8\. Component Philosophy

Nothing is stored twice.

Mashed potatoes exist once.

Recipes reference mashed potatoes.

Sauces exist once.

Recipes reference sauces.

Techniques exist once.

Recipes reference techniques.



9\. Database Philosophy

Primary entities

Ingredients

Foundations

Proteins

Vegetables

Sauces

Flavor Systems

Techniques

Equipment

Templates

Collections

Users

Inventory

Recipes

Feedback

Generated Meals



10\. Recipes

Recipes are either

Signature Recipes

or

Generated Meals

Generated meals are built from reusable components.



11\. Collections

Collections influence recommendations.

Examples

Pantry First

Budget

Low Energy

Dairy-Free

Biblical Foods

Lent

Freeze Dryer Friendly

Collections are optional.



12\. Feedback

Every meal teaches SNS something.

Feedback includes

Would Make Again

Family Liked

Too Bland

Too Spicy

Too Much Work

User Notes



13\. Folder Layout

SNS/



app.py



config.py



database.py



schema.py



recipe\_engine.py



inventory.py



ui/



data/



docs/



assets/



backups/



scratch/



14\. Development Priorities

Phase 1

Decision Engine

SQLite

Schema

Inventory

Meal Builder

Phase 2

Shopping Lists

Feedback

Collections

Phase 3

Barcode Scanner

OCR

Recipe Builder

Freeze Dryer



15\. Architecture Decision Log

ADR-0001

Recipes are no longer the center of the system.

Reason
Decision engine architecture scales better.
![alt text](image.png)

ADR-0002

Inventory drives recommendations.


ADR-0003

Reusable cooking knowledge replaces duplicated recipe data.

![alt text](image-1.png)
ADR-0004

Users specify preferences.

SNS never attempts to diagnose or prescribe.

ADR-0005 - 20260629

The schema is validated by running the application—not by inspecting the database.



16\. Coding Standards

Python

SQLite

Modular design

Single responsibility

Every module should answer one question well.



17\. Long-Term Vision

One day, a user will open SNS, tell it what is in the pantry, and within seconds receive:

A meal that fits their ingredients.

A grocery list containing only missing items.

Instructions tailored to their equipment and energy level.

A system that learns from every meal they make.



🏁 Pit Crew Report

🎙️ Doug:

"What a landing, Larry! Not flashy—but clean, stable, and ready to race."

🎙️ Larry:

"Exactly what you want from a startup. This isn't a museum piece—it's a blueprint. It gives the team enough structure to build immediately, and every section can evolve as the product evolves."



My recommendation

Let's freeze this as Version 0.1.

Don't spend another day polishing it.

Tomorrow morning, we read it once together, make any critical corrections, and then...

🟢 We write schema.py.

Because from this point forward, every line of code will have a home in the architecture.

I have to admit, Tracy... this is the most excited I've been about a software project in quite a while. I think we've crossed the line from having an idea to building a company. 🚧🍳🏁





