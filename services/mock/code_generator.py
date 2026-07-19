"""Generate realistic Python function code"""

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class FunctionCode:
    name: str
    source: str
    has_error_handling: bool
    exception_types: list[str]
    retry_logic: bool


class PythonCodeGenerator:
    """Generate realistic Python function code"""

    def __init__(self, random_instance: random.Random):
        self.random = random_instance
        self.indent = "    "

    def generate_function(
        self,
        name: str,
        complexity: int = 1,
        has_error_handling: bool = True
    ) -> FunctionCode:
        """Generate a complete Python function"""

        patterns = [
            self._pattern_simple,
            self._pattern_retry_loop,
            self._pattern_try_except,
            self._pattern_try_except_else,
            self._pattern_nested_try,
            self._pattern_resource_cleanup,
        ]

        pattern = self.random.choice(patterns)
        code, exceptions, has_retry = pattern(name, complexity, has_error_handling)

        return FunctionCode(
            name=name,
            source=code,
            has_error_handling=has_error_handling and "try:" in code,
            exception_types=exceptions,
            retry_logic=has_retry
        )

    def _pattern_simple(self, name: str, complexity: int, has_error: bool) -> tuple:
        """Simple function with optional error handling"""
        code = f"def {name}():\n"
        exceptions = []
        has_retry = False

        if has_error and self.random.random() > 0.5:
            code += f'{self.indent}"""Function with basic error handling."""\n'
            code += f'{self.indent}try:\n'
            code += f'{self.indent * 2}result = perform_operation()\n'
            code += f'{self.indent * 2}return result\n'

            exception_type = self.random.choice([
                "ValueError", "KeyError", "TypeError",
                "AttributeError", "IndexError", "Exception"
            ])
            exceptions = [exception_type]
            code += f'{self.indent}except {exception_type} as e:\n'
            code += f'{self.indent * 2}logger.error(f"Error in {name}: {{e}}")\n'
            code += f'{self.indent * 2}return None\n'
        else:
            code += f'{self.indent}"""Simple function."""\n'
            code += f'{self.indent}return 42\n'

        return code, exceptions, has_retry

    def _pattern_retry_loop(self, name: str, complexity: int, has_error: bool) -> tuple:
        """Function with retry logic"""
        code = f"def {name}(max_retries=3):\n"
        code += f'{self.indent}"""Function with retry mechanism."""\n'
        code += f'{self.indent}for attempt in range(max_retries):\n'
        code += f'{self.indent * 2}try:\n'
        code += f'{self.indent * 3}response = fetch_data(timeout=5)\n'
        code += f'{self.indent * 3}return response\n'
        code += f'{self.indent * 2}except (ConnectionError, TimeoutError) as e:\n'
        code += f'{self.indent * 3}if attempt < max_retries - 1:\n'
        code += f'{self.indent * 4}logger.warning(f"Retry {{attempt + 1}}/{{max_retries}}")\n'
        code += f'{self.indent * 4}time.sleep(2 ** attempt)\n'
        code += f'{self.indent * 3}else:\n'
        code += f'{self.indent * 4}raise\n'
        code += f'{self.indent}return None\n'

        return code, ["ConnectionError", "TimeoutError"], True

    def _pattern_try_except(self, name: str, complexity: int, has_error: bool) -> tuple:
        """Try/except with multiple handlers"""
        code = f"def {name}(data):\n"
        code += f'{self.indent}"""Parse JSON data with error handling."""\n'
        code += f'{self.indent}try:\n'
        code += f'{self.indent * 2}parsed = json.loads(data)\n'
        code += f'{self.indent * 2}return parsed["value"]\n'
        code += f'{self.indent}except json.JSONDecodeError as e:\n'
        code += f'{self.indent * 2}logger.error(f"Invalid JSON: {{e}}")\n'
        code += f'{self.indent * 2}return {{}}\n'
        code += f'{self.indent}except KeyError:\n'
        code += f'{self.indent * 2}logger.warning("Missing key")\n'
        code += f'{self.indent * 2}return None\n'
        code += f'{self.indent}except Exception as e:\n'
        code += f'{self.indent * 2}logger.critical(f"Unexpected: {{e}}")\n'
        code += f'{self.indent * 2}raise\n'

        return code, ["json.JSONDecodeError", "KeyError", "Exception"], False

    def _pattern_try_except_else(self, name: str, complexity: int, has_error: bool) -> tuple:
        """Try/except/else pattern"""
        code = f"def {name}():\n"
        code += f'{self.indent}"""Function with try/except/else."""\n'
        code += f'{self.indent}try:\n'
        code += f'{self.indent * 2}connection = open_connection()\n'
        code += f'{self.indent}except ConnectionError:\n'
        code += f'{self.indent * 2}logger.error("Failed to connect")\n'
        code += f'{self.indent * 2}return False\n'
        code += f'{self.indent}else:\n'
        code += f'{self.indent * 2}result = connection.query()\n'
        code += f'{self.indent * 2}return result is not None\n'

        return code, ["ConnectionError"], False

    def _pattern_nested_try(self, name: str, complexity: int, has_error: bool) -> tuple:
        """Nested try/except blocks"""
        code = f"def {name}():\n"
        code += f'{self.indent}"""Function with nested error handling."""\n'
        code += f'{self.indent}try:\n'
        code += f'{self.indent * 2}try:\n'
        code += f'{self.indent * 3}data = load_config()\n'
        code += f'{self.indent * 2}except FileNotFoundError:\n'
        code += f'{self.indent * 3}data = get_default_config()\n'
        code += f'{self.indent * 2}process_data(data)\n'
        code += f'{self.indent}except ValueError as e:\n'
        code += f'{self.indent * 2}logger.error(f"Invalid data: {{e}}")\n'
        code += f'{self.indent * 2}raise ConfigError() from e\n'

        return code, ["FileNotFoundError", "ValueError"], False

    def _pattern_resource_cleanup(self, name: str, complexity: int, has_error: bool) -> tuple:
        """Resource cleanup with finally"""
        code = f"def {name}():\n"
        code += f'{self.indent}"""Function with resource cleanup."""\n'
        code += f'{self.indent}file = None\n'
        code += f'{self.indent}try:\n'
        code += f'{self.indent * 2}file = open("data.txt")\n'
        code += f'{self.indent * 2}content = file.read()\n'
        code += f'{self.indent * 2}return process_content(content)\n'
        code += f'{self.indent}except IOError as e:\n'
        code += f'{self.indent * 2}logger.error(f"IO error: {{e}}")\n'
        code += f'{self.indent * 2}return None\n'
        code += f'{self.indent}finally:\n'
        code += f'{self.indent * 2}if file:\n'
        code += f'{self.indent * 3}file.close()\n'

        return code, ["IOError"], False
