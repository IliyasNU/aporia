import { Link } from 'react-router'

import { useDocumentTitle } from '../hooks/useDocumentTitle'

export function NotFoundPage({ what = 'page' }: { what?: string }) {
  useDocumentTitle('Not found')
  return (
    <div>
      <h1 className="font-serif text-3xl font-semibold">This {what} does not exist</h1>
      <p className="mt-4 text-muted">
        It may have been unpublished or deleted.{' '}
        <Link to="/" className="font-medium text-accent-strong underline">
          Back to the essays
        </Link>
      </p>
    </div>
  )
}
