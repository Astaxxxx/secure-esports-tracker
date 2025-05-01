import os
import sys
import unittest
import logging
import importlib.util

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_runner')

def is_package(directory):
    init_path = os.path.join(directory, "__init__.py")
    return os.path.isfile(init_path)

def create_init_file(directory):
    init_path = os.path.join(directory, "__init__.py")
    try:
        with open(init_path, 'w') as f:
            f.write("# This file makes the directory a Python package\n")
        logger.info(f"Created missing __init__.py in {directory}")
        return True
    except Exception as e:
        logger.error(f"Failed to create __init__.py in {directory}: {e}")
        return False

def run_tests():

    if "" not in sys.path:
        sys.path.insert(0, "")

    test_dirs = [
        'tests/security_tests',
        'tests/mqtt_tests',
        'tests/data_tests'
    ]

    for test_dir in test_dirs:
        if os.path.exists(test_dir) and not is_package(test_dir):
            logger.warning(f"Missing __init__.py in {test_dir}")
            create_init_file(test_dir)

    test_suite = unittest.TestSuite()
    test_loader = unittest.defaultTestLoader

    for test_dir in test_dirs:
        try:
            if os.path.exists(test_dir):
                if not is_package(test_dir):
                    logger.warning(f"{test_dir} is not a valid package, skipping")
                    continue
                tests = test_loader.discover(test_dir, pattern='test_*.py')
                test_suite.addTests(tests)
                logger.info(f"Discovered tests in {test_dir}")
            else:
                logger.warning(f"Test directory not found: {test_dir}")
        except Exception as e:
            logger.error(f"Error discovering tests in {test_dir}: {e}")
            if os.path.exists(test_dir):
                for file in os.listdir(test_dir):
                    if file.startswith('test_') and file.endswith('.py'):
                        try:
                            module_name = os.path.splitext(file)[0]
                            module_path = os.path.join(test_dir, file)
                            
                            spec = importlib.util.spec_from_file_location(module_name, module_path)
                            if spec:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)

                                module_tests = test_loader.loadTestsFromModule(module)
                                test_suite.addTests(module_tests)
                                logger.info(f"Added tests from {module_path}")
                        except Exception as module_err:
                            logger.error(f"Error loading {module_path}: {module_err}")

    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)

    print("\n====== TEST SUMMARY ======")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print("\n------ FAILURES ------")
        for test, traceback in result.failures:
            print(f"\n{test}")
            print(f"{traceback}")
    
    if result.errors:
        print("\n------ ERRORS ------")
        for test, traceback in result.errors:
            print(f"\n{test}")
            print(f"{traceback}")

    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    print("Running all unit tests for Secure Esports Equipment Performance Tracker")

    if not is_package("tests"):
        create_init_file("tests")
    
    success = run_tests()
    sys.exit(0 if success else 1)