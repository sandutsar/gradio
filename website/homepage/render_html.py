import html
import inspect
import json
import os
import re

import markdown2
import requests
from jinja2 import Template
from render_html_helpers import generate_meta_image

from gradio.inputs import InputComponent
from gradio.interface import Interface
from gradio.outputs import OutputComponent

GRADIO_DIR = "../../"
GRADIO_GUIDES_DIR = os.path.join(GRADIO_DIR, "guides")
GRADIO_DEMO_DIR = os.path.join(GRADIO_DIR, "demo")
GRADIO_ASSETS_LIST = os.listdir(
    os.path.join(GRADIO_DIR, "gradio", "templates", "frontend", "assets")
)
GRADIO_ASSETS = {
    f"{asset.split('.')[0]}_{asset.split('.')[-1]}_file": asset
    for asset in GRADIO_ASSETS_LIST
}

with open("src/navbar.html", encoding="utf-8") as navbar_file:
    navbar_html = navbar_file.read()


def render_index():
    os.makedirs("generated", exist_ok=True)
    with open("src/tweets.json", encoding="utf-8") as tweets_file:
        tweets = json.load(tweets_file)
    star_request = requests.get("https://api.github.com/repos/gradio-app/gradio").json()
    star_count = (
        "{:,}".format(star_request["stargazers_count"])
        if "stargazers_count" in star_request
        else ""
    )
    with open("src/index_template.html", encoding="utf-8") as template_file:
        template = Template(template_file.read())
        output_html = template.render(
            tweets=tweets,
            star_count=star_count,
            navbar_html=navbar_html,
            **GRADIO_ASSETS,
        )
    with open(
        os.path.join("generated", "index.html"), "w", encoding="utf-8"
    ) as generated_template:
        generated_template.write(output_html)


guide_files = ["getting_started.md"]
all_guides = sorted(os.listdir(GRADIO_GUIDES_DIR))
guide_files.extend([file for file in all_guides if file != "getting_started.md"])
guides = []
for guide in guide_files:
    if guide.lower() == "readme.md":
        continue
    guide_name = guide[:-3]
    pretty_guide_name = " ".join(
        [
            word.capitalize().replace("Ml", "ML").replace("Gan", "GAN").replace("Api", "API")
            for word in guide_name.split("_")
        ]
    )
    with open(os.path.join(GRADIO_GUIDES_DIR, guide), "r") as f:
        guide_content = f.read()

    tags = None
    if "tags: " in guide_content:
        tags = guide_content.split("tags: ")[1].split("\n")[0].split(", ")

    spaces = None
    if "related_spaces: " in guide_content:
        spaces = guide_content.split("related_spaces: ")[1].split("\n")[0].split(", ")
    title = guide_content.split("\n")[0]
    contributor = None
    if "Contributed by " in guide_content:
        contributor = guide_content.split("Contributed by ")[1].split("\n")[0]

    url = f"https://gradio.app/{guide_name}/"

    guide_content = "\n".join(
        [
            line
            for line in guide_content.split("\n")
            if not (
                line.startswith("tags: ")
                or line.startswith("related_spaces: ")
                or line.startswith("Contributed by ")
                or line == title
            )
        ]
    )

    guides.append(
        {
            "name": guide_name,
            "pretty_name": pretty_guide_name,
            "content": guide_content,
            "tags": tags,
            "spaces": spaces,
            "url": url,
            "contributor": contributor,
        }
    )


def render_guides_main():
    with open("src/guides_main_template.html", encoding="utf-8") as template_file:
        template = Template(template_file.read())
        output_html = template.render(guides=guides, navbar_html=navbar_html)
    os.makedirs(os.path.join("generated", "guides"), exist_ok=True)
    with open(
        os.path.join("generated", "guides", "index.html"), "w", encoding="utf-8"
    ) as generated_template:
        generated_template.write(output_html)
    with open(
        os.path.join("generated", "guides.html"), "w", encoding="utf-8"
    ) as generated_template:
        generated_template.write(output_html)


