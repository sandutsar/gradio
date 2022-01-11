<script>
  export let value, theme;
  let [labels, confidences] = [[], []];
  if ("confidences" in value) {
    for (const label_confidence of value["confidences"]) {
      let confidence = Math.round(label_confidence["confidence"] * 100) + "%";
      labels.push(label_confidence["label"]);
      confidences.push(confidence);
    }
  }
</script>

<div class="output-label" {theme}>
  {#if "confidences" in value}
    <div
      class="output-class font-bold text-2xl py-6 px-4 flex-grow flex items-center justify-center"
    >
      {value["label"]}
    </div>
    <div class="confidence_intervals flex text-xl">
      <div class="labels mr-2" style="max-width: 120px">
        {#each labels as label}
          <div
            class="label overflow-hidden whitespace-nowrap h-7 mb-2 overflow-ellipsis text-right"
            title={label}
          >
            {label}
          </div>
        {/each}
      </div>
      <div class="confidences flex flex-grow flex-col items-baseline">
        {#each confidences as confidence}
          <div
            class="confidence flex justify-end overflow-hidden whitespace-nowrap h-7 mb-2 px-1"
            title={confidence}
            style={"min-width: calc(" + confidence + " - 12px)"}
          >
            {confidence}
          </div>
        {/each}
      </div>
    </div>
  {:else}
    <div
      class="output-class-without-confidences font-bold text-2xl py-6 px-4 flex-grow flex items-center justify-center"
    >
      {value["label"]}
    </div>
  {/if}
</div>

<style lang="postcss">
  .output-label[theme="default"] {
    .label {
      @apply text-sm h-5;
    }
    .confidence {
      @apply font-mono box-border border-b-2 border-gray-300 bg-gray-200 dark:bg-gray-500 dark:border-gray-600 text-sm h-5 font-semibold rounded;
    }
    .confidence:first-child {
      @apply border-yellow-600 bg-yellow-500 dark:bg-red-600 border-red-700 text-white;
    }
  }
</style>
