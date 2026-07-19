"""
Mock application with various code patterns for instrumentation testing.
This is the code that will be instrumented by RuntimeSpy.
"""

import random
import time
from typing import Optional, List, Dict


def simple_calculation(x: int, y: int) -> int:
    """Simple function that gets executed frequently."""
    return x + y


def calculate_average(numbers: List[int]) -> float:
    """Executed frequently - calculates average."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def unused_helper() -> str:
    """Dead code - never called."""
    return "This function is never executed"


def validate_input(value: str) -> bool:
    """Validates input - used in most paths."""
    if not value:
        return False
    return len(value) > 0


def retry_with_backoff(max_retries: int = 3):
    """Function with retry logic."""
    for attempt in range(max_retries):
        try:
            if random.random() > 0.7:
                raise ConnectionError("Connection failed")
            return f"Success on attempt {attempt + 1}"
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.01)


def handle_exception(operation: str) -> Optional[str]:
    """Function with exception handling."""
    try:
        if operation == "fail":
            raise ValueError("Operation failed")
        elif operation == "timeout":
            raise TimeoutError("Operation timed out")
        return f"Operation {operation} succeeded"
    except ValueError as e:
        return f"Caught ValueError: {e}"
    except Exception as e:
        # Generic catch - anti-pattern
        return f"Caught unknown exception: {e}"
    finally:
        # Resource cleanup
        pass


def process_data(data: Dict[str, int]) -> int:
    """Main processing function - frequently used."""
    total = 0
    for key, value in data.items():
        if value > 0:
            total += value * 2
    return total


def dead_exception_handler(value: int):
    """Function with dead exception handler."""
    try:
        if value < 0:
            raise ValueError("Negative value")
        return value * 2
    except KeyError:
        # This handler is never triggered (dead code)
        return -1
    except ValueError:
        return 0


def missing_finally_block(resource_id: str) -> str:
    """Function missing finally block for cleanup."""
    try:
        if resource_id == "error":
            raise RuntimeError("Resource error")
        return f"Resource {resource_id} processed"
    except RuntimeError:
        return "Error handled"
    # Missing finally block for cleanup


def nested_try_except():
    """Nested try/except structure."""
    try:
        try:
            value = random.randint(0, 100)
            if value > 50:
                raise ValueError("Value too high")
            return value
        except ValueError:
            raise RuntimeError("Nested error")
    except RuntimeError as e:
        return f"Caught: {e}"


def complex_logic(a: int, b: int) -> int:
    """Function with complex conditional logic."""
    if a > 0:
        if b > 0:
            return a + b
        else:
            return a - b
    else:
        if b > 0:
            return b - a
        else:
            return -(a + b)


def completely_unused():
    """Dead code - completely unused function."""
    x = 1
    y = 2
    z = x + y
    return z


def rarely_used(n: int = 1) -> int:
    """Rarely used function - low execution frequency."""
    result = 1
    for i in range(n):
        result *= (i + 1)
    return result


def main_entry_point():
    """Main entry point that coordinates operations."""

    # This code path is always executed
    results = []

    # Test 1: Simple calculations (always runs)
    for i in range(5):
        result = simple_calculation(i, i + 1)
        results.append(result)

    # Test 2: Calculate averages (always runs)
    numbers = [1, 2, 3, 4, 5]
    avg = calculate_average(numbers)
    results.append(int(avg))

    # Test 3: Validation (always runs)
    for test_val in ["hello", "world", "test"]:
        if validate_input(test_val):
            results.append(1)

    # Test 4: Process data (always runs)
    data = {"a": 10, "b": 20, "c": 30}
    total = process_data(data)
    results.append(total)

    # Test 5: Handle exceptions (always runs)
    for op in ["success", "fail", "timeout"]:
        try:
            handle_exception(op)
        except TimeoutError:
            pass

    # Test 6: Complex logic (always runs)
    for a in [1, -1]:
        for b in [1, -1]:
            complex_logic(a, b)

    # Test 7: Nested try/except (always runs)
    for _ in range(3):
        nested_try_except()

    # Test 8: Retry logic (sometimes runs)
    try:
        for _ in range(2):
            retry_with_backoff(max_retries=2)
    except ConnectionError:
        pass

    # Test 9: Dead handlers (always runs)
    dead_exception_handler(10)
    dead_exception_handler(-10)

    # Test 10: Missing finally (always runs)
    missing_finally_block("good")
    missing_finally_block("error")

    # Test 11: Rarely used functions (sometimes runs)
    if random.random() > 0.8:
        rarely_used(5)

    # Dead code functions never called:
    # - unused_helper()
    # - completely_unused()

    return len(results)


if __name__ == "__main__":
    # Run multiple times to build up execution profile
    for _ in range(10):
        main_entry_point()

    print("✅ Mock app execution complete")
