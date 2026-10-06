<script lang="ts">
	import { TEENS_HUB } from '$lib/audienceHub';
	import AudienceHub from '$lib/components/AudienceHub.svelte';

	let { data } = $props();
</script>

<AudienceHub hub={TEENS_HUB} shelf={data.shelf} loadError={data.loadError} />
