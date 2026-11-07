"""
Programming Language Code Generation and Execution Built-ins.
Provides templates for languages (Python, C, C++, Java, JavaScript) and seamless compilation/execution.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from shell.builtins.base import BaseBuiltin
from shell.builtins.registry import register_builtin

if TYPE_CHECKING:
    from shell.core.context import ShellContext


CODE_TEMPLATES: Dict[str, Dict[str, Tuple[str, str]]] = {
    # format: {lang: {template_name: (default_filename, code_content)}}
    "python": {
        "add": (
            "add_numbers.py",
            '''"""
Program: Add Two Numbers
Language: Python
"""

def add_numbers(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b

if __name__ == "__main__":
    num1 = 15.5
    num2 = 24.5
    result = add_numbers(num1, num2)
    print("=" * 40)
    print(" Python Addition Program")
    print("=" * 40)
    print(f"Number 1: {num1}")
    print(f"Number 2: {num2}")
    print(f"Result:   {num1} + {num2} = {result}")
    print("=" * 40)
''',
        ),
        "age": (
            "age_validation.py",
            '''"""
Program: Age Validation & Voting Eligibility
Language: Python
"""

def validate_age(age: int) -> bool:
    """Check if a person is an adult (age >= 18)."""
    return age >= 18

if __name__ == "__main__":
    test_ages = [15, 18, 24, 12, 65]
    print("=" * 45)
    print(" Python Age Validation Program")
    print("=" * 45)
    for age in test_ages:
        status = "Eligible (Adult)" if validate_age(age) else "Ineligible (Minor)"
        print(f"  Age {age:>2}: {status}")
    print("=" * 45)
''',
        ),
        "hello": (
            "hello_world.py",
            '''"""
