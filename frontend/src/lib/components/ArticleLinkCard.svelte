<script lang="ts">
	import type { ArticleLink } from '$lib/library-public';
	import { localizeHref } from '$lib/href';

	let { article, cta }: { article: ArticleLink; cta: string } = $props();
</script>

<!-- An article surfaced on a page that is NOT the articles index: the reader's
     guide on a book page, an author's articles on their own page. Both sides
     serve the same three fields, so they render through one card and cannot
     drift apart — the whole point of extracting it.

     Deliberately not ArticleCard: that one is the index's row card and owns an
     <h2>, which here would sit inside a section that already has one and break
     the heading hierarchy (page-design D1). So the title is a `text-h3` span,
     and the card rides the shared `.card-tint` hover recipe (border→accent,
     ground→surface-2, no lift) so it warms exactly like every other row card
     (page-design D3/H1). -->
<a
	href={localizeHref(`/articles/${article.slug}/`)}
	class="card-tint block rounded-card border border-border bg-surface p-4"
>
	<span class="text-h3">{article.h1}</span>
	{#if article.description}
		<span class="mt-1 block text-body text-muted">{article.description}</span>
	{/if}
	<span class="mt-2 block text-body text-accent">{cta} →</span>
</a>
