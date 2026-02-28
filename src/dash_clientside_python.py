import inspect
import typing_extensions as tp
import dash_extensions.enrich as dee
import dash_extensions as de
import dash_extensions.utils as deu
from dash.development.base_component import Component
import textwrap as tw
import itertools as itt
import dill


SCRIPT: dict[str, str] = {"src": "https://pyscript.net/releases/2024.5.1/core.js", "type": "module"}


STYLESHEET: dict[str, str] = {"href": "https://pyscript.net/releases/2024.1.1/core.css", "rel": "stylesheet"}


class ClientsidePythonTransform(dee.DashTransform):
    def __init__(self, prefix: str | None = None):
        self.prefix = prefix or ""
        self.ff = []
        super().__init__()

    @staticmethod
    def _filter(callbacks: list[dee.CallbackBlueprint]) -> tuple[list[dee.CallbackBlueprint], list[dee.CallbackBlueprint]]:
        server, client = [], []
        for callback in callbacks:
            client.append(callback) if callback.kwargs.get("clientside", False) else server.append(callback)
        return server, client
    
    def _to_js(self, callback: dee.CallbackBlueprint) -> dee.CallbackBlueprint:
        annotations = inspect.getfullargspec(callback.f).annotations
        name: str = callback.f.__name__
        args = [a for a in annotations if a != "return"]
        args_str: str = ",".join(args)
        js_str: str = fr"({args_str}) => {name}({args_str})"
        self.ff.append(callback.f)
        callback.f = js_str
        return callback

    def apply(self, callbacks: list[dee.CallbackBlueprint], clientside_callbacks: list[dee.CallbackBlueprint]) -> tuple[list[dee.CallbackBlueprint], list[dee.CallbackBlueprint]]:
        callbacks, self.python_client_callbacks = ClientsidePythonTransform._filter(callbacks)

        return self.apply_serverside(callbacks), self.apply_clientside(clientside_callbacks + list(map(self._to_js, self.python_client_callbacks)))

    def transform_layout(self, layout: list[Component]) -> None:
        names = [f.__name__ for f in self.ff]

        ff_bytes = list(map(dill.dumps, self.ff))

        layout.children = [
            *deu.as_list(layout.children),
            de.Purify(
                html=
                """
                <script>
                    console.log("here");
                    await pyodide.loadPackage("micropip");
                    const micropip = pyodide.pyimport("micropip");
                    await micropip.install("dill");
                    console.log("here");
                </script>
                """ + fr"""
                <py-script>
                    import js
                    # import dill

                    from pyscript.ffi import create_proxy

                    for name, f_b in zip({str(names)}, {str(ff_bytes)}):
                        continue
                        f = dill.loads(f_b)
                        js_f = create_proxy(f)
                        setattr(js, name, js_f)

                </py-script>
                """
                ,
                config={
                    "ALLOWED_TAGS": ["py-script", "script"]
                }
            )
        ]


if __name__ == "__main__":
    from dash import html, Input
    app: dee.DashProxy = dee.DashProxy(transforms=[ClientsidePythonTransform()], external_scripts=[SCRIPT], external_stylesheets=[STYLESHEET])
    app.layout = (button := html.Button("Hello World"))


    @app.callback(
        Input(button, "n_clicks"),
        prevent_inital_call=True,
        clientside=True,
    )
    def foo(_: int) -> None:
        print("Hi on the client")

    app.run()
