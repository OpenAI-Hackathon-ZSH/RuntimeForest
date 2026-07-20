"""
Multi-path mock application for testing different execution frequencies.

This app has:
1. Frequently used paths (high frequency)
2. Sometimes used paths (medium frequency)
3. Rarely used paths (low frequency)
4. Never used paths (frequency = 0)
"""

import random


# ============================================================================
# FREQUENTLY USED (Should have high frequency)
# ============================================================================

def main_loop():
    """Always executed in every test run."""
    return "main"


def core_operation():
    """Core functionality - used by main."""
    total = 0
    for i in range(10):
        total += i
    return total


def validate_input(data):
    """Validation - used in most paths."""
    return data is not None and len(data) > 0


# ============================================================================
# SOMETIMES USED (Should have medium frequency - ~50% of the time)
# ============================================================================

def feature_alpha():
    """Used when random() > 0.5."""
    result = []
    for i in range(5):
        result.append(i * 2)
    return result


def feature_beta():
    """Used when random() <= 0.5."""
    data = {}
    for key in ["a", "b", "c"]:
        data[key] = random.randint(1, 100)
    return data


def error_handling_path(mode):
    """Used in some error cases."""
    try:
        if mode == "error":
            raise ValueError("Test error")
        return f"Success: {mode}"
    except ValueError:
        return "Error caught"


# ============================================================================
# RARELY USED (Should have low frequency - ~10% of the time)
# ============================================================================

def special_mode():
    """Only used when random() > 0.9."""
    return "special"


def debug_function():
    """Only called in debug mode (~10% chance)."""
    print("Debug info")
    return True


def fallback_logic():
    """Fallback for rare cases."""
    return "fallback"


# ============================================================================
# NEVER USED (Should have frequency = 0)
# ============================================================================

def unused_function_1():
    """This function is never called."""
    return "unused1"


def unused_function_2():
    """This function is never called."""
    return "unused2"


def completely_dead():
    """Dead code - should be deleted."""
    x = 1
    y = 2
    return x + y


def never_executed():
    """Another dead function."""
    for i in range(100):
        pass
    return "never"


# ============================================================================
# BRANCHING LOGIC - Different paths taken different numbers of times
# ============================================================================

def branching_logic(value):
    """
    Different branches taken different number of times:
    - if value > 50: taken 60 times
    - elif value > 25: taken 30 times
    - else: taken 10 times
    """
    if value > 50:
        return "high"  # Frequent path
    elif value > 25:
        return "medium"  # Medium path
    else:
        return "low"  # Rare path


def conditional_feature(flag):
    """
    One branch always used, one branch never used:
    - if flag: taken every time (frequency = N)
    - else: never taken (frequency = 0)
    """
    if flag:
        return feature_alpha()
    else:
        return unused_function_1()  # Dead path!


# ============================================================================
# EXCEPTION HANDLING - Some handlers never triggered
# ============================================================================

def exception_handler(exception_type):
    """
    Some exception handlers are triggered, others never:
    """
    try:
        if exception_type == "value_error":
            raise ValueError("value error")
        elif exception_type == "key_error":
            raise KeyError("key error")
        elif exception_type == "type_error":
            raise TypeError("type error")
        return "no error"
    except ValueError:
        return "caught value error"  # Triggered sometimes
    except KeyError:
        return "caught key error"  # Triggered sometimes
    except TypeError:
        return "caught type error"  # NEVER triggered (dead handler)


# ============================================================================
# LOOPS - Some iterations never executed
# ============================================================================

def loop_with_break():
    """
    Loop that sometimes breaks early:
    - Usually iterates 5 times
    - Rarely breaks at 2
    """
    for i in range(5):
        if i == 2 and random.random() > 0.95:
            break  # Rarely taken path (frequency ~ 1-2)
        result = i * 2
    return result


def empty_loop():
    """
    Loop that is never executed.
    """
    for i in range(100):  # Never entered
        result = i
    return result


# ============================================================================
# MAIN TEST FLOW
# ============================================================================

def run_simulation(num_iterations=100):
    """
    Run simulation showing different execution frequencies.

    Expected frequencies:
    - main_loop: 100 (always called)
    - core_operation: 100 (always called)
    - validate_input: 100 (always called)
    - feature_alpha: ~50 (called 50% of time)
    - feature_beta: ~50 (called 50% of time)
    - special_mode: ~10 (called 10% of time)
    - debug_function: ~10 (called 10% of time)
    - exception_handler with "value_error": ~25
    - exception_handler with "key_error": ~25
    - exception_handler with "type_error": 0 (NEVER called)
    - unused_function_1: 0 (NEVER called)
    - unused_function_2: 0 (NEVER called)
    - completely_dead: 0 (NEVER called)
    - never_executed: 0 (NEVER called)
    """

    for iteration in range(num_iterations):
        # Always executed
        main_loop()
        core_operation()
        validate_input("test")

        # Sometimes executed (~50%)
        if random.random() > 0.5:
            feature_alpha()
        else:
            feature_beta()

        # Rarely executed (~10%)
        if random.random() > 0.9:
            special_mode()
            debug_function()

        # Different branching
        value = random.randint(0, 100)
        branching_logic(value)

        # Conditional with dead branch
        conditional_feature(True)  # Never executes else branch

        # Exception handling
        exception_mode = random.choice(["none", "value", "key"])
        if exception_mode == "value":
            exception_handler("value_error")
        elif exception_mode == "key":
            exception_handler("key_error")
        else:
            exception_handler("none")
        # Note: type_error NEVER called, so handler is dead

        # Loop with break
        loop_with_break()

        # Dead code never called:
        # - unused_function_1()
        # - unused_function_2()
        # - completely_dead()
        # - never_executed()
        # - exception_handler("type_error") - handler is dead


if __name__ == "__main__":
    print("Running multi-path simulation...")
    print("This will show different execution frequencies:")
    print("")
    print("HIGH frequency (100):")
    print("  - main_loop")
    print("  - core_operation")
    print("  - validate_input")
    print("")
    print("MEDIUM frequency (~50):")
    print("  - feature_alpha")
    print("  - feature_beta")
    print("")
    print("LOW frequency (~10-25):")
    print("  - special_mode")
    print("  - debug_function")
    print("  - exception_handler (for value/key errors)")
    print("")
    print("ZERO frequency (DEAD CODE):")
    print("  - unused_function_1")
    print("  - unused_function_2")
    print("  - completely_dead")
    print("  - never_executed")
    print("  - exception_handler with type_error (dead handler)")
    print("  - conditional_feature else branch (dead branch)")
    print("")

    run_simulation(100)
    print("\n✅ Simulation complete")
