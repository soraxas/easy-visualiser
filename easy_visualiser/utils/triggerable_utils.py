from typing import Optional

from easy_visualiser.key_mapping import Key
from easy_visualiser.modal_control import ModalControl
from easy_visualiser.plugin_capability import TriggerableMixin
from easy_visualiser.plugins import VisualisablePlugin


def move_triggerable_plugin_keys_to_nested_modal_control(
    plugin: TriggerableMixin, key: Key.KeyType, modal_name: Optional[str] = None
) -> VisualisablePlugin:
    plugin.replace_mappings_with(
        ModalControl(key, plugin.get_copied_mapping_list(), modal_name)
    )
    assert isinstance(plugin, VisualisablePlugin)
    return plugin
