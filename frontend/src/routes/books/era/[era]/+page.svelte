<script lang="ts">
	import BookHubPage from '$lib/components/BookHubPage.svelte';
	import { bookEraPath } from '$lib/bookHubs';
	import { eraById } from '$lib/eras';
	import { i18n } from '$lib/i18n.svelte';

	let { data } = $props();
	const t = i18n.t;
</script>

<BookHubPage
	label={t(data.era.k)}
	path={bookEraPath(data.era.id)}
	books={data.books}
	biosHref={`/biographies/era/${data.era.id}/`}
	others={data.others.map((id) => ({ href: bookEraPath(id), label: t(eraById(id)!.k) }))}
	othersHeading={t('books.hubOtherEras')}
/>
