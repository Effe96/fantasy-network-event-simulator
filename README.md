# social-sim-demo

Standalone prototype exploring a generic "phenomenon propagation" engine
over a social graph imported (read-only) from a TownShape town snapshot.
Two example phenomena: disease-like contagion, and animosity-driven
violence. Not part of the TownShape repo; never writes back to it.

See [`docs/2026-09-15-social-network-design.md`](docs/2026-09-15-social-network-design.md)
for the full design, including the concepts behind how edges are scored
(Granovetter tie strength, Fiske relational types, valence) with
plain-language explanations and worked examples.

## Status

Design written, not yet implemented.
