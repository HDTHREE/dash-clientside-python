import inspect
import dash_extensions.enrich as dee
import dash_extensions as de
import dash_extensions.utils as deu
import dash.html as html
from dash import Input, clientside_callback
import dash_extensions.javascript as djs
from dash.development.base_component import Component
import itertools as itt

clientside_callback


class ClientsidePythonTransform(dee.DashTransform):

    @staticmethod
    def _filter(callbacks: list[dee.CallbackBlueprint]) -> tuple[list[dee.CallbackBlueprint], list[dee.CallbackBlueprint]]:
        server, client = [], []
        for callback in callbacks:
            client.append(callback) if callback.kwargs.get("clientside", False) else server.append(callback)
        return server, client
    
    @staticmethod
    def _remove_decorator(source: str) -> str:
        if not source.startswith("@"):
            return source
        index: int = source.index("def")
        return source[index:]
    
    @staticmethod
    def _to_js(callback: dee.CallbackBlueprint, name: str) -> dee.CallbackBlueprint:
        annotations = inspect.getfullargspec(callback.f).annotations
        args = [a for a in annotations if a != "return"]
        args_str: str = ",".join(args)
        js_str: str = fr"({args_str}) => {name}({args_str});"
        callback.f = js_str
        return callback


    def _get_name(source: str) -> str:
        start: int = source.index("def") + 4
        rest = source[start:]
        try:
            end = rest.index(r"(")
        except ValueError:
            end = rest.index(r"[")
        return rest[:end]

    def apply(self, callbacks: list[dee.CallbackBlueprint], clientside_callbacks: list[dee.CallbackBlueprint]) -> tuple[list[dee.CallbackBlueprint], list[dee.CallbackBlueprint]]:
        python_server_callbacks, self.python_client_callbacks = ClientsidePythonTransform._filter(callbacks)

        self.source = [ClientsidePythonTransform._remove_decorator(inspect.getsource(cb.f)) for cb in self.python_client_callbacks]
        self.names = [ClientsidePythonTransform._get_name(f_str) for f_str in self.source]

        return self.apply_serverside(python_server_callbacks), self.apply_clientside(clientside_callbacks)

    def apply_serverside(self, callbacks: list[dee.CallbackBlueprint]) -> list[dee.CallbackBlueprint]:
        return callbacks

    def apply_clientside(self, callbacks: list[dee.CallbackBlueprint]) -> list[dee.CallbackBlueprint]:
        return [*callbacks, *itt.starmap(ClientsidePythonTransform._to_js, zip(self.python_client_callbacks, self.names))]


    def transform_layout(self, layout: list[Component]):
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


app = dee.DashProxy(transforms=[ClientsidePythonTransform()], external_scripts=[{"src": "https://pyscript.net/releases/2024.5.1/core.js", "type": "module"}], external_stylesheets=[{"href": "https://pyscript.net/releases/2024.1.1/core.css", "rel": "stylesheet"}])
button = html.Button()
app.layout = html.Div(children=button)

setattr



@app.callback(Input(button, "n_clicks"), Input(button, "disabled"), clientside=True)
def test(_: int, checked: bool) -> None:
    print("here")


app.run()
