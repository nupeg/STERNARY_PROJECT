from dataclasses import dataclass
from json import load

@dataclass(slots=True, frozen=True)
class Settings:
    input_path: str
    input_file: str

    output_path: str
    output_file: str


def load_settings() -> Settings:
    with open("settings.json", encoding="utf-8") as file:
        load_data = load(file)
    settings = Settings(
        input_path=load_data["input_path"],
        input_file=load_data["input_file"],

        output_path=load_data["output_path"],
        output_file=load_data["output_file"]     
    )
    return settings
