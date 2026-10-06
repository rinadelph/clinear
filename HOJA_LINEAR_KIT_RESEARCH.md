# Hoja — Linear Kit research

## Provenance

- Source: https://github.com/cloverinternational/linear-kit
- Vendored at: `vendor/linear-kit`
- Snapshot: `082f12364cb3646913ae165406ef0ce96b14e55e`
- License: MIT (confirmed in `vendor/linear-kit/package.json`)

## What Linear Kit provides

A Svelte 5, framework-agnostic Linear-style UI package with:

- `mountLinearKit()` universal mount API
- Web Component entry point
- Svelte component entry point
- React/Vue integration examples
- Scoped `.linear-kit-root` design tokens
- Light/dark/auto themes and one-color branding
- Hash/history/controlled routing modes
- App shell, sidebar, issue detail, projects, cycles, team board, settings, and other page components
- A documented UI-to-data contract and explicit EMPTY vs UNKNOWN fallback rules

## Useful patterns for Hoja

1. **Scoped design-token system:** centralize canvas, surface, line, text, muted, accent, radius, density, sidebar width, and theme mode. Hoja should adopt this instead of page-specific colors.
2. **Configurable workspace shell:** workspace identity, user identity, navigation, and chrome options should be data-driven rather than hardcoded.
3. **UI-to-data adapter boundary:** keep backend-specific GraphQL transformation outside presentation components. Map state types, priorities, initials, dates, grouping, and markdown in an adapter.
4. **Explicit data states:** distinguish known empty data from unavailable/unknown data; expose loading, partial, error, and stale status instead of silently inventing values.
5. **Page inventory discipline:** retain issue detail, team board, projects, project detail, cycles, and cycle detail; improve Inbox and Team Home; avoid shipping empty or fabricated Agent/Initiatives/Views/Workspace/Pulse/Settings surfaces until backed by real Hoja data.
6. **Mutation callbacks:** make create/update issue and comment actions explicit callbacks or API services instead of inert controls.

## Risks and constraints

- Linear Kit is Svelte 5 while Hoja is React/Vite; do not import Svelte components directly into Hoja.
- It is a UI reference/vendor snapshot, not a drop-in backend integration.
- Its docs identify hardcoded/inert controls and data-contract gaps; Hoja must not copy those defects.
- Preserve MIT provenance and keep vendor code isolated; adapt ideas/components into Hoja rather than silently treating the vendor as Hoja source.

## Recommended next Hoja improvements

- Add a real `components.json` and install selected shadcn components into `frontend/src/components/ui`.
- Introduce a typed `hojaData` adapter between GraphQL and React screens.
- Implement a real sidebar workspace menu backed by organizations/memberships.
- Build Inbox and Team Home from actual issue/comment data.
- Add issue detail routing and a real board with status-grouped issues.
- Add loading, partial, stale, and error indicators.
- Replace placeholder sections with only supported product surfaces.
