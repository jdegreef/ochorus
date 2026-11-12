<script lang="ts">
	import type { CoverStyleId } from '$lib/coverStyles';
	import { plateWords } from '$lib/bookplate';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * "Save as image": the plate drawn as a PNG (`bookplateCard.ts`) and handed
	 * to the share sheet — in the app, through `$lib/platform` — or downloaded
	 * on the website, by the same path the quote card takes. The renderer is
	 * imported on the first tap: it has no place in the finish panel's bundle.
	 */
	let {
		slug,
		name,
		title,
		author,
		date,
		style,
		small = false
	}: {
		slug: string;
		name: string;
		title: string;
		author: string;
		date: string;
		style: CoverStyleId;
		small?: boolean;
	} = $props();
	const t = i18n.t;

	let busy = $state(false);
	let saved = $state(false);

	async function save() {
		if (busy) return;
		busy = true;
		try {
			const { saveBookplate } = await import('$lib/bookplateCard');
			const result = await saveBookplate({
				slug,
				name,
				title,
				...plateWords(t, author),
				date,
				style,
				locale: getLang()
			});
			saved = result === 'shared' || result === 'downloaded';
		} catch {
			// Drawing or sharing failed: the plate is still on the page.
		} finally {
			busy = false;
		}
	}
</script>

<button type="button" class="btn {small ? 'btn-sm btn-ghost' : 'btn-sm'}" onclick={save} disabled={busy} aria-busy={busy} aria-live="polite">
	{saved ? t('bookplate.saved') : t('bookplate.save')}
</button>
