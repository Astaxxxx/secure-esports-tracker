import os

directories = [
    "tests",
    "tests/security_tests",
    "tests/mqtt_tests",
    "tests/data_tests"
]

def main():
    print("Creating __init__.py files in test directories...")
    
    for directory in directories:

        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# This file makes the directory a Python package\n")
            print(f"Created {init_file}")
        else:
            print(f"{init_file} already exists")

if __name__ == "__main__":
    main()