/**
 * Group a topic's books by author — but only when the topic is genuinely
 * author-clustered, so the topic page can read like the sermons shelf (a
 * `GroupHeading` per author) for the Puritans while a diverse collection like
 * Women of Faith stays a single flat grid.
 *
 * The rule: group only when MOST of the books share an author with at least one
 * other book. A gallery where nearly every book is by a different author would
 * become a wall of single-book headings, and a one-author topic has nothing to
 * group — both return `null`, and the caller falls back to the flat grid it had
 * before. Author order is first-appearance in the input; books keep their order
 * within each author.
 */

export interface GroupableBook {
	author: { slug: string; name: string; photo_url: string };
}

export interface AuthorGroup<T extends GroupableBook> {
	slug: string;
	name: string;
	photo_url: string;
	items: T[];
}

export function groupBooksByAuthor<T extends GroupableBook>(books: T[]): AuthorGroup<T>[] | null {
	const map = new Map<string, AuthorGroup<T>>();
	for (const book of books) {
		const key = book.author.slug;
		if (!map.has(key)) {
			map.set(key, { slug: key, name: book.author.name, photo_url: book.author.photo_url, items: [] });
		}
		map.get(key)!.items.push(book);
	}
	const groups = [...map.values()];
	if (groups.length < 2) return null;
	// Books that share an author with at least one other book. Grouping earns its
	// headings only when these are the majority.
	const clustered = groups
		.filter((g) => g.items.length >= 2)
		.reduce((n, g) => n + g.items.length, 0);
	return clustered > books.length / 2 ? groups : null;
}
