"""
This is the core file in the `gradio` package, and defines the Interface class,
including various methods for constructing an interface and then launching it.
"""

from __future__ import annotations

import copy
import os
import random
import re
import time
import warnings
import weakref
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin

from gradio import interpretation, utils
from gradio.external import load_from_pipeline, load_interface  # type: ignore
from gradio.flagging import CSVLogger, FlaggingCallback  # type: ignore
from gradio.inputs import InputComponent
from gradio.inputs import State as i_State  # type: ignore
from gradio.inputs import get_input_instance
from gradio.launchable import Launchable
from gradio.outputs import OutputComponent
from gradio.outputs import State as o_State  # type: ignore
from gradio.outputs import get_output_instance
from gradio.process_examples import load_from_cache, process_example
from gradio.routes import PredictBody

if TYPE_CHECKING:  # Only import for type checking (is False at runtime).
    import transformers


class Interface(Launchable):
    """
    Gradio interfaces are created by constructing a `Interface` object
    with a locally-defined function, or with `Interface.load()` with the path
    to a repo or by `Interface.from_pipeline()` with a Transformers Pipeline.
    """

    # stores references to all currently existing Interface instances
    instances: weakref.WeakSet = weakref.WeakSet()

    @classmethod
    def get_instances(cls) -> List[Interface]:
        """
        :return: list of all current instances.
        """
        return list(Interface.instances)

    @classmethod
    def load(
        cls,
        name: str,
        src: Optional[str] = None,
        api_key: Optional[str] = None,
        alias: Optional[str] = None,
        **kwargs,
    ) -> Interface:
        """
        Class method to construct an Interface from an external source repository, such as huggingface.
        Parameters:
        name (str): the name of the model (e.g. "gpt2"), can include the `src` as prefix (e.g. "huggingface/gpt2")
        src (str): the source of the model: `huggingface` or `gradio` (or empty if source is provided as a prefix in `name`)
        api_key (str): optional api key for use with Hugging Face Model Hub
        alias (str): optional, used as the name of the loaded model instead of the default name
        Returns:
        (gradio.Interface): a Gradio Interface object for the given model
        """
        interface_info = load_interface(name, src, api_key, alias)
        kwargs = dict(interface_info, **kwargs)
        interface = cls(**kwargs)
        interface.api_mode = True  # So interface doesn't run pre/postprocess.
        return interface

    @classmethod
    def from_pipeline(cls, pipeline: transformers.Pipeline, **kwargs) -> Interface:
        """
        Construct an Interface from a Hugging Face transformers.Pipeline.
        Parameters:
        pipeline (transformers.Pipeline):
        Returns:
        (gradio.Interface): a Gradio Interface object from the given Pipeline

        Example usage:
            import gradio as gr
            from transformers import pipeline
            pipe = pipeline(model="lysandre/tiny-vit-random")
            gr.Interface.from_pipeline(pipe).launch()
        """
        interface_info = load_from_pipeline(pipeline)
        kwargs = dict(interface_info, **kwargs)
        interface = cls(**kwargs)
        return interface

    def __init__(
        self,
        fn: Callable | List[Callable],
        inputs: str | InputComponent | List[str | InputComponent] = None,
        outputs: str | OutputComponent | List[str | OutputComponent] = None,
        verbose: bool = False,
        examples: Optional[List[Any] | List[List[Any]] | str] = None,
        examples_per_page: int = 10,
        live: bool = False,
        layout: str = "unaligned",
        show_input: bool = True,
        show_output: bool = True,
        capture_session: Optional[bool] = None,
        interpretation: Optional[Callable | str] = None,
        num_shap: float = 2.0,
        theme: Optional[str] = None,
        repeat_outputs_per_model: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        article: Optional[str] = None,
        thumbnail: Optional[str] = None,
        css: Optional[str] = None,
        height=None,
        width=None,
        allow_screenshot: bool = False,
        allow_flagging: Optional[str] = None,
        flagging_options: List[str] = None,
        encrypt=None,
        show_tips=None,
        flagging_dir: str = "flagged",
        analytics_enabled: Optional[bool] = None,
        server_name=None,
        server_port=None,
        enable_queue=None,
        api_mode=None,
        flagging_callback: FlaggingCallback = CSVLogger(),
    ):  # TODO: (faruk) Let's remove depreceated parameters in the version 3.0.0
        """
        Parameters:
        fn (Union[Callable, List[Callable]]): the function to wrap an interface around.
        inputs (Union[str, InputComponent, List[Union[str, InputComponent]]]): a single Gradio input component, or list of Gradio input components. Components can either be passed as instantiated objects, or referred to by their string shortcuts. The number of input components should match the number of parameters in fn.
        outputs (Union[str, OutputComponent, List[Union[str, OutputComponent]]]): a single Gradio output component, or list of Gradio output components. Components can either be passed as instantiated objects, or referred to by their string shortcuts. The number of output components should match the number of values returned by fn.
        verbose (bool): DEPRECATED. Whether to print detailed information during launch.
        examples (Union[List[List[Any]], str]): sample inputs for the function; if provided, appears below the UI components and can be used to populate the interface. Should be nested list, in which the outer list consists of samples and each inner list consists of an input corresponding to each input component. A string path to a directory of examples can also be provided. If there are multiple input components and a directory is provided, a log.csv file must be present in the directory to link corresponding inputs.
        examples_per_page (int): If examples are provided, how many to display per page.
        live (bool): whether the interface should automatically reload on change.
        layout (str): Layout of input and output panels. "horizontal" arranges them as two columns of equal height, "unaligned" arranges them as two columns of unequal height, and "vertical" arranges them vertically.
        capture_session (bool): DEPRECATED. If True, captures the default graph and session (needed for Tensorflow 1.x)
        interpretation (Union[Callable, str]): function that provides interpretation explaining prediction output. Pass "default" to use simple built-in interpreter, "shap" to use a built-in shapley-based interpreter, or your own custom interpretation function.
        num_shap (float): a multiplier that determines how many examples are computed for shap-based interpretation. Increasing this value will increase shap runtime, but improve results. Only applies if interpretation is "shap".
        title (str): a title for the interface; if provided, appears above the input and output components.
        description (str): a description for the interface; if provided, appears above the input and output components.
        article (str): an expanded article explaining the interface; if provided, appears below the input and output components. Accepts Markdown and HTML content.
        thumbnail (str): path to image or src to use as display picture for models listed in gradio.app/hub
        theme (str): Theme to use - one of "default", "huggingface", "seafoam", "grass", "peach". Add "dark-" prefix, e.g. "dark-peach" for dark theme (or just "dark" for the default dark theme).
        css (str): custom css or path to custom css file to use with interface.
        allow_screenshot (bool): DEPRECATED if False, users will not see a button to take a screenshot of the interface.
        allow_flagging (str): one of "never", "auto", or "manual". If "never" or "auto", users will not see a button to flag an input and output. If "manual", users will see a button to flag. If "auto", every prediction will be automatically flagged. If "manual", samples are flagged when the user clicks flag button. Can be set with environmental variable GRADIO_ALLOW_FLAGGING.
        flagging_options (List[str]): if provided, allows user to select from the list of options when flagging. Only applies if allow_flagging is "manual".
        encrypt (bool): DEPRECATED. If True, flagged data will be encrypted by key provided by creator at launch
        flagging_dir (str): what to name the dir where flagged data is stored.
        show_tips (bool): DEPRECATED. if True, will occasionally show tips about new Gradio features
        enable_queue (bool): DEPRECATED. if True, inference requests will be served through a queue instead of with parallel threads. Required for longer inference times (> 1min) to prevent timeout.
        api_mode (bool): DEPRECATED. If True, will skip preprocessing steps when the Interface is called() as a function (should remain False unless the Interface is loaded from an external repo)
        server_name (str): DEPRECATED. Name of the server to use for serving the interface - pass in launch() instead.
        server_port (int): DEPRECATED. Port of the server to use for serving the interface - pass in launch() instead.
        """
        if not isinstance(fn, list):
            fn = [fn]
        if not isinstance(inputs, list):
            inputs = [inputs]
        if not isinstance(outputs, list):
            outputs = [outputs]

        self.input_components = [get_input_instance(i) for i in inputs]
        self.output_components = [get_output_instance(o) for o in outputs]
        if repeat_outputs_per_model:
            self.output_components *= len(fn)

        self.stateful = False
        if sum(isinstance(i, i_State) for i in self.input_components) > 1:
            raise ValueError("Only one input component can be State.")
        if sum(isinstance(o, o_State) for o in self.output_components) > 1:
            raise ValueError("Only one output component can be State.")

        if sum(isinstance(i, i_State) for i in self.input_components) == 1:
            if len(fn) > 1:
                raise ValueError("State cannot be used with multiple functions.")
            state_param_index = [
                isinstance(i, i_State) for i in self.input_components
            ].index(True)
            self.stateful = True
            self.state_param_index = state_param_index
            state: i_State = self.input_components[state_param_index]
            if state.default is None:
                default = utils.get_default_args(fn[0])[state_param_index]
                state.default = default
            self.state_default = state.default

            if sum(isinstance(i, o_State) for i in self.output_components) == 1:
                state_return_index = [
                    isinstance(i, o_State) for i in self.output_components
                ].index(True)
                self.state_return_index = state_return_index
            else:
                raise ValueError(
                    "For a stateful interface, there must be exactly one State"
                    " input component and one State output component."
                )

        if (
            interpretation is None
            or isinstance(interpretation, list)
            or callable(interpretation)
        ):
            self.interpretation = interpretation
        elif isinstance(interpretation, str):
            self.interpretation = [
                interpretation.lower() for _ in self.input_components
            ]
        else:
            raise ValueError("Invalid value for parameter: interpretation")

        self.predict = fn
        self.predict_durations = [[0, 0]] * len(fn)
        self.function_names = [func.__name__ for func in fn]
        self.__name__ = ", ".join(self.function_names)

        if verbose:
            warnings.warn(
                "The `verbose` parameter in the `Interface`"
                "is deprecated and has no effect."
            )
        if allow_screenshot:
            warnings.warn(
                "The `allow_screenshot` parameter in the `Interface`"
                "is deprecated and has no effect."
            )

        self.status = "OFF"
        self.live = live
        self.layout = layout
        self.show_input = show_input
        self.show_output = show_output
        self.flag_hash = random.getrandbits(32)
        self.capture_session = capture_session

        if capture_session is not None:
            warnings.warn(
                "The `capture_session` parameter in the `Interface`"
                " is deprecated and may be removed in the future."
            )
            try:
                import tensorflow as tf

                self.session = tf.get_default_graph(), tf.keras.backend.get_session()
            except (ImportError, AttributeError):
                # If they are using TF >= 2.0 or don't have TF,
                # just ignore this parameter.
                pass

        if server_name is not None or server_port is not None:
            raise DeprecationWarning(
                "The `server_name` and `server_port` parameters in `Interface`"
                "are deprecated. Please pass into launch() instead."
            )

        self.session = None
        self.title = title

        CLEANER = re.compile("<.*?>")

        def clean_html(raw_html):
            cleantext = re.sub(CLEANER, "", raw_html)
            return cleantext

        md = MarkdownIt(
            "js-default",
            {
                "linkify": True,
                "typographer": True,
                "html": True,
            },
        ).use(footnote_plugin)

        simple_description = None
        if description is not None:
            description = md.render(description)
            simple_description = clean_html(description)
        self.simple_description = simple_description
        self.description = description
        if article is not None:
            article = utils.readme_to_html(article)
            article = md.render(article)
        self.article = article

        self.thumbnail = thumbnail
        theme = theme if theme is not None else os.getenv("GRADIO_THEME", "default")
        DEPRECATED_THEME_MAP = {
            "darkdefault": "default",
            "darkhuggingface": "dark-huggingface",
            "darkpeach": "dark-peach",
            "darkgrass": "dark-grass",
        }
        VALID_THEME_SET = (
            "default",
            "huggingface",
            "seafoam",
            "grass",
            "peach",
            "dark",
            "dark-huggingface",
            "dark-seafoam",
            "dark-grass",
            "dark-peach",
        )
        if theme in DEPRECATED_THEME_MAP:
            warnings.warn(
                f"'{theme}' theme name is deprecated, using {DEPRECATED_THEME_MAP[theme]} instead."
            )
            theme = DEPRECATED_THEME_MAP[theme]
        elif theme not in VALID_THEME_SET:
            raise ValueError(
                f"Invalid theme name, theme must be one of: {', '.join(VALID_THEME_SET)}"
            )
        self.theme = theme

        self.height = height
        self.width = width
        if self.height is not None or self.width is not None:
            warnings.warn(
                "The `height` and `width` parameters in `Interface` "
                "are deprecated and should be passed into launch()."
            )

        if css is not None and os.path.exists(css):
            with open(css) as css_file:
                self.css = css_file.read()
        else:
            self.css = css
        if (
            examples is None
            or isinstance(examples, str)
            or (
                isinstance(examples, list)
                and (len(examples) == 0 or isinstance(examples[0], list))
            )
        ):
            self.examples = examples
        elif (
            isinstance(examples, list) and len(self.input_components) == 1
        ):  # If there is only one input component, examples can be provided as a regular list instead of a list of lists
            self.examples = [[e] for e in examples]
        else:
            raise ValueError(
                "Examples argument must either be a directory or a nested "
                "list, where each sublist represents a set of inputs."
            )
        self.num_shap = num_shap
        self.examples_per_page = examples_per_page

        self.simple_server = None
        self.allow_screenshot = allow_screenshot

        # For analytics_enabled and allow_flagging: (1) first check for
        # parameter, (2) check for env variable, (3) default to True/"manual"
        self.analytics_enabled = (
            analytics_enabled
            if analytics_enabled is not None
            else os.getenv("GRADIO_ANALYTICS_ENABLED", "True") == "True"
        )
        if allow_flagging is None:
            allow_flagging = os.getenv("GRADIO_ALLOW_FLAGGING", "manual")
        if allow_flagging is True:
            warnings.warn(
                "The `allow_flagging` parameter in `Interface` now"
                "takes a string value ('auto', 'manual', or 'never')"
                ", not a boolean. Setting parameter to: 'manual'."
            )
            self.allow_flagging = "manual"
        elif allow_flagging == "manual":
            self.allow_flagging = "manual"
        elif allow_flagging is False:
            warnings.warn(
                "The `allow_flagging` parameter in `Interface` now"
                "takes a string value ('auto', 'manual', or 'never')"
                ", not a boolean. Setting parameter to: 'never'."
            )
            self.allow_flagging = "never"
        elif allow_flagging == "never":
            self.allow_flagging = "never"
        elif allow_flagging == "auto":
            self.allow_flagging = "auto"
        else:
            raise ValueError(
                "Invalid value for `allow_flagging` parameter."
                "Must be: 'auto', 'manual', or 'never'."
            )

        self.flagging_options = flagging_options
        self.flagging_callback = flagging_callback
        self.flagging_dir = flagging_dir

        self.save_to = None  # Used for selenium tests
        self.share = None
        self.share_url = None
        self.local_url = None
        self.ip_address = utils.get_local_ip_address()

        if show_tips is not None:
            warnings.warn(
                "The `show_tips` parameter in the `Interface` is deprecated. Please use the `show_tips` parameter in `launch()` instead"
            )

        self.requires_permissions = any(
            [component.requires_permissions for component in self.input_components]
        )

        self.enable_queue = enable_queue
        if self.enable_queue is not None:
            warnings.warn(
                "The `enable_queue` parameter in the `Interface`"
                "will be deprecated and may not work properly. "
                "Please use the `enable_queue` parameter in "
                "`launch()` instead"
            )

        self.favicon_path = None
        self.height = height
        self.width = width
        if self.height is not None or self.width is not None:
            warnings.warn(
                "The `width` and `height` parameters in the `Interface` class"
                "will be deprecated. Please provide these parameters"
                "in `launch()` instead"
            )

        self.encrypt = encrypt
        if self.encrypt is not None:
            warnings.warn(
                "The `encrypt` parameter in the `Interface` class"
                "will be deprecated. Please provide this parameter"
                "in `launch()` instead"
            )

        if api_mode is not None:
            warnings.warn("The `api_mode` parameter in the `Interface` is deprecated.")
        self.api_mode = False

        data = {
            "fn": fn,
            "inputs": inputs,
            "outputs": outputs,
            "live": live,
            "capture_session": capture_session,
            "ip_address": self.ip_address,
            "interpretation": interpretation,
            "allow_flagging": allow_flagging,
            "allow_screenshot": allow_screenshot,
            "custom_css": self.css is not None,
            "theme": self.theme,
        }

        if self.analytics_enabled:
            utils.initiated_analytics(data)

        # Alert user if a more recent version of the library exists
        utils.version_check()
        Interface.instances.add(self)

    def __call__(self, *params):
        if (
            self.api_mode
        ):  # skip the preprocessing/postprocessing if sending to a remote API
            output = self.run_prediction(params, called_directly=True)
        else:
            output, _ = self.process(params)
        return output[0] if len(output) == 1 else output

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        repr = "Gradio Interface for: {}".format(
            ", ".join(fn.__name__ for fn in self.predict)
        )
        repr += "\n" + "-" * len(repr)
        repr += "\ninputs:"
        for component in self.input_components:
            repr += "\n|-{}".format(str(component))
        repr += "\noutputs:"
        for component in self.output_components:
            repr += "\n|-{}".format(str(component))
        return repr

    def get_config_file(self):
        return utils.get_config_file(self)

    def run_prediction(
        self,
        processed_input: List[Any],
        return_duration: bool = False,
        called_directly: bool = False,
    ) -> List[Any] | Tuple[List[Any], List[float]]:
        """
        Runs the prediction function with the given (already processed) inputs.
        Parameters:
        processed_input (list): A list of processed inputs.
        return_duration (bool): Whether to return the duration of the prediction.
        called_directly (bool): Whether the prediction is being called
            directly (i.e. as a function, not through the GUI).
        Returns:
        predictions (list): A list of predictions (not post-processed).
        durations (list): A list of durations for each prediction
            (only returned if `return_duration` is True).
        """
        if self.api_mode:  # Serialize the input
            processed_input = [
                input_component.serialize(processed_input[i], called_directly)
                for i, input_component in enumerate(self.input_components)
            ]
        predictions = []
        durations = []
        output_component_counter = 0

        for predict_fn in self.predict:
            start = time.time()
            if self.capture_session and self.session is not None:  # For TF 1.x
                graph, sess = self.session
                with graph.as_default(), sess.as_default():
                    prediction = predict_fn(*processed_input)
            else:
                prediction = predict_fn(*processed_input)
            duration = time.time() - start

            if len(self.output_components) == len(self.predict):
                prediction = [prediction]

            if self.api_mode:  # Serialize the input
                prediction_ = copy.deepcopy(prediction)
                prediction = []
                for (
                    pred
                ) in (
                    prediction_
                ):  # Done this way to handle both single interfaces with multiple outputs and Parallel() interfaces
                    prediction.append(
                        self.output_components[output_component_counter].deserialize(
                            pred
                        )
                    )
                    output_component_counter += 1

            durations.append(duration)
            predictions.extend(prediction)

        if return_duration:
            return predictions, durations
        else:
            return predictions

    def process_api(self, data: PredictBody, username: str = None) -> Dict[str, Any]:
        flag_index = None
        if data.example_id is not None:
            if self.cache_examples:
                prediction = load_from_cache(self, data.example_id)
                durations = None
            else:
                prediction, durations = process_example(self, data.example_id)
        else:
            raw_input = data.data
            if self.stateful:
                state = data.state
                raw_input[self.state_param_index] = state
            prediction, durations = self.process(raw_input)
            if self.allow_flagging == "auto":
                flag_index = self.flagging_callback.flag(
                    self,
                    raw_input,
                    prediction,
                    flag_option="" if self.flagging_options else None,
                    username=username,
                )
        if self.stateful:
            updated_state = prediction[self.state_return_index]
            prediction[self.state_return_index] = None
        else:
            updated_state = None

        durations = durations
        avg_durations = self.config.get("avg_durations")
        response = {
            "data": prediction,
            "flag_index": flag_index,
            "updated_state": updated_state,
        }
        if durations is not None:
            response["durations"] = durations
        if avg_durations is not None:
            response["avg_durations"] = avg_durations
        return response

    def process(self, raw_input: List[Any]) -> Tuple[List[Any], List[float]]:
        """
        First preprocesses the input, then runs prediction using
        self.run_prediction(), then postprocesses the output.
        Parameters:
        raw_input: a list of raw inputs to process and apply the prediction(s) on.
        Returns:
        processed output: a list of processed  outputs to return as the prediction(s).
        duration: a list of time deltas measuring inference time for each prediction fn.
        """
        processed_input = [
            input_component.preprocess(raw_input[i])
            for i, input_component in enumerate(self.input_components)
        ]
        predictions, durations = self.run_prediction(
            processed_input, return_duration=True
        )
        processed_output = [
            output_component.postprocess(predictions[i])
            if predictions[i] is not None
            else None
            for i, output_component in enumerate(self.output_components)
        ]

        avg_durations = []
        for i, duration in enumerate(durations):
            self.predict_durations[i][0] += duration
            self.predict_durations[i][1] += 1
            avg_durations.append(
                self.predict_durations[i][0] / self.predict_durations[i][1]
            )
        if hasattr(self, "config"):
            self.config["avg_durations"] = avg_durations

        return processed_output, durations

    def interpret(self, raw_input: List[Any]) -> List[Any]:
        return interpretation.run_interpret(self, raw_input)

    def test_launch(self) -> None:
        for predict_fn in self.predict:
            print("Test launch: {}()...".format(predict_fn.__name__), end=" ")
            raw_input = []
            for input_component in self.input_components:
                if input_component.test_input is None:
                    print("SKIPPED")
                    break
                else:
                    raw_input.append(input_component.test_input)
            else:
                self.process(raw_input)
                print("PASSED")
                continue

    def launch(self, **args):
        if self.allow_flagging != "never":
            self.flagging_callback.setup(self.flagging_dir)
        return super().launch(**args)

    def integrate(self, comet_ml=None, wandb=None, mlflow=None) -> None:
        """
        A catch-all method for integrating with other libraries.
        Should be run after launch()
        Parameters:
            comet_ml (Experiment): If a comet_ml Experiment object is provided,
            will integrate with the experiment and appear on Comet dashboard
            wandb (module): If the wandb module is provided, will integrate
            with it and appear on WandB dashboard
            mlflow (module): If the mlflow module  is provided, will integrate
            with the experiment and appear on ML Flow dashboard
        """
        analytics_integration = ""
        if comet_ml is not None:
            analytics_integration = "CometML"
            comet_ml.log_other("Created from", "Gradio")
            if self.share_url is not None:
                comet_ml.log_text("gradio: " + self.share_url)
                comet_ml.end()
            else:
                comet_ml.log_text("gradio: " + self.local_url)
                comet_ml.end()
        if wandb is not None:
            analytics_integration = "WandB"
            if self.share_url is not None:
                wandb.log(
                    {
                        "Gradio panel": wandb.Html(
                            '<iframe src="'
                            + self.share_url
                            + '" width="'
                            + str(self.width)
                            + '" height="'
                            + str(self.height)
                            + '" frameBorder="0"></iframe>'
                        )
                    }
                )
            else:
                print(
                    "The WandB integration requires you to "
                    "`launch(share=True)` first."
                )
        if mlflow is not None:
            analytics_integration = "MLFlow"
            if self.share_url is not None:
                mlflow.log_param("Gradio Interface Share Link", self.share_url)
            else:
                mlflow.log_param("Gradio Interface Local Link", self.local_url)
        if self.analytics_enabled and analytics_integration:
            data = {"integration": analytics_integration}
            utils.integration_analytics(data)


def close_all(verbose: bool = True) -> None:
    for io in Interface.get_instances():
        io.close(verbose)


def reset_all() -> None:
    warnings.warn(
        "The `reset_all()` method has been renamed to `close_all()` "
        "and will be deprecated. Please use `close_all()` instead."
    )
    close_all()
