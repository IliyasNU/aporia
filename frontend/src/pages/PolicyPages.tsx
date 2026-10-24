import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { useDocumentTitle } from '../hooks/useDocumentTitle'

function Policy({ title, children }: { title: string; children: ReactNode }) {
  useDocumentTitle(title)
  return (
    <article className="prose prose-stone max-w-none">
      <h1 className="font-serif">{title}</h1>
      {children}
    </article>
  )
}

/** SEC-06: what Aporia stores, why, and for how long. */
export function PrivacyPage() {
  return (
    <Policy title="Privacy">
      <p>
        Aporia keeps as little personal data as it can and uses it only to run the site. It has no
        advertising, no analytics, no third-party trackers and no tracking cookies.
      </p>
      <h2>What we store</h2>
      <ul>
        <li>
          <strong>Your account:</strong> email address, handle, display name, bio, website and a
          one-way hash of your password (never the password itself).
        </li>
        <li>
          <strong>What you choose to do:</strong> essays, comments, the authors you follow, saved
          essays, reports and your topic interests. Interests are visible only to you.
        </li>
        <li>
          <strong>A session cookie</strong> that keeps you signed in. It is strictly necessary,
          cannot be read by scripts and expires after 14 days or when you sign out.
        </li>
        <li>
          <strong>Email subscriptions:</strong> the address and the author you subscribed to. You do
          not need an account for this.
        </li>
      </ul>
      <h2>What we do not do</h2>
      <ul>
        <li>We do not record which essays you open, how long you read or what you click.</li>
        <li>
          Recommendations use only your interests, the authors you follow, how often essays are
          saved and when they were published.
        </li>
        <li>We do not sell or share data with anyone.</li>
        <li>Email addresses of subscribers are never shown publicly.</li>
      </ul>
      <h2>Email</h2>
      <p>
        We send nothing but a confirmation link until you confirm a subscription. Every email has an
        unsubscribe link that works without signing in. Addresses that are never confirmed are
        deleted about a week after the link expires; records of sent emails are deleted after 90
        days.
      </p>
      <h2>Logs</h2>
      <p>
        Servers keep short technical logs to keep the site running. They never contain passwords,
        session tokens or subscription links, and they are rotated automatically.
      </p>
      <h2>Your choices</h2>
      <p>
        You can edit your profile and interests, unfollow authors, remove saved essays, delete your
        essays and comments, and unsubscribe from emails at any time. To delete your account or have
        an email address removed from all subscriptions, contact the operator of this Aporia site.
      </p>
      <p>
        See also the <Link to="/rules">publication rules</Link>.
      </p>
    </Policy>
  )
}

/** SEC-06/SEC-07: what may be published and how moderation works. */
export function RulesPage() {
  return (
    <Policy title="Publication rules">
      <p>
        Aporia is a place for careful thinking. Disagreement is welcome; contempt is not. These
        rules apply to essays, comments and profiles.
      </p>
      <h2>Please do</h2>
      <ul>
        <li>Publish your own work, and credit and link the ideas and quotes you use.</li>
        <li>Argue with positions, not with people.</li>
        <li>Mark clearly when a text is fiction, satire or a thought experiment.</li>
      </ul>
      <h2>Not allowed</h2>
      <ul>
        <li>Harassment, threats, hate against people or groups, or calls for violence.</li>
        <li>Personal data about others without their consent (addresses, phone numbers, …).</li>
        <li>Copyright infringement and plagiarism.</li>
        <li>Spam, advertising and deliberately misleading content.</li>
        <li>Anything illegal.</li>
      </ul>
      <h2>Moderation</h2>
      <p>
        Anyone signed in can report an essay or a comment with the <em>Report</em> link.
        Administrators review reports and may hide content that breaks these rules; hidden content
        disappears from every public page, and its author is told on the essay itself. Illegal
        content is removed permanently.
      </p>
      <p>
        See also how we handle your data in the <Link to="/privacy">privacy notice</Link>.
      </p>
    </Policy>
  )
}
