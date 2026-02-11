"""Tests for utility functions."""

import pytest
import tempfile
from pathlib import Path
from multi_platform_deployer.utils.helpers import (
    read_file,
    write_file,
    read_json,
    write_json,
    read_yaml,
    write_yaml,
    file_exists,
    dir_exists,
)
from multi_platform_deployer.utils.validators import (
    validate_requirements_file,
    validate_python_file,
)
import json
import yaml


class TestHelpers:
    """Test helper functions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_write_and_read_file(self, temp_dir):
        """Test writing and reading text files."""
        file_path = Path(temp_dir) / "test.txt"
        content = "Hello, World!"
        
        write_file(str(file_path), content)
        read_content = read_file(str(file_path))
        
        assert read_content == content
    
    def test_write_and_read_json(self, temp_dir):
        """Test JSON file operations."""
        file_path = Path(temp_dir) / "data.json"
        data = {"name": "test", "value": 42}
        
        write_json(str(file_path), data)
        read_data = read_json(str(file_path))
        
        assert read_data == data
    
    def test_write_and_read_yaml(self, temp_dir):
        """Test YAML file operations."""
        file_path = Path(temp_dir) / "config.yaml"
        data = {"app": "test", "version": "1.0"}
        
        write_yaml(str(file_path), data)
        read_data = read_yaml(str(file_path))
        
        assert read_data == data
    
    def test_file_exists(self, temp_dir):
        """Test file existence check."""
        file_path = Path(temp_dir) / "test.txt"
        
        assert file_exists(str(file_path)) is False
        
        write_file(str(file_path), "test")
        assert file_exists(str(file_path)) is True
    
    def test_dir_exists(self, temp_dir):
        """Test directory existence check."""
        assert dir_exists(temp_dir) is True
        assert dir_exists(str(Path(temp_dir) / "nonexistent")) is False


class TestValidators:
    """Test validation functions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_validate_requirements_file(self, temp_dir):
        """Test requirements file validation."""
        req_file = Path(temp_dir) / "requirements.txt"
        content = "Flask==2.0.0\nDjango>=3.0\nrequests\n"
        
        with open(req_file, "w") as f:
            f.write(content)
        
        is_valid, errors = validate_requirements_file(str(req_file))
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_python_file(self, temp_dir):
        """Test Python file validation."""
        py_file = Path(temp_dir) / "test.py"
        content = "x = 1\ny = 2\nprint(x + y)\n"
        
        with open(py_file, "w") as f:
            f.write(content)
        
        is_valid, errors = validate_python_file(str(py_file))
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_invalid_python_file(self, temp_dir):
        """Test validation with invalid Python."""
        py_file = Path(temp_dir) / "invalid.py"
        content = "x = 1\nif x == 1\n  print(x)"  # Missing colon
        
        with open(py_file, "w") as f:
            f.write(content)
        
        is_valid, errors = validate_python_file(str(py_file))
        
        assert is_valid is False
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
