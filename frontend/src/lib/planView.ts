import { localizeHref } from './href';

/**
 * A plan page opened in its calendar view — where the Google / .ics reminder
 * events are made — for that visit only (`?view=calendar`, read by the plan
 * page on mount): the reader's own list/calendar preference is left alone.
 */
export const planCalendarHref = (slug: string): string => localizeHref(`/plans/${slug}/?view=calendar`);
