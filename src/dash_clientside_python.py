

import dash_extensions.enrich as dee
import dash_extensions as de
from dash import html
from dash.development.base_component import Component



class ClientsidePythonTransform(dee.DashTransform):
    def apply(self, callbacks: list[dee.CallbackBlueprint], clientside_callbacks: list[dee.CallbackBlueprint]) -> tuple[list[dee.CallbackBlueprint], list[dee.CallbackBlueprint]]:
        return self.apply_serverside(callbacks), self.apply_clientside(clientside_callbacks)

    def apply_serverside(self, callbacks: list[dee.CallbackBlueprint]) -> list[dee.CallbackBlueprint]:
        return callbacks

    def apply_serverside(self, callbacks: list[dee.CallbackBlueprint]) -> list[dee.CallbackBlueprint]:
        return callbacks

    def transform_layout(self, layout: Component):
        children = as_list(layout.children) + self.components
        layout.children = children + [

                de.DeferScript(src="https://pyscript.net/latest/pyscript.js"),
                de.Purify(html=r"""<py-script> print("Hello from PyScript!") </py-script> """)
        ]

