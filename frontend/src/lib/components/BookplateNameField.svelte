<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * A signed-in reader with no display name writes one here, on the plate's
	 * blank line. It is the profile's name (Settings → Profile holds the same),
	 * so every plate — and the greeting — takes it at once.
	 */
	const t = i18n.t;
	let value = $state('');
	let saving = $state(false);

	async function save(e: Event) {
		e.preventDefault();
		if (!value.trim() || saving) return;
		saving = true;
		try {
			await auth.setDisplayName(value);
		} finally {
			saving = false;
		}
	}
</script>

<form class="name-field" onsubmit={save}>
	<label class="text-small text-muted" for="bookplate-name">{t('bookplate.namePrompt')}</label>
	<div class="flex flex-wrap justify-center gap-2">
		<input
			id="bookplate-name"
			class="field w-auto min-w-0 flex-1"
			bind:value
			placeholder={t('settings.displayNamePlaceholder')}
			maxlength="120"
			autocomplete="name"
			dir="auto"
		/>
		<button class="btn btn-sm btn-primary" disabled={saving || !value.trim()}>{t('settings.save')}</button>
	</div>
</form>

<style>
	.name-field {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		width: 100%;
	}
</style>
