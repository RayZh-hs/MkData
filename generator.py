from random import randint
import pyperclip
import re
import os
import logging
from ast import literal_eval

_gen_path = os.path.abspath(os.path.dirname(__file__))+"\\templates\\"
_gen_path+= "P1135.gen"
_gen_builtin_locals = locals()
_gen_logger = logging.getLogger("generator")
_gen_buffer = ""

# + util funcs +
def _gen_assign(_gen_var: str, _gen_val: any) -> None:
    """
    assign a value to a variable in the local scope
    """
    _gen_builtin_locals[_gen_var] = _gen_val

def _gen_runeval(_gen_exp: str) -> any:
    """
    run a python expression and return its value
    """
    try:
        return eval(_gen_exp)
    except Exception as e:
        _gen_logger.error("Failed to run the python expression.")
        _gen_logger.error("> "+_gen_exp)
        exit(0)

# + parser funcs +
def _gen_gettype(_gen_from: str) -> str:
    """
    locates the type of the output in a given line _gen_from
    
    the type takes shape of [...] in the line
    """
    _gen_re_found = re.findall(r"\[.{1,}\]", _gen_from)
    if(len(_gen_re_found)==0):
        _gen_logger.warning("No type found in the line.")
        _gen_logger.warning("> "+_gen_from)
        return None
    if(len(_gen_re_found)>1):
        _gen_logger.error("A single varibale can only have one type.")
        _gen_logger.error("> "+_gen_from)
        exit(0)
    return _gen_re_found[0][1:-1]

def _gen_getassert(_gen_from: str) -> str:
    # assertions take shape of @...@, within which is a python expression
    _gen_re_found = re.findall(r"@.{1,}@", _gen_from)
    if(len(_gen_re_found)==0):
        return None
    return _gen_re_found[-1][1:-1]

def _gen_getvarname(_gen_from: str) -> str:
    # the variable name is either undefined or the first word in the line
    # it is followed by the type
    _gen_re_found = re.findall(r".{0,}\[", _gen_from)
    if(len(_gen_re_found)==0):
        return None # undefined
    _gen_re_found = _gen_re_found[0]
    _gen_re_found = re.sub(r"[\W_]+", "", _gen_re_found)
    if(_gen_re_found[0:4]=='_gen'):
        _gen_logger.error("Variable names cannot start with '_gen'.")
        _gen_logger.error("> "+_gen_from)
        exit(0)
    return _gen_re_found

def _gen_getconstraints(_gen_from: str) -> str:
    # constraints are in the form of (...), within which are constraints
    _gen_re_found = re.findall(r"\(.{1,}\)", _gen_from)
    if(len(_gen_re_found)==0):
        return None
    return _gen_re_found[-1][1:-1]

def _gen_getsuffix(_gen_from: str) -> str:
    # suffixes are in the form of $..., where the '...' stands for a single char (default to $\n)
    _gen_re_found = re.findall(r"\$.{0,}", _gen_from)
    if(len(_gen_re_found)==0):
        return ' '
    _gen_re_found = _gen_re_found[-1]
    _gen_re_found = _gen_re_found[1:]
    if(len(_gen_re_found)==0):
        return '\n'
    # _gen_re_found = repr(_gen_re_found)
    _gen_re_found = literal_eval(f"'{_gen_re_found}'")
    return _gen_re_found

