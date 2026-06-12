import os
import inspect
import importlib.util
import logging
from typing import List, Type
from app.sdk.tools import BaseTool

logger = logging.getLogger("AgentForge.PluginLoader")

def load_plugins_from_directory(directory_path: str) -> List[Type[BaseTool]]:
    """Scan directory for python files, import modules, and register classes extending BaseTool."""
    tools = []
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        return tools

    for filename in os.listdir(directory_path):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            file_path = os.path.join(directory_path, filename)
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find all classes that subclass BaseTool
                    for name, cls in inspect.getmembers(module, inspect.isclass):
                        if issubclass(cls, BaseTool) and cls is not BaseTool:
                            tools.append(cls)
                            logger.info(f"Loaded custom SDK plugin: {cls.__name__} from {filename}")
            except Exception as err:
                logger.error(f"Failed to load plugin from file {filename}: {err}")
                
    return tools