Program: Hello World
Language: Python
"""

if __name__ == "__main__":
    print("Hello from Python in myOS Modular Shell!")
''',
        ),
    },
    "c": {
        "add": (
            "add_numbers.c",
            '''#include <stdio.h>

/* Function to add two integers */
int add_numbers(int a, int b) {
    return a + b;
}

int main(void) {
    int num1 = 15;
    int num2 = 25;
    int sum = add_numbers(num1, num2);

    printf("========================================\\n");
    printf(" C Addition Program\\n");
    printf("========================================\\n");
    printf("Number 1: %d\\n", num1);
    printf("Number 2: %d\\n", num2);
    printf("Result:   %d + %d = %d\\n", num1, num2, sum);
    printf("========================================\\n");
    return 0;
}
''',
        ),
        "age": (
            "age_validation.c",
            '''#include <stdio.h>

/* Function to validate adulthood */
int is_adult(int age) {
    return age >= 18;
}

int main(void) {
    int sample_ages[] = {15, 18, 24, 12, 65};
    int count = sizeof(sample_ages) / sizeof(sample_ages[0]);

    printf("=============================================\\n");
    printf(" C Age Validation Program\\n");
    printf("=============================================\\n");

    for (int i = 0; i < count; i++) {
        int age = sample_ages[i];
        if (is_adult(age)) {
            printf("  Age %2d: Eligible (Adult)\\n", age);
        } else {
            printf("  Age %2d: Ineligible (Minor)\\n", age);
        }
    }
    printf("=============================================\\n");
    return 0;
}
''',
        ),
        "hello": (
            "hello_world.c",
            '''#include <stdio.h>

int main(void) {
    printf("Hello from C in myOS Modular Shell!\\n");
    return 0;
}
''',
        ),
    },
    "cpp": {
        "add": (
            "add_numbers.cpp",
            '''#include <iostream>

int addNumbers(int a, int b) {
    return a + b;
}

int main() {
    int num1 = 20;
    int num2 = 30;
    std::cout << "========================================" << std::endl;
    std::cout << " C++ Addition Program" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Number 1: " << num1 << std::endl;
    std::cout << "Number 2: " << num2 << std::endl;
    std::cout << "Result:   " << num1 << " + " << num2 << " = " << addNumbers(num1, num2) << std::endl;
    std::cout << "========================================" << std::endl;
    return 0;
}
''',
        ),
        "age": (
            "age_validation.cpp",
            '''#include <iostream>
#include <vector>

bool validateAge(int age) {
    return age >= 18;
}

int main() {
    std::vector<int> sampleAges = {15, 18, 24, 12, 65};

    std::cout << "=============================================" << std::endl;
    std::cout << " C++ Age Validation Program" << std::endl;
    std::cout << "=============================================" << std::endl;

    for (int age : sampleAges) {
        std::cout << "  Age " << (age < 10 ? " " : "") << age << ": "
                  << (validateAge(age) ? "Eligible (Adult)" : "Ineligible (Minor)")
                  << std::endl;
    }
    std::cout << "=============================================" << std::endl;
    return 0;
}
''',
        ),
        "hello": (
            "hello_world.cpp",
            '''#include <iostream>

int main() {
    std::cout << "Hello from C++ in myOS Modular Shell!" << std::endl;
    return 0;
}
''',
        ),
    },
    "java": {
        "add": (
            "AddProgram.java",
            '''public class AddProgram {
    public static int add(int a, int b) {
        return a + b;
    }

    public static void main(String[] args) {
        int a = 25;
        int b = 35;
        System.out.println("========================================");
        System.out.println(" Java Addition Program");
        System.out.println("========================================");
        System.out.println("Number 1: " + a);
        System.out.println("Number 2: " + b);
        System.out.println("Result:   " + a + " + " + b + " = " + add(a, b));
        System.out.println("========================================");
    }
}
''',
        ),
        "age": (
            "AgeValidation.java",
            '''public class AgeValidation {
    public static boolean isEligible(int age) {
        return age >= 18;
    }

    public static void main(String[] args) {
        int[] sampleAges = {15, 18, 24, 12, 65};

        System.out.println("=============================================");
        System.out.println(" Java Age Validation Program");
        System.out.println("=============================================");

        for (int age : sampleAges) {
            String status = isEligible(age) ? "Eligible (Adult)" : "Ineligible (Minor)";
            System.out.printf("  Age %2d: %s%n", age, status);
        }
        System.out.println("=============================================");
    }
}
''',
        ),
        "hello": (
            "HelloProgram.java",
            '''public class HelloProgram {
    public static void main(String[] args) {
        System.out.println("Hello from Java in myOS Modular Shell!");
    }
}
''',
        ),
    },
    "javascript": {
        "add": (
            "add_numbers.js",
            '''/**
 * Program: Add Two Numbers
 * Language: JavaScript (Node.js)
 */

function addNumbers(a, b) {
    return a + b;
}

const num1 = 18;
const num2 = 32;
console.log("========================================");
console.log(" JavaScript Addition Program");
console.log("========================================");
console.log(`Number 1: ${num1}`);
console.log(`Number 2: ${num2}`);
console.log(`Result:   ${num1} + ${num2} = ${addNumbers(num1, num2)}`);
console.log("========================================");
''',
        ),
        "age": (
            "age_validation.js",
            '''/**
 * Program: Age Validation & Voting Eligibility
 * Language: JavaScript (Node.js)
 */

function validateAge(age) {
    return age >= 18;
}

const sampleAges = [15, 18, 24, 12, 65];
console.log("=============================================");
console.log(" JavaScript Age Validation Program");
console.log("=============================================");

sampleAges.forEach(age => {
    const status = validateAge(age) ? "Eligible (Adult)" : "Ineligible (Minor)";
    console.log(`  Age ${String(age).padStart(2, ' ')}: ${status}`);
});
console.log("=============================================");
''',
        ),
        "hello": (
            "hello_world.js",
            '''console.log("Hello from JavaScript in myOS Modular Shell!");
''',
        ),
    },
}

# Aliases for languages
LANG_ALIASES = {
    "py": "python",
    "python": "python",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "java": "java",
    "js": "javascript",
    "javascript": "javascript",
    "node": "javascript",
}


@register_builtin
class TemplateBuiltin(BaseBuiltin):
    """
    Builtin to scaffold and write predefined programming code templates.
    """

    @property
    def name(self) -> str:
        return "template"

    @property
    def aliases(self) -> List[str]:
        return ["codegen"]

    @property
    def description(self) -> str:
        return "Create source code files with predefined templates (add, age, hello)."

    @property
    def usage(self) -> str:
        return "template [list | create <language> <add|age|hello> [filename]]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args or args[0] in ("list", "--list", "-l"):
            return self._list_templates(context)

        subcommand = args[0]
        if subcommand == "create":
            if len(args) < 3:
                self.write_err(context, "template create: usage: template create <lang> <add|age|hello> [filename]\n")
                return 1

            lang_raw = args[1].lower()
            lang = LANG_ALIASES.get(lang_raw)
            if not lang or lang not in CODE_TEMPLATES:
                self.write_err(context, f"template: unsupported language '{lang_raw}'. Supported: {', '.join(sorted(set(LANG_ALIASES.values())))}\n")
                return 1

            tmpl_type = args[2].lower()
            available_tmpls = CODE_TEMPLATES[lang]
            if tmpl_type not in available_tmpls:
                self.write_err(context, f"template: unknown template '{tmpl_type}'. Available: {', '.join(available_tmpls.keys())}\n")
                return 1

            default_name, code = available_tmpls[tmpl_type]
            target_filename = args[3] if len(args) > 3 else default_name
            target_path = (context.cwd / target_filename).resolve()

            try:
                target_path.write_text(code, encoding="utf-8")
                self.write(context, f"[Success] Created {lang.capitalize()} '{tmpl_type}' program at: {target_filename}\n")
                self.write(context, f"Execute it using: runcode \"{target_filename}\"\n")
                return 0
            except OSError as e:
                self.write_err(context, f"template: error writing file '{target_filename}': {e}\n")
                return 1

        self.write_err(context, f"template: unknown subcommand '{subcommand}'. Use 'template list'.\n")
        return 1

    def _list_templates(self, context: ShellContext) -> int:
        self.write(context, "\nAvailable Code Templates:\n")
        self.write(context, "=" * 60 + "\n")
        self.write(context, f"{'LANGUAGE':<15} {'TEMPLATE':<15} {'DEFAULT FILE':<25}\n")
        self.write(context, "-" * 60 + "\n")

        for lang, tmpls in sorted(CODE_TEMPLATES.items()):
            for tmpl, (fname, _) in sorted(tmpls.items()):
                self.write(context, f"{lang:<15} {tmpl:<15} {fname:<25}\n")

        self.write(context, "=" * 60 + "\n")
        self.write(context, "Usage: template create <language> <template> [filename]\n")
        self.write(context, "Example: template create python age age_checker.py\n\n")
        return 0


@register_builtin
class RunCodeBuiltin(BaseBuiltin):
    """
    Builtin to compile and execute source code files across supported programming languages.
    """

    @property
    def name(self) -> str:
        return "runcode"

    @property
    def aliases(self) -> List[str]:
        return ["compile"]

    @property
    def description(self) -> str:
        return "Compile and execute code files (Python, C, C++, Java, JavaScript)."

    @property
    def usage(self) -> str:
        return "runcode <filename> [args...]"

    def execute(self, args: List[str], context: ShellContext) -> int:
        if not args:
            self.write_err(context, "runcode: missing filename operand\n")
            return 1

        filename = args[0]
        exec_args = args[1:]
        resolved_path = (context.cwd / filename).resolve()

        if not resolved_path.exists():
            self.write_err(context, f"runcode: file not found: '{filename}'\n")
            return 1

        ext = resolved_path.suffix.lower()

        if ext == ".py":
            return self._run_python(resolved_path, exec_args, context)
        elif ext == ".c":
            return self._run_c(resolved_path, exec_args, context)
        elif ext in (".cpp", ".cc", ".cxx"):
            return self._run_cpp(resolved_path, exec_args, context)
        elif ext == ".java":
            return self._run_java(resolved_path, exec_args, context)
        elif ext == ".js":
            return self._run_javascript(resolved_path, exec_args, context)
        else:
            self.write_err(context, f"runcode: unsupported file extension '{ext}'. Supported: .py, .c, .cpp, .java, .js\n")
            return 1

    def _run_python(self, file_path: Path, args: List[str], context: ShellContext) -> int:
        self.write(context, f"[Executing Python] {file_path.name}...\n")
        cmd = [sys.executable, str(file_path)] + args
        return self._spawn_process(cmd, context)

    def _run_javascript(self, file_path: Path, args: List[str], context: ShellContext) -> int:
        node_bin = shutil.which("node")
        if not node_bin:
            self.write_err(context, "runcode: Node.js ('node') runtime not found in PATH.\n")
            return 127
        self.write(context, f"[Executing JavaScript] {file_path.name}...\n")
        cmd = [node_bin, str(file_path)] + args
        return self._spawn_process(cmd, context)

    def _run_c(self, file_path: Path, args: List[str], context: ShellContext) -> int:
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.write_err(context, "runcode: C compiler ('gcc' or 'clang') not found in PATH.\n")
            return 127

        out_bin = file_path.with_suffix(".exe" if os.name == "nt" else "")
        self.write(context, f"[Compiling C] {file_path.name} -> {out_bin.name}...\n")

        compile_proc = subprocess.run(
            [compiler, str(file_path), "-o", str(out_bin)],
            cwd=str(context.cwd),
            text=True,
            capture_output=True,
        )
        if compile_proc.returncode != 0:
            self.write_err(context, f"[Compilation Failed]:\n{compile_proc.stderr}\n")
            return compile_proc.returncode

        self.write(context, f"[Running Executable] {out_bin.name}...\n")
        return self._spawn_process([str(out_bin)] + args, context)

    def _run_cpp(self, file_path: Path, args: List[str], context: ShellContext) -> int:
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            self.write_err(context, "runcode: C++ compiler ('g++' or 'clang++') not found in PATH.\n")
            return 127

        out_bin = file_path.with_suffix(".exe" if os.name == "nt" else "")
        self.write(context, f"[Compiling C++] {file_path.name} -> {out_bin.name}...\n")

        compile_proc = subprocess.run(
            [compiler, str(file_path), "-o", str(out_bin)],
            cwd=str(context.cwd),
            text=True,
            capture_output=True,
        )
        if compile_proc.returncode != 0:
            self.write_err(context, f"[Compilation Failed]:\n{compile_proc.stderr}\n")
            return compile_proc.returncode

        self.write(context, f"[Running Executable] {out_bin.name}...\n")
        return self._spawn_process([str(out_bin)] + args, context)

    def _run_java(self, file_path: Path, args: List[str], context: ShellContext) -> int:
        javac = shutil.which("javac")
        java = shutil.which("java")
        if not javac or not java:
            self.write_err(context, "runcode: Java SDK ('javac'/'java') not found in PATH.\n")
            return 127

        self.write(context, f"[Compiling Java] {file_path.name}...\n")
        compile_proc = subprocess.run(
            [javac, str(file_path)],
            cwd=str(context.cwd),
            text=True,
            capture_output=True,
        )
        if compile_proc.returncode != 0:
            self.write_err(context, f"[Compilation Failed]:\n{compile_proc.stderr}\n")
            return compile_proc.returncode

        class_name = file_path.stem
        self.write(context, f"[Running Java Class] {class_name}...\n")
        return self._spawn_process([java, class_name] + args, context)

    def _spawn_process(self, cmd: List[str], context: ShellContext) -> int:
        """Spawn process and stream its output live into context stdout/stderr."""
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(context.cwd),
                text=True,
                errors="replace",
            )
            stdout_data, stderr_data = proc.communicate()
            if stdout_data:
                self.write(context, stdout_data)
            if stderr_data:
                self.write_err(context, stderr_data)
            return proc.returncode
        except Exception as e:
            self.write_err(context, f"runcode: execution error: {e}\n")
            return 1