def render_guides():
    for guide in guides:
        generate_meta_image(guide)

        code_tags = re.findall(r'\{\{ code\["([^\s]*)"\] \}\}', guide["content"])
        demo_names = re.findall(r'\{\{ demos\["([^\s]*)"\] \}\}', guide["content"])
        code, demos = {}, {}

        guide["content"] = (
            guide["content"]
            .replace("website/src/assets", "/assets")
            .replace("```python\n", "<pre><code class='lang-python'>")
            .replace("```bash\n", "<pre><code class='lang-bash'>")
            .replace("```directory\n", "<pre><code class='lang-bash'>")
            .replace("```csv\n", "<pre><code class='lang-bash'>")
            .replace("```", "</code></pre>")
        )

        for code_src in code_tags:
            with open(os.path.join(GRADIO_DEMO_DIR, code_src, "run.py")) as code_file:
                python_code = code_file.read().replace(
                    'if __name__ == "__main__":\n    iface.launch()', "iface.launch()"
                )
                code[code_src] = (
                    "<pre><code class='lang-python'>" + python_code + "</code></pre>"
                )

        for demo_name in demo_names:
            demos[demo_name] = (
                "</div><div id='interface_" + demo_name + "'></div><div class='prose'>"
            )
        guide_template = Template(guide["content"])
        guide_output = guide_template.render(code=code, demos=demos)

        # Escape HTML tags inside python code blocks so they show up properly
        pattern = "<code class='lang-python'>\n?((.|\n)*?)\n?</code>"
        guide_output = re.sub(
            pattern,
            lambda x: "<code class='lang-python'>"
            + html.escape(x.group(1))
            + "</code>",
            guide_output,
        )

        copy_button = (
            "<button class='copy flex float-right cursor-pointer rounded-l-none rounded-r mx-0 my-2' "
            "onclick='copyCode(this)'><img class='copy-svg m0 w-7 flex-initial' "
            "src='/assets/img/copy-grey.svg'><div class='flex-auto'></div></button>"
        )
        guide_output = guide_output.replace(
            "<pre>", "<div class='code-block' style='display: flex'><pre>"
        )
        guide_output = guide_output.replace("</pre>", f"</pre>{copy_button}</div>")

        output_html = markdown2.markdown(
            guide_output, extras=["target-blank-links", "header-ids", "tables"]
        )
        os.makedirs("generated", exist_ok=True)
        os.makedirs(os.path.join("generated", guide["name"]), exist_ok=True)
        with open(
            "src/guides_template.html", encoding="utf-8"
        ) as general_template_file:
            general_template = Template(general_template_file.read())
        with open(
            os.path.join("generated", guide["name"], "index.html"),
            "w",
            encoding="utf-8",
        ) as generated_template:
            output_html = general_template.render(
                template_html=output_html,
                demo_names=demo_names,
                navbar_html=navbar_html,
                title=guide["pretty_name"],
                url=guide["url"],
                guide_name=guide["name"],
                spaces=guide["spaces"],
                tags=guide["tags"],
                contributor=guide["contributor"],
                **GRADIO_ASSETS,
            )
            generated_template.write(output_html)


