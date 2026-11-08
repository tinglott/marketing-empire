# Vendor attribution

## trend-pulse — https://github.com/claude-world/trend-pulse — MIT
"MIT License / Copyright (c) 2026 Claude World / Permission is hereby granted,
free of charge, to any person obtaining a copy of this software…"
Full text: `trend-pulse-LICENSE.txt` (copied from the installed package's
dist-info licenses directory; the same text was read from
raw.githubusercontent.com/claude-world/trend-pulse/main/LICENSE on Nov 8, 2026).
Used via pip (`pip install trend-pulse`, 2.1.0) — NOT vendored as source, because
the pip install worked. The `trend` command calls its library; if it is
unavailable it falls back to direct RSS/Atom fetches.

## social-campaigns — https://github.com/mrsahilbeniwal/social-campaigns — MIT
"MIT License / Copyright (c) 2026 Sahil Beniwal / Permission is hereby granted,
free of charge, to any person obtaining a copy of this software…"
Vendored files (unchanged, with the project's LICENSE):
- `social-campaigns/platform-specs.md` — per-platform character/hashtag caps
- `social-campaigns/prompt-templates.md` — campaign prompt templates
- `social-campaigns/LICENSE`
Only the platform rules were adopted into `empire.py`. social-campaigns has NO
disclosure/FTC language — the house `#ad` rule fills that gap.

## PurffleShorts — https://github.com/Chamanrajragu/purffle-shorts — MIT
"MIT License / Copyright (c) 2025 Purffle / Permission is hereby granted, free
of charge, to any person obtaining a copy of this software…"
NOT vendored and NOT a dependency of the core. Documented as the optional
stock-footage / word-caption upgrade engine in `docs/purffleshorts.md`.
