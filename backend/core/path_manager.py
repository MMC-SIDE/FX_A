"""
Path management for consistent Python path handling across the application
"""
import sys
import os
from pathlib import Path
from typing import Optional


class PathManager:
    """Central path management for the FX Trading System"""
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent.parent
        self.root_dir = self.backend_dir.parent
        self.setup_paths()
    
    def setup_paths(self):
        """Setup Python path for imports"""
        backend_str = str(self.backend_dir)
        
        # Add backend directory to Python path if not already present
        if backend_str not in sys.path:
            sys.path.insert(0, backend_str)
        
        # Set environment variable for subprocess compatibility
        current_pythonpath = os.environ.get('PYTHONPATH', '')
        if backend_str not in current_pythonpath:
            if current_pythonpath:
                os.environ['PYTHONPATH'] = f"{backend_str}{os.pathsep}{current_pythonpath}"
            else:
                os.environ['PYTHONPATH'] = backend_str
    
    def get_backend_dir(self) -> Path:
        """Get backend directory path"""
        return self.backend_dir
    
    def get_root_dir(self) -> Path:
        """Get project root directory path"""
        return self.root_dir
    
    def get_logs_dir(self) -> Path:
        """Get logs directory path"""
        logs_dir = self.root_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        return logs_dir
    
    def get_config_dir(self) -> Path:
        """Get config directory path"""
        config_dir = self.root_dir / "config"
        config_dir.mkdir(exist_ok=True)
        return config_dir
    
    def get_data_dir(self) -> Path:
        """Get data directory path"""
        data_dir = self.root_dir / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir


# Singleton instance
_path_manager: Optional[PathManager] = None


def get_path_manager() -> PathManager:
    """Get the singleton PathManager instance"""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager


def setup_python_path():
    """Convenience function to setup Python path"""
    get_path_manager().setup_paths()


# Auto-setup when module is imported
setup_python_path()