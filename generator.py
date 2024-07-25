from random import randint
import pyperclip
import re
import os
import logging
from ast import literal_eval

_gen_path = os.path.abspath(os.path.dirname(__file__))+"\\templates\\"
_gen_path+= "Demo_01.gen"
_gen_compact_length = 80
_gen_builtin_locals = locals()
_gen_logger = logging.getLogger("generator")
_gen_buffer = ""

# + util funcs +
def _gen_preprocess_path(_gen_name: str) -> str:
    """
    preprocess the path to the template file

    the path should be in the form of "templates/P1125.gen"
    """
    return os.path.abspath(os.path.dirname(__file__))+"\\templates\\"+_gen_name

def _gen_assign(_gen_var: str, _gen_val: any) -> None:
    """
    assign a value to a variable in the local scope
    """
    _gen_builtin_locals[_gen_var] = _gen_val

def _gen_runeval(_gen_exp: str, localsdict:str|None=None) -> any:
    """
    run a python expression and return its value
    """
    try:
        return eval(_gen_exp, globals(), localsdict)
    except Exception as e:
        _gen_logger.error("Failed to run the python expression.")
        _gen_logger.error("> "+_gen_exp)
        exit(0)

def _gen_split_and_run(_gen_exp: str, _gen_sep: str, _gen_maxsplit:int=-1) -> None|tuple:
    """
    split a string by a separator and run each part as a python expression

    returns a tuple of the results
    """
    if not _gen_exp.__contains__(_gen_sep):
        return None
    _gen_exp = _gen_exp.split(_gen_sep, maxsplit=_gen_maxsplit)
    _gen_exp = tuple([_gen_runeval(i) for i in _gen_exp])
    return _gen_exp

def _gen_pack_str(_gen_str: str, length:int=_gen_compact_length) -> str:
    """
    compact a string to a maximum fixed length
    """
    _gen_str = _gen_str.strip()
    if(len(_gen_str) > length):
        _gen_str = _gen_str[0:length-3]+"..."
    return _gen_str

# + parser funcs +
def _gen_gettype(_gen_from: str) -> str:
    """
    locates the type of the output in a given line _gen_from
    
    the type takes shape of [...] in the line
    """
    _gen_re_found = re.findall(r"\[.{1,}?\]", _gen_from)
    if(len(_gen_re_found)==0):
        _gen_logger.warning("No type found in the line.")
        _gen_logger.warning("> "+_gen_from)
        return None
    if(len(_gen_re_found)>1):
        _gen_logger.warning("Multiple []s are identified in this line.")
        _gen_logger.warning("> "+_gen_from)
        _gen_logger.warning("Please make sure you know what you are doing.")
    # if used correctly, only the first [] is the type
    # other []s are used in python expressions
    return _gen_re_found[0][1:-1]

def _gen_getassert(_gen_from: str) -> str:
    """
    finds the assertion in a given line _gen_from

    an `assertion` overrides every other expression in the line; 
    it takes shape of @...@, within which is a python expression

    for lists,  single asserts @...@ determine each element;
                double asserts @@...@@ determine the entire list/matrix
    """
    # assertions take shape of @...@, within which is a python expression
    _gen_re_found = re.findall(r"\@.{1,}\@", _gen_from)
    if(len(_gen_re_found)==0):
        return None
    return _gen_re_found[-1][1:-1]

def _gen_getvarname(_gen_from: str) -> str:
    """
    fetches the variable name in a given line _gen_from

    if the variable is undefined, return None
    """
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

def _gen_getrange(_gen_from: str, enforce_heading:bool=False) -> str:
    """
    identifies a range obj in _gen_from

    ranges are in the form of (... , ...), within which are two python expressions determining the lower and upper bounds
    """
    _gen_re_found = re.findall(r"^[ ]*\(.{1,}\)" if enforce_heading else r"\(.{1,}\)", _gen_from)
    if(len(_gen_re_found)==0):
        return None
    return _gen_re_found[-1][1:-1]