# + generator sections +
def _gen_process(copy_to_clipboard:bool=True, path:str=_gen_path) -> str:
    global _gen_logger, _gen_buffer, _gen_builtin_locals
    logging.basicConfig(level=logging.DEBUG)
    with open(path, 'r', encoding='utf-8') as _gen_file:
        _gen_logger.debug(f"File {path} opened.")
        _gen_lines = _gen_file.readlines()

    _gen_lines = [line.strip('\n') for line in _gen_lines]
    
    while(len(_gen_lines)>0 and _gen_lines[0] != '#begin'):
        _gen_lines.pop(0)
    
    if len(_gen_lines) == 0:
        _gen_logger.warning("No #begin tag found.")
        _gen_logger.warning("Program will exit.")
        exit(0)
    
    _gen_logger.info("#begin tag found.")
    # + main entrance +
    _gen_lines.pop(0)
    while(len(_gen_lines)>0 and _gen_lines[0] != '#end'):
        _gen_front = _gen_lines[0]
        _gen_type = _gen_gettype(_gen_front)
        _gen_logger.debug("Identified generator type: "+_gen_type)
        if(_gen_type == None):
            pass # just pass over this line
        elif(_gen_type == "int"):
            _gen_var_val = 0
            # check whether to reassign the variable
            _gen_var_name = _gen_getvarname(_gen_front)
            # check whether to assert the variable
            _gen_var_assert = _gen_getassert(_gen_front)
            if(_gen_var_assert != None):
                _gen_var_val = _gen_runeval(_gen_var_assert)
            else:
                # find constraints where assertions aren't present
                _gen_var_constraints = _gen_getconstraints(_gen_front)
                if(_gen_var_constraints != None):
                    # the constraint for an int should be in the form of (exp1,exp2)
                    _gen_var_constraints = _gen_var_constraints.split(",")
                    _gen_var_val = randint(int(_gen_runeval(_gen_var_constraints[0])), int(_gen_runeval(_gen_var_constraints[1])))
            # whatever the path, render to buffer and (maybe) assign to local scope
            _gen_buffer += (str(_gen_var_val) + _gen_getsuffix(_gen_front))
            _gen_logger.info(f"Suceessfully generated [int]: {_gen_var_val}.")
            if _gen_var_name != None:
                _gen_assign(_gen_var_name, _gen_var_val)
                _gen_logger.info(f"Assigned to local scope: {_gen_var_name} = {_gen_var_val}.")
        elif(_gen_type[0:7] == "intlist"):
            # the type should be in the form of [intlist n], where n(an expression) is the length of the list
            # first find the length of the list
            _gen_var_len = _gen_type[8:]
            _gen_var_len = _gen_runeval(_gen_var_len)
            # then assign the values to the list
            _gen_var_val = []
            _gen_var_name = _gen_getvarname(_gen_front)
            _gen_var_assert = _gen_getassert(_gen_front)
            if(_gen_var_assert != None):
                # using assertions, the user must match the length of the list to his/her input
                _gen_var_val = _gen_runeval(_gen_var_assert)
            else:
                # otherwise, constraints are used to determine the values of the list
                _gen_var_constraints = _gen_getconstraints(_gen_front)
                if(_gen_var_constraints != None):
                    _gen_var_constraints = _gen_var_constraints.split(",")
                    for i in range(_gen_var_len):
                        _gen_var_val.append(randint(int(_gen_runeval(_gen_var_constraints[0])), int(_gen_runeval(_gen_var_constraints[1]))))
            # compare the length of the list to the length of the values
            if(len(_gen_var_val) != _gen_var_len):
                _gen_logger.error("The length of the list does not match the length of the values constructed bby the line.")
                _gen_logger.error("> "+_gen_front)
                exit(0)
            # render to buffer
            _gen_buffer += (" ".join([str(i) for i in _gen_var_val]) + _gen_getsuffix(_gen_front))
            _gen_logger.info(f"Suceessfully generated [intlist]: {_gen_var_val}.")
            # no need to assign to local scope since this is a list
        elif(_gen_type == "intmatrix"):
            ...
        elif(_gen_type == "str"):
            ...
        elif(_gen_type == "strlist"):
            ...
        
        _gen_lines.pop(0)
    if(copy_to_clipboard):
        pyperclip.copy(_gen_buffer)
        _gen_logger.info("Buffer copied to clipboard.")
    return _gen_buffer

if __name__ == "__main__":
    _gen_process()