import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Markdown } from './Markdown'

describe('Markdown', () => {
  it('renders Markdown formatting', () => {
    const { container } = render(<Markdown source={'# Title\n\nSome *emphasis*.'} />)

    expect(container.querySelector('h1')).toHaveTextContent('Title')
    expect(container.querySelector('em')).toHaveTextContent('emphasis')
  })

  it('drops raw HTML instead of rendering or running it', () => {
    const { container } = render(
      <Markdown source={'Hi <script>window.hacked = true</script><b onclick="x()">bold</b>'} />,
    )

    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('b')).toBeNull()
    expect(container.innerHTML).not.toContain('onclick')
  })

  it('removes javascript: links and marks other links as user content', () => {
    const { container } = render(
      <Markdown source={'[bad](javascript:alert(1)) and [good](https://example.com)'} />,
    )
    const links = Array.from(container.querySelectorAll('a'))

    expect(links.map((a) => a.getAttribute('href'))).toEqual(['', 'https://example.com'])
    expect(links[1]).toHaveAttribute('rel', 'nofollow ugc noopener noreferrer')
  })

  it('shows images as links instead of loading them', () => {
    const { container } = render(<Markdown source={'![a pixel](https://tracker.example/p.gif)'} />)

    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('a')).toHaveTextContent('[image: a pixel]')
  })
})
