<script lang="ts">
	import BookHubPage from '$lib/components/BookHubPage.svelte';
	import { bookTraditionPath } from '$lib/bookHubs';
	import { hubPath } from '$lib/hubs';
	import { i18n } from '$lib/i18n.svelte';

	let { data } = $props();
</script>

<BookHubPage
	label={data.hub.label}
	path={bookTraditionPath(data.hub.slug)}
	lede={data.hub.intro}
	books={data.books}
	biosHref={hubPath(data.hub)}
	others={data.others.map((h) => ({ href: bookTraditionPath(h.slug), label: h.label }))}
	othersHeading={i18n.t('books.hubOtherTraditions')}
/>
