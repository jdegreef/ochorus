<script lang="ts">
	import HubPage from '$lib/components/HubPage.svelte';

	let { data } = $props();
</script>

<HubPage {...data} />
