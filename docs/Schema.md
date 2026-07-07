Stock \& Stir (SNS)

Schema Specification

Version 0.1



Purpose

This document defines the initial logical schema for Stock \& Stir (SNS). The guiding principle is: "Tell me what you have, and I'll turn it into dinner."

Core Philosophy

•	Inventory is the primary input.

•	Decision Engine is the core product.

•	Recipes are assemblies of reusable components.

•	Every fact has exactly one home.

Core Tables

•	ingredients

•	ingredient\_forms

•	prep\_forms

Component Tables

•	proteins

•	vegetables

•	foundations

•	sauces

•	flavor\_systems

•	techniques

•	equipment

Meal Assembly

•	meal\_templates

•	template\_slots

Rules Engine

•	compatibility\_rules

•	substitution\_rules

•	constraint\_rules

Recipe Tables

•	signature\_recipes

•	signature\_recipe\_components

•	signature\_recipe\_instructions

Inventory \& Grocery

•	user\_inventory

•	grocery\_lists

•	grocery\_list\_items

Users

•	users

•	user\_preferences

•	meal\_feedback

Collections

•	collections

•	collection\_members

•	collection\_rules

Implementation Order

•	schema.py

•	SQLite database

•	Seed lookup tables

•	Decision Engine

•	Streamlit UI

Change Log

2026-06-29 | v000.1 | Author: ChatGPT | Reviewer: Tracy Lovett | Status: Draft

Initial schema specification created from the approved SNS architecture.



