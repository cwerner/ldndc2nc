# -*- coding: utf-8 -*-
"""ldndc2nc.config_handler: read the configuration settings for this ldndc2nc run."""

import logging
import os
from pathlib import Path

import yaml

from .variable import Variable

log = logging.getLogger(__name__)


def find_config(local_file=None):
    """ look for config file in the default locations """
    env_var = os.environ.get("LDNDC2NC_CONF", "__NOTSET__")
    locations = [
        x / "ldndc2nc.conf" for x in [Path("."), Path.home(), Path("/etc/ldndc2nc")]
    ]
    locations.append(Path(env_var))

    if local_file:
        locations.insert(0, Path(local_file))

    for cfg_file in locations:
        if cfg_file.is_file():
            return cfg_file
    return None


def read_config(file_path) -> None:
    """ read yaml config file and modify special properties"""

    print(f"read_config: {file_path}")
    with open(file_path, "r") as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

    return cfg


def write_config(self, dest=Path.home()):
    """ write cfg file to user dir """

    if self.cfg:
        self._decode()
        fname = Path(dest) / "ldndc2nc.conf"
        with open(fname, "w") as f:
            f.write(yaml.dump(self._decode(self.cfg), default_flow_style=False))


def get_section(self, section):
    """ parse config data structure, return data of required section """

    if self.cfg:
        self.cfg = self._encode(self.cfg)

    section_data = None

    def is_valid_section(s):
        valid_sections = ["info", "project", "variables", "refdata"]
        return s in valid_sections

    if is_valid_section(section.lower()):
        try:
            section_data = self.cfg.get(section, self.cfg.get(section.lower()))
        except KeyError:
            log.warning(
                f"Section <{section.lower()}> not found in cfg file {self.file_path}"
            )
            log.warning(f"The following sections are present: {list(self.cfg.keys())}.")
    else:
        raise RuntimeError(
            log.critical(f"Section {section.lower()} is not a valid section")
        )
    return section_data


class ConfigHandler:

    _write_config = write_config
    _get_section = get_section

    def __init__(self, local_file=None):
        self.cfg_file = find_config(local_file=local_file)
        raw = read_config(self.cfg_file)
        self.cfg = self._encode(raw)

    @staticmethod
    def _decode(cfg):
        if "variables" in cfg:
            for file, variables in cfg["variables"].items():
                cfg["variables"][file] = [v.text_full for v in variables]
        return cfg

    @staticmethod
    def _encode(cfg):
        if "variables" in cfg:
            for file, variables in cfg["variables"].items():
                cfg["variables"][file] = [
                    Variable(v) if isinstance(v, str) else v for v in variables
                ]
        return cfg

    @property
    def file_path(self):
        if not self.cfg_file:
            self.cfg_file = find_config()
        return self.cfg_file

    @property
    def variables(self):
        vars = []
        if "variables" in self.cfg:
            for file, variables in self.cfg["variables"].items():
                vars += [Variable(v) if isinstance(v, str) else v for v in variables]
        return vars

    @property
    def text(self):
        clean = self._decode(self.cfg)
        return yaml.dump(clean, default_style=False) if self.cfg else None

    @property
    def global_info(self):
        global_info = {}
        for section_name in ["info", "project"]:
            section = self.section(section_name)
            if section:
                global_info.update(section)
            else:
                log.warn(f"No <{section_name}> data found in config")
        return global_info

    def section(self, section):
        return self._get_section(section)

    def write(self, *args, **kwargs):
        self._write_config(*args, **kwargs)

    def __repr__(self):
        return f"<cfg: {self.file_path}>"
