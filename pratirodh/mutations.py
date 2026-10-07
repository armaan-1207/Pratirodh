"""Conservative structural adapters for reviewed fixture mutation families.

Constructing a mutant never qualifies it: the engine must still observe the
contract's unsafe witness and preserve every legitimate-use case.
"""
import ast


def construct(source, mutation, cwe):
    if source.count(mutation['find']) == 1:
        return source.replace(mutation['find'], mutation['replace'], 1), 'exact-source'
    reviewed = {
        'containment-weakened': ('if not requested.is_relative_to(root):', "if '..' in name:"),
        'canonicalization-removed': ('requested = (root / name).resolve()', 'requested = (root / name).absolute()'),
    }
    if cwe != 'CWE-22' or reviewed.get(mutation['family']) != (mutation['find'], mutation['replace']):
        return None, 'unavailable'
    tree = ast.parse(source)
    # Accept one explicit Path containment guard, in either polarity. Refuse
    # multiple guards, compound expressions or unknown argument shapes.
    guards = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test.operand if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not) else node.test
        if (isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute)
                and test.func.attr == 'is_relative_to' and isinstance(test.func.value, ast.Name)
                and len(test.args) == 1 and isinstance(test.args[0], ast.Name) and not test.keywords):
            guards.append((node, test))
    if len(guards) != 1:
        return None, 'unavailable'
    guard, call = guards[0]
    if mutation['family'] == 'containment-weakened':
        # Disable only this containment predicate, preserving branch polarity.
        guard.test = ast.Constant(value=not isinstance(guard.test, ast.UnaryOp))
    else:
        assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                       and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id == call.func.value.id]
        if len(assignments) != 1:
            return None, 'unavailable'
        value = assignments[0].value
        if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                and value.func.attr == 'resolve' and not value.args and not value.keywords):
            return None, 'unavailable'
        value.func.attr = 'absolute'
    return ast.unparse(ast.fix_missing_locations(tree)) + '\n', 'reviewed-python-path-ast-v1'
