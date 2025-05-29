from typing import Callable, Optional, Dict, Any
from nicegui import ui

class form(ui.card):
    def __init__(self, on_submit: Optional[Callable] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.elements: Dict[str, Any] = {}
        self.on_submit_callback = on_submit
        self.submit_button = None
        self._container = None

    def __enter__(self):
        self._container = super().__enter__()
        return self

    def add_element(self, element: Any, key: str) -> None:
        """Speichert Referenz zu Elementen mit key-Property"""
        if hasattr(element, 'props') and 'key' in element.props:
            self.elements[key] = element

    def collect_values(self) -> Dict[str, Any]:
        """Sammelt Werte aller Elemente mit key-Property"""
        values = {}
        for key, element in self.elements.items():
            # Zugriff auf den Wert über das Value-Model des Elements
            if hasattr(element, 'value'):
                values[key] = element.value
            elif hasattr(element, 'values') and hasattr(element, 'value'):
                # Für Elemente wie Select mit options
                values[key] = element.value
        return values

    def submit(self) -> None:
        """Handler für Submit-Ereignis"""
        # check if descendant elements exist
        for descendant in self._container.descendants():
            if hasattr(descendant, 'props') and 'key' in descendant.props:
                self.add_element(descendant, descendant.props['key'])
        if self.on_submit_callback:
            kwargs = self.collect_values()
            self.on_submit_callback(**kwargs)

    def create_submit_button(self, label: str = 'Submit', **kwargs) -> None:
        """Erstellt den Submit-Button mit optionalen Eigenschaften"""
        with ui.row().classes('w-full justify-end'):
            self.submit_button = ui.button(label, on_click=self.submit, **kwargs)
            return self.submit_button

def example_usage():
    def handle_submit(**kwargs):
        print("Submitted values:", kwargs)
        ui.notify(f"Received values: {kwargs}")

    with form(on_submit=handle_submit) as f:
        ui.input('Name').props('key=name')
        ui.input('Email').props('key=email type=email')
        ui.select(['Water', 'Beer', 'Soda'], label='Drink').props('key=drink')
        ui.checkbox('Agree to terms').props('key=agree')
        f.create_submit_button('Save', icon='save')

