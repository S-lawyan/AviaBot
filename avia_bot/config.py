import os

import yaml
from pydantic import BaseModel, SecretStr
from loguru import logger


class BotConfig(BaseModel):
    bot_token: SecretStr
    api_token: SecretStr
    channel_id: int


class DatabaseConfig(BaseModel):
    db_host: str
    db_port: int
    db_user: str
    db_pass: SecretStr
    db_name: str

    def get_mysql_uri(self) -> str:
        uri_template = "mysql+asyncmy://{user}:{password}@{host}:{port}/{db_name}"
        return uri_template.format(
            user=self.db_user,
            password=self.db_pass.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            db_name=self.db_name,
        )


class Settings(BaseModel):
    db: DatabaseConfig
    bot: BotConfig


def load_config(config_path: str) -> Settings:
    try:
        with open(file=config_path, mode="r") as file:
            dictionary: dict = yaml.load(stream=file, Loader=yaml.FullLoader)
            config: Settings = Settings.model_validate(dictionary)
        return config

    except FileNotFoundError:
        logger.error(f"The configuration file is missing along the path: {file_path}")

    except yaml.YAMLError as exception:
        logger.error(f"Error loading YAML: {exception}")

    except Exception as e:
        logger.error(f"An UNUSUAL  error occurred while loading the configuration file:: {e}")


__all__ = ["Settings", "load_config"]