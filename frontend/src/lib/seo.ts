const FALLBACK_SITE_URL = 'https://example.com'
const FALLBACK_OG_IMAGE = '/og-default.png'

const envSiteUrl = import.meta.env.VITE_SITE_URL?.trim()
const envOgImage = import.meta.env.VITE_OG_IMAGE?.trim()

export const SITE_URL = (
  envSiteUrl && envSiteUrl.length > 0 ? envSiteUrl : FALLBACK_SITE_URL
).replace(/\/$/, '')
export const SITE_NAME = 'Gadget Management System'
export const DEFAULT_TITLE = 'Inventory and lifecycle tracking for every gadget'
export const DEFAULT_DESCRIPTION =
  'Track gadget inventory, assignments, maintenance, and lifecycle status from one clear workspace.'
export const DEFAULT_OG_IMAGE =
  envOgImage && envOgImage.length > 0 ? envOgImage : FALLBACK_OG_IMAGE

export type MetaTag = {
  title?: string
  charSet?: string
  name?: string
  content?: string
  property?: string
}

export type LinkTag = {
  rel: string
  href: string
}

export type SeoPageInput = {
  title: string
  description: string
  path: string
  imagePath?: string
}

export type SeoHeadOutput = {
  meta: MetaTag[]
  links: LinkTag[]
}

export function buildPageTitle(title: string): string {
  return `${title} | ${SITE_NAME}`
}

export function buildCanonicalUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${SITE_URL}${normalizedPath}`
}

export function getRobotsContent(): string {
  if (!import.meta.env.PROD) {
    return 'noindex, nofollow'
  }

  if (import.meta.env.VITE_ENABLE_INDEXING === 'false') {
    return 'noindex, nofollow'
  }

  return 'index, follow'
}

export function getBaseMeta(): MetaTag[] {
  return [
    { charSet: 'utf-8' },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    { name: 'robots', content: getRobotsContent() },
    { property: 'og:type', content: 'website' },
    { property: 'og:site_name', content: SITE_NAME },
    { name: 'twitter:card', content: 'summary_large_image' },
  ]
}

export function getPageMeta(input: SeoPageInput): MetaTag[] {
  const canonical = buildCanonicalUrl(input.path)
  const imageUrl = input.imagePath?.startsWith('http')
    ? input.imagePath
    : `${SITE_URL}${input.imagePath ?? DEFAULT_OG_IMAGE}`

  return [
    { title: buildPageTitle(input.title) },
    { name: 'description', content: input.description },
    { property: 'og:title', content: buildPageTitle(input.title) },
    { property: 'og:description', content: input.description },
    { property: 'og:url', content: canonical },
    { property: 'og:image', content: imageUrl },
    { name: 'twitter:title', content: buildPageTitle(input.title) },
    { name: 'twitter:description', content: input.description },
    { name: 'twitter:image', content: imageUrl },
  ]
}

export function getCanonicalLink(path: string): LinkTag {
  return {
    rel: 'canonical',
    href: buildCanonicalUrl(path),
  }
}

export function buildSeoHead(input: SeoPageInput): SeoHeadOutput {
  return {
    meta: [...getBaseMeta(), ...getPageMeta(input)],
    links: [getCanonicalLink(input.path)],
  }
}

export function createSeoHeadFromLoader<TLoaderData>(
  buildInput: (loaderData?: TLoaderData) => SeoPageInput,
): (ctx: { loaderData?: TLoaderData }) => SeoHeadOutput {
  return (ctx) => buildSeoHead(buildInput(ctx.loaderData))
}

export function getOrganizationSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: SITE_NAME,
    url: SITE_URL,
    description: DEFAULT_DESCRIPTION,
  }
}
