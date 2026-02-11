"""Tests for configuration management."""

import pytest
from pathlib import Path
import json
import yaml
import tempfile
from multi_platform_deployer.config.loader import ConfigLoader
from multi_platform_deployer.config.validator import ConfigValidator


class TestConfigLoader:
    """Test ConfigLoader class."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_load_yaml_config(self, temp_project):
        """Test loading YAML configuration."""
        config_file = Path(temp_project) / "deployment.yaml"
        config_data = {
            "platform": "render",
            "app_name": "test-app",
        }
        
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        
        loader = ConfigLoader(temp_project)
        config = loader.load_config("deployment.yaml")
        
        assert config["platform"] == "render"
        assert config["app_name"] == "test-app"
    
    def test_load_json_config(self, temp_project):
        """Test loading JSON configuration."""
        config_file = Path(temp_project) / "deployment.json"
        config_data = {
            "platform": "railway",
            "app_name": "my-app",
        }
        
        with open(config_file, "w") as f:
            json.dump(config_data, f)
        
        loader = ConfigLoader(temp_project)
        config = loader.load_config("deployment.json")
        
        assert config["platform"] == "railway"
        assert config["app_name"] == "my-app"
    
    def test_get_set_config(self, temp_project):
        """Test getting and setting config values."""
        loader = ConfigLoader(temp_project)
        
        loader.set("platform", "vercel")
        assert loader.get("platform") == "vercel"
        
        loader.set("app_name", "vercel-app")
        assert loader.get("app_name") == "vercel-app"
    
    def test_load_env_file(self, temp_project):
        """Test loading environment file."""
        env_file = Path(temp_project) / ".env"
        with open(env_file, "w") as f:
            f.write("DATABASE_URL=postgres://localhost/db\n")
            f.write("SECRET_KEY=mysecret\n")
            f.write("# Comment line\n")
            f.write("APP_NAME=test-app\n")
        
        loader = ConfigLoader(temp_project)
        env_vars = loader.load_env_file()
        
        assert env_vars["DATABASE_URL"] == "postgres://localhost/db"
        assert env_vars["SECRET_KEY"] == "mysecret"
        assert env_vars["APP_NAME"] == "test-app"
        assert len(env_vars) == 3


class TestConfigValidator:
    """Test ConfigValidator class."""
    
    def test_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            "platform": "render",
            "app_name": "test-app",
        }
        
        is_valid, errors = ConfigValidator.validate(config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_required_keys(self):
        """Test validation with missing required keys."""
        config = {"platform": "render"}
        
        is_valid, errors = ConfigValidator.validate(config)
        
        assert is_valid is False
        assert "app_name" in str(errors)
    
    def test_invalid_platform(self):
        """Test validation with invalid platform."""
        config = {
            "platform": "invalid-platform",
            "app_name": "test-app",
        }
        
        is_valid, errors = ConfigValidator.validate(config)
        
        assert is_valid is False
    
    def test_multiple_platforms(self):
        """Test validation with multiple platforms."""
        config = {
            "platform": ["render", "railway"],
            "app_name": "test-app",
        }
        
        is_valid, errors = ConfigValidator.validate(config)
        
        assert is_valid is True
    
    def test_empty_app_name(self):
        """Test validation with empty app_name."""
        config = {
            "platform": "render",
            "app_name": "",
        }
        
        is_valid, errors = ConfigValidator.validate(config)
        
        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