def _gen_getsuffix(_gen_from: str) -> str:
    """
    identifies the suffix of the output in the line_gen_from

    suffixes are in the form of $..., where the '...' stands for the char(s) to be appended to the output

    returns the suffix according to various senarios

    - without $, the default suffix is ' '
    - with $, the default suffix is '\n', so '$' is the same as '$\n'
    """
    _gen_re_found = re.findall(r"\$.{0,}", _gen_from)
    if(len(_gen_re_found)==0):
        return ' '
    # there may be $ flags in [] to indicate \n
    # the suffix is the last $ flag
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
    _gen_buffer = ""
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
        
        # * None: pass over this line
        if(_gen_type == None):
            pass # just pass over this line
        
        # * int: generate a random integer 
        elif(_gen_type == "int"):
            _gen_var_val = 0
            # check whether to reassign the variable
            _gen_var_name = _gen_getvarname(_gen_front)
            # check whether to assert the variable
            _gen_var_assert = _gen_getassert(_gen_front)
            if(_gen_var_assert != None):
                _gen_var_val = _gen_runeval(_gen_var_assert)
            else:
                # find ranges where assertions aren't present
                # changed
                _gen_front = _gen_front[_gen_front.find("]")+1:]
                _gen_var_constraints = _gen_getrange(_gen_front)
                if(_gen_var_constraints != None):
                    # the range for an int should be in the form of (exp1,exp2)
                    # -- _gen_var_constraints = _gen_var_constraints.split(",")
                    # -- _gen_var_val = randint(int(_gen_runeval(_gen_var_constraints[0])), int(_gen_runeval(_gen_var_constraints[1])))
                    _gen_var_val = randint(*_gen_split_and_run(_gen_var_constraints, ","))
            # whatever the path, render to buffer and (maybe) assign to local scope
            _gen_buffer += (str(_gen_var_val) + _gen_getsuffix(_gen_front))
            _gen_logger.info(f"Suceessfully generated [int]: {_gen_var_val}.")
            if _gen_var_name != None:
                _gen_assign(_gen_var_name, _gen_var_val)
                _gen_logger.info(f"Assigned to local scope: {_gen_var_name} = {_gen_var_val}.")

        # * intlist: generate a list of random integers
        elif(_gen_type[0:7] == "intlist"):
            # the type should be in the form of [intlist n], where n(an expression) is the length of the list
            # first find the length of the list
            _gen_list_endl = _gen_type.__contains__("$")
            _gen_type = re.sub(r"\$", "", _gen_type)
            _gen_var_len = _gen_type[8:]
            if(_gen_rng:=_gen_getrange(_gen_var_len)) != None:
                _gen_var_len = randint(*_gen_split_and_run(_gen_rng, ","))
            else:
                _gen_var_len = _gen_runeval(_gen_var_len)
            # then assign the values to the list
            _gen_var_val = []
            _gen_var_name = _gen_getvarname(_gen_front)
            _gen_var_assert = _gen_getassert(_gen_front)
            if(_gen_var_assert != None):
                # check for double assertions
                _gen_var_assert = _gen_var_assert.strip()
                if(_gen_var_assert[0]=='@' and _gen_var_assert[-1]=='@'):
                    # using double assertions, the user must match the length of the list to his/her input
                    _gen_var_val = _gen_runeval(_gen_var_assert.strip('@'))
                else:
                    # single assertions
                    for i in range(_gen_var_len):
                        _gen_var_val.append(_gen_runeval(_gen_var_assert, localsdict={'i': i}))
            else:
                # otherwise, ranges are used to determine the values of the list
                _gen_front = _gen_front[_gen_front.find("]")+1:]
                _gen_var_constraints = _gen_getrange(_gen_front)
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
            _gen_buffer += (("\n" if _gen_list_endl else " ").join([str(i) for i in _gen_var_val]) + _gen_getsuffix(_gen_front))
            _gen_logger.info(_gen_pack_str(f"Suceessfully generated [intlist]: {_gen_var_val}."))
            if(_gen_var_name != None):
                _gen_assign(_gen_var_name, _gen_var_val)
                _gen_logger.info(_gen_pack_str(f"Assigned to local scope: {_gen_var_name} = {_gen_var_val}."))
        
        # * intmatrix: generate a matrix of random integers
        elif(_gen_type[0:9] == "intmatrix"):
            # the type should be in the form of [intmatrix n,m], where n and m are the dimensions of the matrix
            # first find the dimensions of the matrix
            _gen_var_dims = _gen_type[10:]
            _gen_var_dims = _gen_split_and_run(_gen_var_dims, ",")
            # then assign the values to the matrix
            _gen_var_val = []
            _gen_var_name = _gen_getvarname(_gen_front)
            _gen_var_assert = _gen_getassert(_gen_front)
            if(_gen_var_assert != None):
                if(_gen_var_assert[0]=='@' and _gen_var_assert[-1]=='@'):
                    # using double assertions, the user must match the length of the list to his/her input
                    _gen_var_val = _gen_runeval(_gen_var_assert.strip('@'))
                else:
                    # single assertions
                    for i in range(_gen_var_dims[0]):
                        _gen_var_val.append([])
                        for j in range(_gen_var_dims[1]):
                            _gen_var_val[i].append(_gen_runeval(_gen_var_assert, localsdict={'i':i, 'j':j}))
            else:
                # otherwise, ranges are used to determine the values of the matrix
                _gen_front = _gen_front[_gen_front.find("]")+1:]
                _gen_var_constraints = _gen_getrange(_gen_front)
                if(_gen_var_constraints != None):
                    _gen_var_constraints = _gen_var_constraints.split(",")
                    for i in range(_gen_var_dims[0]):
                        _gen_var_val.append([randint(int(_gen_runeval(_gen_var_constraints[0])), int(_gen_runeval(_gen_var_constraints[1]))) for j in range(_gen_var_dims[1])])
            # compare the dimensions of the matrix to the dimensions of the values
            if(len(_gen_var_val) != _gen_var_dims[0] or len(_gen_var_val[0]) != _gen_var_dims[1]):
                _gen_logger.error("The dimensions of the matrix do not match the dimensions of the values constructed by the line.")
                _gen_logger.error("> "+_gen_front)
                exit(0)
            # render to buffer
            _gen_buffer += ("\n".join([" ".join([str(i) for i in j]) for j in _gen_var_val]) + _gen_getsuffix(_gen_front))
            _gen_logger.info(_gen_pack_str(f"Suceessfully generated [intmatrix]: {_gen_var_val}."))
            if(_gen_var_name != None):
                _gen_assign(_gen_var_name, _gen_var_val)
                _gen_logger.info(_gen_pack_str(f"Assigned to local scope: {_gen_var_name} = {_gen_var_val}."))
        
        # * str: generate a random string
        elif(_gen_type[0:3] == "str" and _gen_type[3]!="l"):
            _gen_var_val = ""
            _gen_var_name = _gen_getvarname(_gen_front)
            _gen_var_assert = _gen_getassert(_gen_front)
            if(_gen_var_assert != None):
                _gen_var_val = _gen_runeval(_gen_var_assert)
            else:
                # first get length
                _gen_var_len = _gen_type[4:]
                if(_gen_rng:=_gen_getrange(_gen_var_len)) != None:
                    _gen_var_len = randint(*_gen_split_and_run(_gen_rng, ","))
                else:
                    _gen_var_len = _gen_runeval(_gen_var_len)
                # Ranges:
                # in this case, the 'range' is (...), in which possible chars are listed
                # use a-z,A-Z,0-9 for these special cases
                # eg. (a-z0) will generate a random char from a-z and 0
                _gen_var_constraints = _gen_getrange(_gen_front, enforce_heading=False)
                if(_gen_var_constraints == None):
                    _gen_logger.error("No ranges found in the line.")
                    _gen_logger.error("> "+_gen_front)
                    exit(0)
                _gen_var_constraints = re.sub("a-z", "abcdefghijklmnopqrstuvwxyz", _gen_var_constraints)
                _gen_var_constraints = re.sub("A-Z", "ABCDEFGHIJKLMNOPQRSTUVWXYZ", _gen_var_constraints)
                _gen_var_constraints = re.sub("0-9", "0123456789", _gen_var_constraints)
                # now rand(0,sizeof(_gen_var_constraints)-1) should get the index to a random char
                _gen_dict_len = len(_gen_var_constraints)
                for i in range(_gen_var_len):
                    _gen_var_val += _gen_var_constraints[randint(0, _gen_dict_len-1)]
            _gen_buffer += (_gen_var_val + _gen_getsuffix(_gen_front))
            _gen_logger.info(f"Suceessfully generated [str]: {_gen_var_val}.")
            if(_gen_var_name != None):
                _gen_assign(_gen_var_name, _gen_var_val)
                _gen_logger.info(f"Assigned to local scope: {_gen_var_name} = {_gen_var_val}.")
        
        # * strlist: generate a list of random strings
        elif(_gen_type[0:7] == "strlist"):
            _gen_list_endl = _gen_type.__contains__("$")
            _gen_type = re.sub(r"\$", "", _gen_type)
            _gen_var_len = _gen_type[8:]
            # identify str_len and list_len
            # todo: A better `split` function
            _gen_var_len = _gen_var_len.split(",", maxsplit=1)
            if(_gen_rng:=_gen_getrange(_gen_var_len[0])) != None:
                _gen_list_len = randint(*_gen_split_and_run(_gen_rng, ","))
            else:
                _gen_list_len = _gen_runeval(_gen_var_len[0])
            if(_gen_rng:=_gen_getrange(_gen_var_len[1])) != None:
                _gen_str_len = randint(*_gen_split_and_run(_gen_rng, ","))
            else:
                _gen_str_len = _gen_runeval(_gen_var_len[1])
            _gen_var_val = []
            _gen_var_name = _gen_getvarname(_gen_front)
            _gen_var_assert = _gen_getassert(_gen_front)
            if(_gen_var_assert != None):
                if(_gen_var_assert[0]=='@' and _gen_var_assert[-1]=='@'):
                    # using double assertions, the user must match the length of the list to his/her input
                    _gen_var_val = _gen_runeval(_gen_var_assert.strip('@'))
                else:
                    # single assertions
                    for i in range(_gen_var_len):
                        _gen_var_val.append(_gen_runeval(_gen_var_assert, localsdict={'i':i}))
            else:
                _gen_front = _gen_front[_gen_front.find("]")+1:]
                _gen_var_constraints = _gen_getrange(_gen_front)
                if(_gen_var_constraints == None):
                    _gen_logger.error("No ranges found in the line.")
                    _gen_logger.error("> "+_gen_front)
                    exit(0)
                _gen_var_constraints = re.sub("a-z", "abcdefghijklmnopqrstuvwxyz", _gen_var_constraints)
                _gen_var_constraints = re.sub("A-Z", "ABCDEFGHIJKLMNOPQRSTUVWXYZ", _gen_var_constraints)
                _gen_var_constraints = re.sub("0-9", "0123456789", _gen_var_constraints)
                _gen_dict_len = len(_gen_var_constraints)
                for i in range(_gen_list_len):
                    _gen_var_val.append("".join([_gen_var_constraints[randint(0, _gen_dict_len-1)] for j in range(randint(1, _gen_str_len))]))
            _gen_buffer += (("\n" if _gen_list_endl else " ").join([str(i) for i in _gen_var_val]) + _gen_getsuffix(_gen_front))
            _gen_logger.info(_gen_pack_str(f"Suceessfully generated [strlist]: {_gen_var_val}."))
            if(_gen_var_name != None):
                _gen_assign(_gen_var_name, _gen_var_val)
                _gen_logger.info(_gen_pack_str(f"Assigned to local scope: {_gen_var_name} = {_gen_var_val}."))
        
        _gen_lines.pop(0)
    if(copy_to_clipboard):
        pyperclip.copy(_gen_buffer)
        _gen_logger.info("Buffer copied to clipboard.")
    return _gen_buffer

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    _gen_process()