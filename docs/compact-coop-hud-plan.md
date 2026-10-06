# Compact co-op HUD (parked)

Owner request, 2026-10-05. Tracker: beads-8wg.1.116.
Branch: feat/compact-coop-hud. Base: origin/main d409e26.

No implementation is requested yet. Resume only when the owner asks.

Layout confirmed by the owner, 2026-10-05:

| Upper player row | |
| --- | --- |
| X health | X ammo |
| Zero health | Zero ammo |

Both columns align vertically. Each player has two adjacent vertical bars.
X uses the current orientation, with the player/weapon icons at the bottom.
Zero's icons are at the top of his bars, facing X's icons across the row gap.
Zero's fill grows from bottom to top; recommended depletion is from the top
so the remaining fill stays at the bottom. Preserve readable numeric/tick
semantics if the existing renderer supplies them.

The intent is two bar widths instead of four, with more vertical stacking.
Choose bar height and spacing during visual design so the combined panel is
compact and does not obscure gameplay. Use the existing game pixel art and
HUD style. Preserve weapon identity and the current handling of absent ammo.

## Acceptance

Show the owner real gameplay screenshots or a live candidate before marking
this done or shipping it. Final owner visual review is required.

Review full, partial and empty health/ammo, health-only and weapon-equipped
states, 4:3 and widescreen, and both player character assignments. Preserve
single-player HUD behavior and keep boss health readable without overlap.
