import { mkdir, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const rootDir = path.resolve(__dirname, '..')
const routesDir = path.join(rootDir, 'src', 'routes')
const publicDir = path.join(rootDir, 'public')
const sitemapPath = path.join(publicDir, 'sitemap.xml')

const siteUrl = (process.env.VITE_SITE_URL || 'https://example.com').replace(
  /\/$/,
  '',
)

async function getRouteFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  const files = await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        return getRouteFiles(entryPath)
      }
      return entry.name.endsWith('.tsx') ? [entryPath] : []
    }),
  )

  return files.flat()
}

function toRoutePath(filePath) {
  const relativePath = path.relative(routesDir, filePath)
  const noExt = relativePath.replace(/\.tsx$/, '')

  if (noExt === '__root') {
    return null
  }

  const rawSegments = noExt.split(path.sep)
  if (rawSegments.some((segment) => segment.startsWith('_'))) {
    return null
  }
  if (rawSegments.some((segment) => segment.startsWith('$'))) {
    return null
  }

  const segments = rawSegments.filter((segment) => segment !== 'index')
  if (segments.length === 0) {
    return '/'
  }

  return `/${segments.join('/')}`
}

function buildSitemapXml(routes) {
  const lastModified = new Date().toISOString().split('T')[0]

  const urls = routes
    .map((route) => {
      const priority = route === '/' ? '1.0' : '0.7'
      return [
        '  <url>',
        `    <loc>${siteUrl}${route}</loc>`,
        `    <lastmod>${lastModified}</lastmod>`,
        '    <changefreq>weekly</changefreq>',
        `    <priority>${priority}</priority>`,
        '  </url>',
      ].join('\n')
    })
    .join('\n')

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    urls,
    '</urlset>',
  ].join('\n')
}

async function main() {
  const routeFiles = await getRouteFiles(routesDir)
  const routes = Array.from(
    new Set(routeFiles.map(toRoutePath).filter(Boolean)),
  ).sort()

  await mkdir(publicDir, { recursive: true })
  await writeFile(sitemapPath, `${buildSitemapXml(routes)}\n`, 'utf8')

  console.log(
    `Generated sitemap with ${routes.length} route(s): ${sitemapPath}`,
  )
}

main().catch((error) => {
  console.error('Failed to generate sitemap:', error)
  process.exit(1)
})
