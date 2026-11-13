/**
 * One line about each curated topic (backend migration 0001), shown under the heading
 * of its tag page. A tag added later without a line here simply shows none.
 */
export const forumDescriptions: Record<string, string> = {
  ethics: 'Right and wrong, virtue, duty and how to live.',
  stoicism: 'Epictetus, Seneca, Marcus Aurelius and the practice of calm.',
  existentialism: 'Freedom, anxiety, the absurd and making a self.',
  epistemology: 'Knowledge, belief, doubt and justification.',
  metaphysics: 'Being, time, causation, identity and what there is.',
  consciousness: 'Minds, experience, the self and the hard problem.',
  logic: 'Arguments, validity, paradoxes and good reasoning.',
}

/** "1 reply", "3 replies". */
export function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`
}
