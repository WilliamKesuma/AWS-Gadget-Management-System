---
inclusion: fileMatch
fileMatchPattern: "src/**/*.{ts,tsx}"
---

# SEO Implementation Protocol

Documentation reference: `src/lib/seo.ts`

## Core Principle

Every route file **must** declare a `head` function on its `Route` export. No route may omit SEO metadata.

---

## 1. SEO Constant Block

Define a typed `const` SEO object **statically at module scope** (never inside the component). Follow this naming convention: `<ROUTE_NAME>_SEO`.

```ts
const ASSETS_SEO = {
  title: 'Asset Inventory',
  description: 'Track, assign, and manage organization-wide hardware assets and their lifecycle status.',
  path: '/assets',
} satisfies import('../lib/seo').SeoPageInput
```

**Rules:**
- `title` — Short noun phrase (2–4 words), no brand suffix (added by `buildPageTitle`).
- `description` — 1–2 sentences (120–160 characters). Action-oriented, keyword-rich, unique per page.
- `path` — Must match the TanStack Router route path exactly.
- `imagePath` — Optional. Supply only when a page has a unique OG image.

---

## 2. Route Head Registration

Always attach the `head` property directly to the `createFileRoute(...)({})` options object using `buildSeoHead`:

```ts
export const Route = createFileRoute('/_authenticated/assets')({
  component: AssetsPage,
  head: () => buildSeoHead(ASSETS_SEO),
})
```

**When the head depends on loader data**, use `createSeoHeadFromLoader` instead:

```ts
export const Route = createFileRoute('/_authenticated/assets/$id')({
  loader: async ({ params }) => fetchAsset(params.id),
  component: AssetDetailPage,
  head: createSeoHeadFromLoader((asset) => ({
    title: asset?.name ?? 'Asset Detail',
    description: `View full details for asset ${asset?.name}.`,
    path: `/assets/${asset?.id}`,
  })),
})
```

---

## 3. Robots Policy by Route Type

| Route type | robots value |
|---|---|
| Public pages (login, marketing) | `index, follow` (handled by `src/lib/seo.ts` env check) |
| Authenticated / private pages | Always override with `noindex, nofollow` |

Authenticated routes **must** pass a `noindex` override inside `buildSeoHead`. Since `buildSeoHead` calls `getBaseMeta()` which already reads the env variable, authenticated pages additionally need a robots override added to the head meta. Do this by spreading an override after `buildSeoHead`:

```ts
import { buildSeoHead, getCanonicalLink, getBaseMeta, getPageMeta } from '../lib/seo'

// For authenticated routes — override robots to noindex
head: () => ({
  meta: [
    ...getBaseMeta(),
    { name: 'robots', content: 'noindex, nofollow' },
    ...getPageMeta(ASSETS_SEO),
  ],
  links: [getCanonicalLink(ASSETS_SEO.path)],
}),
```

---

## 4. Imports

Always import from the central SEO library:

```ts
import { buildSeoHead } from '../lib/seo'
// or for authenticated routes:
import { getBaseMeta, getPageMeta, getCanonicalLink } from '../lib/seo'
```

Use relative imports (not `@/lib/seo`) so the module remains portable across route nesting depths.

---

## 5. Quality Checklist

Before committing, verify each route:

- [ ] SEO const is defined at module scope with `satisfies SeoPageInput`
- [ ] `head` is declared in the route options object
- [ ] `title` is concise (≤ 50 chars) and unique across all routes
- [ ] `description` is between 120–160 characters and unique
- [ ] `path` matches the actual route path
- [ ] Authenticated routes inject `noindex, nofollow` robots override
- [ ] No inline SEO objects — always use the named const
