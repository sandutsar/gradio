import InputNumber from "./input/Number.svelte";
import InputRadio from "./input/Radio.svelte";
import InputTextbox from "./input/Textbox.svelte"
import InputSlider from "./input/Slider.svelte"
import InputCheckbox from "./input/Checkbox.svelte"
import InputCheckboxGroup from "./input/CheckboxGroup.svelte"
import InputAudio from "./input/Audio.svelte";
import InputFile from "./input/File.svelte";
import InputImage from "./input/Image.svelte";
import InputVideo from "./input/Video.svelte";
import InputDropdown from "./input/Dropdown.svelte";

import OutputTextbox from "./output/Textbox.svelte";
import OutputCarousel from "./output/Carousel.svelte";
import OutputImage from "./output/Image.svelte";
import OutputVideo from "./output/Video.svelte";
import OutputAudio from "./output/Audio.svelte";
import OutputFile from "./output/File.svelte";
import OutputJson from "./output/Json.svelte";
import OutputHtml from "./output/Html.svelte";
import OutputDataframe from "./output/Dataframe.svelte";
import OutputLabel from "./output/Label.svelte";
import OutputHighlightedText from "./output/HighlightedText.svelte";

import Dummy from "./Dummy.svelte"

export const inputComponentMap = {
    "audio": InputAudio,
    "dataframe": Dummy,
    "dropdown": InputDropdown,
    "file": InputFile,
    "image": InputImage,
    "number": InputNumber,
    "radio": InputRadio,
    "textbox": InputTextbox,
    "slider": InputSlider,
    "checkbox": InputCheckbox,
    "checkboxgroup": InputCheckboxGroup,
    "timeseries": Dummy,
    "video": InputVideo,
}

export const outputComponentMap = {
    "audio": OutputAudio,
    "carousel": OutputCarousel,
    "dataframe": OutputDataframe,
    "file": OutputFile,
    "html": OutputHtml,
    "image": OutputImage,
    "json": OutputJson,
    "textbox": OutputTextbox,
    "highlightedText": OutputHighlightedText,
    "label": OutputLabel,
    "timeseries": Dummy,
    "video": OutputVideo,
}
