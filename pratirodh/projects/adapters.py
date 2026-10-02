"""Explicit adapters share the worker protocol; no host build fallback."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Adapter:
    name: str
    identity: str
    static: tuple
    fuzz_tool: str
    formal_tool: str

    def inspect(self, files):
        if self.name == 'node' and not {'package.json', 'package-lock.json'} <= files.keys():
            raise ValueError('Node projects require package.json and package-lock.json')
        if self.name == 'cpp' and 'CMakeLists.txt' not in files:
            raise ValueError('C/C++ requires CMake/CTest')
        if self.name == 'python' and not any(n.endswith('.py') for n in files):
            raise ValueError('Python source missing')

    def build(self, manifest):
        return manifest['commands']['build']

    def baseline(self, manifest):
        return manifest['commands']['test']


ADAPTERS = {
    'python': Adapter('python', 'python-pytest-v2', ('python', '-m', 'bandit', '-q', '-f', 'json', '-r', '.'), 'atheris', 'crosshair'),
    'node': Adapter('node', 'node-npm-typescript-v2', (), 'jazzer.js', ''),
    'cpp': Adapter('cpp', 'clang-cmake-ctest-v2', (), 'libFuzzer+ASan+UBSan', 'cbmc'),
}
