<script>
    export let value, theme;
    let [labels, confidences] = [[], []];
    $: if ("confidences" in value) {
        for (const label_confidence of value["confidences"]) {
            let confidence = Math.round(label_confidence["confidence"] * 100) + "%";
            labels.push(label_confidence["label"])
            confidences.push(confidence)
        }
    }
</script>

{#if "confidences" in value}
{#each labels as label, i}
        <div class="label overflow-hidden whitespace-nowrap h-7 mb-2 overflow-ellipsis text-right" title={label}>
          {label}
        </div>
        
        <div
          class="confidence flex justify-end overflow-hidden whitespace-nowrap h-7 mb-2 px-1"
          title={confidences[i]}
          style={{
            minWidth: "calc(" + confidences[i] + " - 12px)"
          }}
        >
          {confidences[i]}
        </div>
    {/each}
    {:else}
        <div class="output_label">
            <div class="output_class_without_confidences font-bold text-2xl py-6 px-4 flex-grow flex items-center justify-center">
            {value["label"]}
            </div>
        </div>
{/if}




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