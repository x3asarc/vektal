"""
Configuration Loader

Load and validate vendor configurations and store profiles.
"""

from pathlib import Path
import yaml
from typing import Union

from .vendor_schema import VendorConfig, SKUPattern, VendorInfo, VendorURLs, ScrapingConfig
from .store_profile_schema import StoreProfile


def load_vendor_config(yaml_path: Union[Path, str]) -> VendorConfig:
    """
    Load and validate vendor YAML configuration.

    Args:
        yaml_path: Path to vendor YAML file

    Returns:
        VendorConfig instance
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Vendor config not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return VendorConfig.model_validate(data)


def load_store_profile(yaml_path: Union[Path, str]) -> StoreProfile:
    """
    Load and validate store profile.

    Args:
        yaml_path: Path to store profile YAML

    Returns:
        StoreProfile instance
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Store profile not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return StoreProfile.model_validate(data)


def save_vendor_config(config: VendorConfig, yaml_path: Union[Path, str]) -> None:
    """
    Save vendor config to YAML.

    Args:
        config: VendorConfig instance
        yaml_path: Path to save YAML file
    """
    path = Path(yaml_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        yaml.dump(
            config.model_dump(exclude_none=True, mode='json'),
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True
        )


def save_store_profile(profile: StoreProfile, yaml_path: Union[Path, str]) -> None:
    """
    Save store profile to YAML.

    Args:
        profile: StoreProfile instance
        yaml_path: Path to save YAML file
    """
    path = Path(yaml_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        yaml.dump(
            profile.model_dump(exclude_none=True, mode='json'),
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True
        )


def list_vendor_configs(config_dir: Union[Path, str] = "config/vendors") -> list[Path]:
    """
    List all vendor YAML files.

    Args:
        config_dir: Directory containing vendor configs

    Returns:
        List of Path objects
    """
    path = Path(config_dir)
    if not path.exists():
        return []
    return [f for f in path.glob("*.yaml") if not f.name.startswith("_")]
