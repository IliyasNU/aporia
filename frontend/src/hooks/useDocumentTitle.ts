import { useEffect } from 'react'

const SITE = 'Aporia'
const DEFAULT_DESCRIPTION = 'Aporia: a home for philosophical essays.'

/** Sets the tab title and meta description (and Open Graph tags) for the current page. */
export function useDocumentTitle(title: string | null, description?: string) {
  useEffect(() => {
    document.title = title ? `${title} · ${SITE}` : SITE
    const text = description || DEFAULT_DESCRIPTION
    setMeta('name', 'description', text)
    setMeta('property', 'og:title', title ?? SITE)
    setMeta('property', 'og:description', text)
  }, [title, description])
}

function setMeta(attribute: 'name' | 'property', key: string, content: string) {
  let tag = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`)
  if (!tag) {
    tag = document.createElement('meta')
    tag.setAttribute(attribute, key)
    document.head.appendChild(tag)
  }
  tag.content = content
}
