import json
from pathlib import Path
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Settings:
    input_path: str
    input_file: str
    output_path: str
    output_file: str

    def get(self, key: str, default=None):
        """
        Garante compatibilidade com chamadas do tipo settings.get('INPUT_FILE').
        Atende tanto nomes em maiúsculo quanto minúsculo e junta caminhos se necessário.
        """
        key_upper = key.upper()
        
        if key_upper in ("INPUT_FILE", "INPUT_PATH_FULL"):
            return str(Path(self.input_path) / self.input_file)
        elif key_upper in ("OUTPUT_FILE", "OUTPUT_PATH_FULL"):
            return str(Path(self.output_path) / self.output_file)
        
        # Acesso genérico aos atributos minúsculos
        return getattr(self, key.lower(), default)

    def __getitem__(self, item: str):
        """Permite acesso no estilo dicionário: settings['INPUT_FILE']"""
        val = self.get(item)
        if val is None:
            raise KeyError(item)
        return val


def load_settings(config_path: str = "settings.json") -> Settings:
    """
    Carrega as configurações a partir do arquivo JSON.
    """
    with open(config_path, encoding="utf-8") as file:
        load_data = json.load(file)
        
    return Settings(
        input_path=load_data["input_path"],
        input_file=load_data["input_file"],
        output_path=load_data["output_path"],
        output_file=load_data["output_file"]
    )
