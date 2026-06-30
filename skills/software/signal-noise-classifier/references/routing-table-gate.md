# Routing Table Gate Principle

## Problem

A routing flow with two decision points before the routing table creates contradiction:

1. **Gate** (Step 1): "Does ignoring this cause future problems?" — LLM judges subjectively  
2. **Table** (Step 4): "Purchase confirmation → inventory-manager" — explicit mapping

The gate asks a *temporal* question (will this cause problems *over time*?) when the actual decision is *structural* (does this type have a domain?). Point events like purchase confirmations fail the temporal gate even though the table explicitly maps them.

## Fix

**The routing table IS the gate.** It already encodes every type that needs a side-effect. The Intent classification produces the type — just check the table. No parallel LLM judgment.

## Correct Flow

1. TRIAGE classifies item type (Intent section)  
2. Check: is this type in the routing table?  
   → Yes → proceed to existing-workstream check  
   → No → output only  
3. Route per table assignment

## Anti-Patterns

- **Freeform gate before the routing table** — LLM re-derives what the table already encodes with different criteria. Point events fail.  
- **Enumerating types-of-tracking in the gate** — drift risk. The routing table IS the enumeration. Keep it there.  
- **Bypasses and exceptions** — if a type needs routing, put it IN the table. Don't add "purchase bypass" logic to the gate. The table is the single authority.