def render_docs():
    if os.path.exists("generated/colab_links.json"):
        with open("generated/colab_links.json") as demo_links_file:
            try:
                demo_links = json.load(demo_links_file)
            except ValueError:
                demo_links = {}
    else:  # docs will be missing demo links
        demo_links = {}
    SCREENSHOT_FOLDER = "dist/assets/demo_screenshots"
    os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

    def get_function_documentation(func):
        doc_str = inspect.getdoc(func)
        func_doc, params_doc, return_doc = [], [], []
        documented_params = {"self"}
        mode = "pre"
        for line in doc_str.split("\n"):
            if line.startswith("Parameters:"):
                mode = "in"
                continue
            if line.startswith("Returns:"):
                mode = "out"
                continue
            if "DEPRECATED" in line:
                continue
            if mode == "pre":
                func_doc.append(line)
            elif mode == "in":
                space_index = line.index(" ")
                colon_index = line.index(":")
                name = line[:space_index]
                documented_params.add(name)
                params_doc.append(
                    (
                        name,
                        line[space_index + 2 : colon_index - 1],
                        line[colon_index + 2 :],
                    )
                )
            elif mode == "out":
                colon_index = line.index(":")
                return_doc.append((line[1 : colon_index - 1], line[colon_index + 2 :]))
        params = inspect.getfullargspec(func)
        param_set = []
        for i in range(len(params.args)):
            neg_index = -1 - i
            if params.args[neg_index] not in documented_params:
                continue
            if params.defaults and i < len(params.defaults):
                default = params.defaults[neg_index]
                if type(default) == str:
                    default = '"' + default + '"'
                else:
                    default = str(default)
                param_set.insert(0, (params.args[neg_index], default))
            else:
                param_set.insert(0, (params.args[neg_index],))
        return "\n".join(func_doc), param_set, params_doc, return_doc

    def get_class_documentation(cls):
        inp = {}
        inp["name"] = cls.__name__
        doc = inspect.getdoc(cls)
        doc_lines = doc.split("\n")
        inp["doc"] = "\n".join(doc_lines[:-2])
        inp["type"] = doc_lines[-2].split("type: ")[-1]
        inp["demos"] = doc_lines[-1][7:].split(", ")
        _, inp["params"], inp["params_doc"], _ = get_function_documentation(
            cls.__init__
        )
        inp["shortcuts"] = list(cls.get_shortcut_implementations().items())
        if "interpret" in cls.__dict__:
            (
                inp["interpret"],
                inp["interpret_params"],
                inp["interpret_params_doc"],
                _,
            ) = get_function_documentation(cls.interpret)
            _, _, _, inp["interpret_returns_doc"] = get_function_documentation(
                cls.get_interpretation_scores
            )

        return inp

    inputs = [get_class_documentation(cls) for cls in InputComponent.__subclasses__()]
    outputs = [get_class_documentation(cls) for cls in OutputComponent.__subclasses__()]
    interface_params = get_function_documentation(Interface.__init__)
    interface = {
        "doc": inspect.getdoc(Interface),
        "params": interface_params[1],
        "params_doc": interface_params[2],
    }
    launch_params = get_function_documentation(Interface.launch)
    launch = {
        "params": launch_params[1],
        "params_doc": launch_params[2],
    }
    load_params = get_function_documentation(Interface.load)
    load = {
        "params": load_params[1],
        "params_doc": load_params[2],
        "return_doc": load_params[3],
    }
    docs = {
        "input": inputs,
        "output": outputs,
        "interface": interface,
        "launch": launch,
        "load": load,
    }
    os.makedirs("generated", exist_ok=True)
    with open("src/docs_template.html") as template_file:
        template = Template(template_file.read())
        output_html = template.render(
            docs=docs, demo_links=demo_links, navbar_html=navbar_html
        )
    os.makedirs(os.path.join("generated", "docs"), exist_ok=True)
    with open(
        os.path.join("generated", "docs", "index.html"), "w"
    ) as generated_template:
        generated_template.write(output_html)


def render_other():
    os.makedirs("generated", exist_ok=True)
    for template_filename in os.listdir("src/other_templates"):
        with open(
            os.path.join("src/other_templates", template_filename)
        ) as template_file:
            template = Template(template_file.read())
            output_html = template.render(GRADIO_ASSETS)
        folder_name = template_filename[:-14]
        os.makedirs(os.path.join("generated", folder_name), exist_ok=True)
        with open(
            os.path.join("generated", folder_name, "index.html"), "w", encoding="utf-8"
        ) as generated_template:
            generated_template.write(output_html)


if __name__ == "__main__":
    render_index()
    render_guides_main()
    render_guides()
    render_docs()
    render_other()
