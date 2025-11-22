import inspect
import dash_extensions.enrich as dee
import dash_extensions as de
import dash_extensions.utils as deu
from dash.development.base_component import Component
import textwrap as tw
import itertools as itt


SCRIPT: dict[str, str] = {"src": "https://pyscript.net/releases/2024.5.1/core.js", "type": "module"}


STYLESHEET: dict[str, str] = {"href": "https://pyscript.net/releases/2024.1.1/core.css", "rel": "stylesheet"}


class ClientsidePythonTransform(dee.DashTransform):
    def __init__(self, prefix: str | None = None):
        self.prefix = prefix or ""
        super().__init__()

    @staticmethod
    def _filter(callbacks: list[dee.CallbackBlueprint]) -> tuple[list[dee.CallbackBlueprint], list[dee.CallbackBlueprint]]:
        server, client = [], []
        for callback in callbacks:
            client.append(callback) if callback.kwargs.get("clientside", False) else server.append(callback)
        return server, client
    
    @staticmethod
    def _remove_decorator(source: str) -> str:
        if source.startswith(" "):
            source = tw.dedent(source)
        if not source.startswith("@"):
            return source
        index: int = source.index("def")
        return source[index:]

    
    @staticmethod
    def _to_js(callback: dee.CallbackBlueprint, name: str) -> dee.CallbackBlueprint:
        annotations = inspect.getfullargspec(callback.f).annotations
        args = [a for a in annotations if a != "return"]
        args_str: str = ",".join(args)
        js_str: str = fr"({args_str}) => {name}({args_str})"
        callback.f = js_str
        return callback


    def _get_name(self, source: str) -> str:
        start: int = source.index("def") + 4
        rest = source[start:]
        try:
            end = rest.index(r"(")
        except ValueError:
            end = rest.index(r"[")
        return self.prefix + rest[:end]

    def apply(self, callbacks: list[dee.CallbackBlueprint], clientside_callbacks: list[dee.CallbackBlueprint]) -> tuple[list[dee.CallbackBlueprint], list[dee.CallbackBlueprint]]:
        python_server_callbacks, self.python_client_callbacks = ClientsidePythonTransform._filter(callbacks)

        self.source = [ClientsidePythonTransform._remove_decorator(inspect.getsource(cb.f)) for cb in self.python_client_callbacks]
        self.names = [self._get_name(f_str) for f_str in self.source]

        return self.apply_serverside(python_server_callbacks), self.apply_clientside(clientside_callbacks)

    def apply_serverside(self, callbacks: list[dee.CallbackBlueprint]) -> list[dee.CallbackBlueprint]:
        return callbacks

    def apply_clientside(self, callbacks: list[dee.CallbackBlueprint]) -> list[dee.CallbackBlueprint]:
        return [*callbacks, *itt.starmap(ClientsidePythonTransform._to_js, zip(self.python_client_callbacks, self.names))]


    def transform_layout(self, layout: list[Component]) -> None:
        layout.children = [
            *deu.as_list(layout.children),
            de.Purify(
                html=fr"""
                <py-script>
                    import js
                    from pyscript.ffi import create_proxy

                    {"".join(self.source)}

                    for name in {str(self.names)}:
                        f = globals()[name]
                        js_f = create_proxy(f)
                        setattr(js, name, js_f)

                </py-script>""",
                config={
                    "ALLOWED_TAGS": ["py-script"]
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
