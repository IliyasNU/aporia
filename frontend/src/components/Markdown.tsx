import ReactMarkdown, { type Components } from 'react-markdown'

/**
 * Renders an article's Markdown safely (SEC-02):
 * - raw HTML in the source is dropped (`skipHtml`), so <script> or <iframe> never run;
 * - react-markdown's default URL filter removes javascript:, data: and similar links;
 * - links to user-chosen sites are marked nofollow/ugc;
 * - images are shown as links instead of being loaded, so an author cannot
 *   embed tracking pixels that reveal readers' IP addresses.
 */
const components: Components = {
  a: ({ href, children }) => (
    <a href={href} rel="nofollow ugc noopener noreferrer">
      {children}
    </a>
  ),
  img: ({ src, alt }) => (
    <a href={typeof src === 'string' ? src : undefined} rel="nofollow ugc noopener noreferrer">
      {alt ? `[image: ${alt}]` : '[image]'}
    </a>
  ),
}

export function Markdown({ source }: { source: string }) {
  return (
    <div className="prose prose-stone prose-lg max-w-none font-serif prose-headings:font-semibold prose-a:text-accent-strong">
      <ReactMarkdown skipHtml components={components}>
        {source}
      </ReactMarkdown>
    </div>
  )
}
