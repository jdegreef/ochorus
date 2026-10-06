<script lang="ts">
	import { YOUNG_READERS_HUB } from '$lib/audienceHub';
	import AudienceHub from '$lib/components/AudienceHub.svelte';

	let { data } = $props();
</script>

<AudienceHub hub={YOUNG_READERS_HUB} shelf={data.shelf} loadError={data.loadError} />
