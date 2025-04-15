from core.base import Singleton
import os
import json
from typing import Dict


class ConfigManager(Singleton):
    def __init__(self, config_path:str="./config/rmsc01.json"):
        super().__init__()

        self.config_path = config_path
        self.load_config(config_path)

    def load_config(self, config_path:str="./config/rmsc01.json"):
        if os.path.isfile(config_path:str):
            with open(config_path, "r") as config_file:
                config_data = json.load(config_file)
                self._update_attributes(config_data)
        else:
            raise FileNotFoundError(f"No {config_file} found in {self.config_dir}")

    def _update_attributes(self, config_data:Dict, prefix:str = ""):
        for key, value in config_data.items():
            if isinstance(value, dict):
                self._update_attributes(value, prefix + key + ".")
            else:
                attribute_name = prefix + key
                self._set_nested_attribute(attribute_name, value)

    def _set_nested_attribute(self, attribute_name, value):
        parts = attribute_name.split(".")
        obj = self
        for part in parts[:-1]:
            if not hasattr(obj, part):
                setattr(obj, part, SimpleNamespace())
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)

    def __getattr__(self, name):
        raise AttributeError(
            f"Attribute '{name}' not found in {self.config_path}."
        )
