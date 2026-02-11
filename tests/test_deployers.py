"""Tests for deployers."""

import pytest
import tempfile
from pathlib import Path
from multi_platform_deployer.deployers import (
    RenderDeployer,
    RailwayDeployer,
    VercelDeployer,
    HerokuDeployer,
)


class TestRenderDeployer:
    """Test RenderDeployer class."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_platform_name(self):
        """Test platform name."""
        assert RenderDeployer.get_platform_name() == "Render"
    
    def test_get_config_template(self, temp_project):
        """Test config template generation."""
        config = {"app_name": "test-app"}
        deployer = RenderDeployer(temp_project, config)
        template = deployer.get_config_template()
        
        assert "services" in template
        assert len(template["services"]) > 0
        assert template["services"][0]["type"] == "web"
    
    def test_validation_without_render_yaml(self, temp_project):
        """Test validation fails without render.yaml."""
        deployer = RenderDeployer(temp_project)
        
        # Should fail because render.yaml doesn't exist
        assert deployer.validate() is False


class TestRailwayDeployer:
    """Test RailwayDeployer class."""
    
    def test_platform_name(self):
        """Test platform name."""
        assert RailwayDeployer.get_platform_name() == "Railway"
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_get_config_template(self, temp_project):
        """Test config template generation."""
        deployer = RailwayDeployer(temp_project)
        template = deployer.get_config_template()
        
        assert "$schema" in template
        assert "deploy" in template


class TestVercelDeployer:
    """Test VercelDeployer class."""
    
    def test_platform_name(self):
        """Test platform name."""
        assert VercelDeployer.get_platform_name() == "Vercel"


class TestHerokuDeployer:
    """Test HerokuDeployer class."""
    
    def test_platform_name(self):
        """Test platform name."""
        assert HerokuDeployer.get_platform_name() == "Heroku"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
